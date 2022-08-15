# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime
from xml.etree import ElementTree

from odoo import api, models

from odoo.addons.sale_amazon_spapi import utils as amazon_utils


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _sync_pickings(self, account_ids=()):
        """ Synchronize the deliveries that were marked as done with Amazon.

        We assume that the combined set of pickings (of all accounts) to be synchronized will always
        be too small for the cron to be killed before it finishes synchronizing all pickings.

        If provided, the tuple of account ids restricts the pickings waiting for synchronization to
        those whose account is listed. If it is not provided, all pickings are synchronized.

        Note: This method is called by the `ir_cron_sync_amazon_pickings` cron.

        :param tuple account_ids: The accounts whose deliveries should be synchronized, as a tuple
                                  of `amazon.account` record ids.
        :return: None
        """
        pickings_by_account = {}

        for picking in self.search([('amazon_sync_pending', '=', True)]):
            if picking.sale_id.order_line:
                offer = picking.sale_id.order_line[0].amazon_offer_id
                account = offer and offer.account_id  # The offer could have been deleted.
                if not account or (account_ids and account.id not in account_ids):
                    continue
                pickings_by_account.setdefault(account, self.env['stock.picking'])
                pickings_by_account[account] += picking

        # Prevent redundant refresh requests.
        accounts = self.env['amazon.account'].browse(account.id for account in pickings_by_account)
        amazon_utils.refresh_aws_credentials(accounts)

        for account, pickings in pickings_by_account.items():
            pickings._confirm_shipment(account)

    def _confirm_shipment(self, account):
        """ Send a confirmation request for each of the current deliveries to Amazon.

        :param record account: The Amazon account of the delivery to confirm on Amazon, as an
                               `amazon.account` record.
        :return: None
        """
        def build_feed_messages(root_):
            """ Build the 'Message' elements to add to the feed.

            :param Element root_: The root XML element to which messages should be added.
            :return: None
            """
            for picking_ in self:
                # Build the message base.
                message_ = ElementTree.SubElement(root_, 'Message')
                order_fulfillment_ = ElementTree.SubElement(message_, 'OrderFulfillment')
                amazon_order_ref_ = picking_.sale_id.amazon_order_ref
                ElementTree.SubElement(order_fulfillment_, 'AmazonOrderID').text = amazon_order_ref_
                shipping_date_ = datetime.now().isoformat()
                ElementTree.SubElement(order_fulfillment_, 'FulfillmentDate').text = shipping_date_

                # Add the fulfillment data.
                fulfillment_data_ = ElementTree.SubElement(
                    order_fulfillment_, 'FulfillmentData'
                )
                ElementTree.SubElement(
                    fulfillment_data_, 'CarrierName'
                ).text = picking_._get_formatted_carrier_name()
                ElementTree.SubElement(
                    fulfillment_data_, 'ShipperTrackingNumber'
                ).text = picking_.carrier_tracking_ref

                # Add the items.
                confirmed_order_lines_ = picking_._get_confirmed_order_lines()
                items_data_ = confirmed_order_lines_.mapped(
                    lambda l_: (l_.amazon_item_ref, l_.product_uom_qty)
                )  # Take the quantity from the sales order line in case the picking contains a BoM.
                for amazon_item_ref_, item_quantity_ in items_data_:
                    item_ = ElementTree.SubElement(order_fulfillment_, 'Item')
                    ElementTree.SubElement(item_, 'AmazonOrderItemCode').text = amazon_item_ref_
                    ElementTree.SubElement(item_, 'Quantity').text = str(int(item_quantity_))

        amazon_utils.ensure_account_is_set_up(account)
        xml_feed = amazon_utils.build_feed(account, 'OrderFulfillment', build_feed_messages)
        try:
            feed_id = amazon_utils.submit_feed(account, xml_feed, 'POST_ORDER_FULFILLMENT_DATA')
        except amazon_utils.AmazonRateLimitError:
            _logger.info(
                "Rate limit reached while sending picking confirmation notification for Amazon "
                "account with id %s.", self.id
            )
        else:
            _logger.info(
                "Sent delivery confirmation notification (feed id %s) to amazon for pickings with "
                "amazon_order_ref %s.",
                feed_id, ', '.join(picking.sale_id.amazon_order_ref for picking in self),
            )
            self.write({'amazon_sync_pending': False})
