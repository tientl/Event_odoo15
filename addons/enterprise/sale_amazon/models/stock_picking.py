# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.sale_amazon import const
from odoo.addons.sale_amazon.lib import mws
from odoo.addons.sale_amazon.models import mws_connector as mwsc

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    amazon_sync_pending = fields.Boolean(
        help="Is True if the picking must be notified to Amazon", default=False)

    def write(self, vals):
        pickings = self
        if 'date_done' in vals:
            amazon_pickings = self.sudo().filtered(lambda p: p.sale_id and p.sale_id.amazon_order_ref)
            amazon_pickings._check_sales_order_line_completion()
            # Flag as pending sync the pickings linked to Amazon that are the last step of a (multi-step) delivery route
            last_step_amazon_pickings = amazon_pickings.filtered(lambda p: p.location_dest_id.usage == 'customer')
            super(StockPicking, last_step_amazon_pickings).write(dict(amazon_sync_pending=True, **vals))
            pickings -= last_step_amazon_pickings
        return super(StockPicking, pickings).write(vals)

    def _check_sales_order_line_completion(self):
        """ Check that all stock moves related to a sales order line are set done at the same time.

        This allows to block a confirmation of a stock picking linked to an Amazon sales order if a
        product's components are not all shipped together. This is necessary because Amazon does not
        allow a product shipment to be confirmed multiple times ; its components should come in a
        single package. Furthermore, the customer would expect all the components to be delivered
        at once rather than received only a fraction of a product.

        :raise: UserError if a stock move is set done while other moves related to the same Amazon
                sales order line are not
        """
        for picking in self:
            # To assess the completion of a sales order line, we group related moves together and
            # sum the total demand and done quantities.
            sales_order_lines_completion = {}
            for move in picking.move_lines.filtered('sale_line_id.amazon_item_ref'):
                completion = sales_order_lines_completion.setdefault(move.sale_line_id, [0, 0])
                completion[0] += move.product_uom_qty
                completion[1] += move.quantity_done

            # Check that all sales order lines are either entirely shipped or not shipped at all
            for sales_order_line, completion in sales_order_lines_completion.items():
                demand_qty, done_qty = completion
                completion_ratio = done_qty / demand_qty if demand_qty else 0
                if 0 < completion_ratio < 1:  # The completion ratio must be either 0% or 100%
                    raise UserError(
                        _("Products delivered to Amazon customers must have their respective parts "
                          "in the same package. Operations related to the product %s were not all "
                          "confirmed at once.") % sales_order_line.product_id.display_name
                    )

    def _check_carrier_details_compliance(self):
        """ Check that a picking has a `carrier_tracking_ref`.

        This allows to block a picking to be validated as done if the `carrier_tracking_ref` is
        missing. This is necessary because Amazon requires a tracking reference based on the
        carrier.

        :raise: UserError if `carrier_id` or `carrier_tracking_ref` is missing
        """
        amazon_pickings_sudo = self.sudo().filtered(
            lambda p: p.sale_id
            and p.sale_id.amazon_order_ref
            and p.location_dest_id.usage == 'customer'
        )  # In sudo mode to read the field on sale.order
        for picking_sudo in amazon_pickings_sudo:
            if not picking_sudo.carrier_id.name:
                raise UserError(_(
                    "Amazon requires that a tracking reference is provided with each delivery. You "
                    "need to assign a carrier to this delivery."
                ))
            if not picking_sudo.carrier_tracking_ref:
                raise UserError(_(
                    "Amazon requires that a tracking reference is provided with each delivery. "
                    "Since the current carrier doesn't automatically provide a tracking reference, "
                    "you need to set one manually."
                ))
        return super()._check_carrier_details_compliance()

    @api.model
    def _sync_pickings(self, account_ids=()):
        """
        Notify Amazon to confirm orders whose pickings are marked as done. Called by cron.
        We assume that the combined set of pickings (of all accounts) to be synchronized will always
        be too small for the cron to be killed before it finishes synchronizing all pickings.
        If provided, the tuple of account ids restricts the pickings waiting for synchronization
        to those whose account is listed. If it is not provided, all pickings are synchronized.
        :param account_ids: the ids of accounts whose pickings should be synchronized
        """
        pickings_by_account = {}
        for picking in self.search([('amazon_sync_pending', '=', True)]):
            if picking.sale_id.order_line:
                offer = picking.sale_id.order_line[0].amazon_offer_id
                account = offer and offer.account_id  # Offer can be deleted before the cron update
                if not account or (account_ids and account.id not in account_ids):
                    continue
                pickings_by_account.setdefault(account, self.env['stock.picking'])
                pickings_by_account[account] += picking
        for account, pickings in pickings_by_account.items():
            pickings._confirm_shipment(account)

    def _confirm_shipment(self, account):
        """ Send the order confirmation feed to Amazon for a batch of orders. """
        error_message = _("An error was encountered when preparing the connection to Amazon.")
        feeds_api = mwsc.get_api_connector(
            mws.Feeds,
            account.seller_key,
            account.auth_token,
            account.base_marketplace_id.code,
            error_message,
            **account._build_get_api_connector_kwargs())
        picking_done = self.env['stock.picking']
        for picking in self:
            amazon_order_ref = picking.sale_id.amazon_order_ref
            confirmed_order_lines = picking._get_confirmed_order_lines()
            items_data = confirmed_order_lines.mapped(
                lambda l: (l.amazon_item_ref, l.product_uom_qty)
            )  # Take the quantity from the sales order line in case the picking contains a BoM
            xml_feed = mwsc.generate_order_fulfillment_feed(
                account.seller_key,
                amazon_order_ref,
                picking._get_formatted_carrier_name(),
                picking.carrier_tracking_ref,
                items_data,
            )
            error_message = _("An error was encountered when confirming shipping of the order with "
                              "amazon id %s.") % amazon_order_ref
            feed_submission_id, rate_limit_reached = mwsc.submit_feed(
                feeds_api, xml_feed, '_POST_ORDER_FULFILLMENT_DATA_', error_message)
            if rate_limit_reached:
                _logger.warning("rate limit reached when confirming picking with id %s for order "
                                "with id %s" % (picking.id, picking.sale_id.id))
                break
            _logger.info("sent shipment confirmation (feed id %s) to amazon for order with "
                         "amazon_order_ref %s" % (feed_submission_id, amazon_order_ref))
            picking_done |= picking
        picking_done.write({'amazon_sync_pending': False})

    def _get_confirmed_order_lines(self):
        """ Return the sales order lines linked to this picking that are confirmed.

        A sales order line is confirmed when the shipment of the linked product can be notified to
        Amazon.

        Note: self.ensure_one()
        """
        self.ensure_one()

        return self.move_lines.filtered(
            lambda m: m.sale_line_id.amazon_item_ref  # Only consider moves for Amazon products
            and m.quantity_done > 0  # Only notify Amazon for shipped products
            and m.quantity_done == m.product_uom_qty  # Only consider fully shipped products
        ).sale_line_id

    def _get_formatted_carrier_name(self):
        """ Return the formatted carrier name.

        If a carrier is set and it is not a custom carrier, search for its Amazon-formatted name. If
        it is a custom carrier or if it is not supported by Amazon, fallback on the carrier name.
        """
        self.ensure_one()

        shipper_name = None
        if self.carrier_id:
            carrier_key = self.carrier_id._get_delivery_type()  # Get the final delivery type
            if carrier_key in ('fixed', 'base_on_rule'):  # The delivery carrier is a custom one
                carrier_key = self.carrier_id.name  # Fallback on the carrier name
            carrier_key = ''.join(filter(str.isalnum, carrier_key)).lower()  # Normalize the key
            shipper_name = const.AMAZON_CARRIER_NAMES_MAPPING.get(carrier_key, self.carrier_id.name)
        return shipper_name
