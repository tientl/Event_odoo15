# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import dateutil.parser
import psycopg2
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY as CONCURRENCY_ERRORS
from odoo.tools import hmac as hmac_tool

from odoo.addons.sale_amazon_spapi import const, utils as amazon_utils


_logger = logging.getLogger(__name__)


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    seller_key = fields.Char(required=False)
    auth_token = fields.Char(required=False)
    refresh_token = fields.Char(
        string="LWA Refresh Token",
        help="The long-lived token that can be exchanged for a new access token.",
    )

    # The API credentials fields below are not stored because they are all short-lived. Their values
    # are kept in memory for the duration of the request and they are re-used as long as they are
    # not expired. If that happens, they are refreshed through an API call.

    access_token = fields.Char(
        string="LWA Access Token",
        help="The short-lived token used to query Amazon API on behalf of a seller.",
        store=False,
    )
    access_token_expiry = fields.Datetime(
        string="The moment at which the token becomes invalid.", default='1970-01-01', store=False
    )
    aws_access_key = fields.Char(
        string="AWS Access Key",
        help="The short-lived key used to identify the assumed ARN role on AWS.",
        store=False,
    )
    aws_secret_key = fields.Char(
        string="AWS Secret Key",
        help="The short-lived key used to verify the access to the assumed ARN role on AWS.",
        store=False,
    )
    aws_session_token = fields.Char(
        string="AWS Session Token",
        help="The short-lived token used to query the SP-API with the assumed ARN role on AWS.",
        store=False,
    )
    aws_credentials_expiry = fields.Datetime(
        string="The moment at which the AWS credentials become invalid.",
        default='1970-01-01',
        store=False,
    )
    restricted_data_token = fields.Char(
        string="Restricted Data Token",
        help="The short-lived token used instead of the LWA Access Token to access restricted data",
        store=False,
    )
    restricted_data_token_expiry = fields.Datetime(
        string="The moment at which the Restricted Data Token becomes invalid.",
        default='1970-01-01',
        store=False,
    )

    #=== CRUD METHODS ===#

    def update_vals_with_active_marketplaces(self, _vals):
        """ Override of sale_amazon to disable the update of active marketplaces when creating the
        account. """
        return

    def check_api_keys(self, _vals):
        """" Override of sale_amazon to disable the check on API keys when updating the account. """
        return

    #=== ACTION METHODS ===#

    def action_redirect_to_oauth_url(self):
        """ Build the OAuth redirect URL and redirect the user to it.

        See step 1 of https://developer-docs.amazon.com/sp-api/docs/website-authorization-workflow.

        Note: self.ensure_one()

        :return: An `ir.actions.act_url` action to redirect the user to the OAuth URL.
        :rtype: dict
        """
        self.ensure_one()

        base_seller_central_url = self.base_marketplace_id.seller_central_url
        oauth_url = urls.url_join(base_seller_central_url, '/apps/authorize/consent')
        base_database_url = self.get_base_url()
        metadata = {
            'account_id': self.id,
            'return_url': urls.url_join(base_database_url, 'amazon/return'),
            'signature': hmac_tool(
                self.env(su=True), 'amazon_compute_oauth_signature', str(self.id)
            ),
        }  # The metadata included in the redirect URL after authorizing the app on Amazon.
        oauth_url_params = {
            'application_id': const.APP_ID,
            'state': json.dumps(metadata),
        }
        return {
            'type': 'ir.actions.act_url',
            'url': f'{oauth_url}?{urls.url_encode(oauth_url_params)}',
            'target': 'self',
        }

    def action_reset_refresh_token(self):
        """ Reset the refresh token of the account.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

        self.refresh_token = None

    def action_check_credentials(self, **_api_keys):
        """ Override of sale_amazon_authentication to disable the credentials check. """
        return

    def action_update_available_marketplaces(self):
        """ Update available marketplaces and assign new ones to the account.

        :return: A rainbow-man action to inform the user about the successful update.
        :rtype: dict
        """
        for account in self:
            available_marketplaces = account._get_available_marketplaces()
            new_marketplaces = available_marketplaces - account.available_marketplace_ids
            account.write({'available_marketplace_ids': [(6, 0, available_marketplaces.ids)]})
            account._onchange_available_marketplace_ids()  # Remove unavailable marketplaces.
            account.active_marketplace_ids += new_marketplaces
        return {
            'effect': {
                'type': 'rainbow_man',
                'message': _("Successfully updated the marketplaces available to this account!"),
            }
        }

    #=== BUSINESS METHODS ===#

    def _get_available_marketplaces(self, *args, **kwargs):
        """ Fetch the API refs of the available marketplaces and return the corresponding recordset.

        Note: self.ensure_one()

        :return: The available marketplaces for the Amazon account.
        :rtype: recordset of `amazon.marketplace`
        :raise UserError: If the rate limit is reached.
        """
        self.ensure_one()

        amazon_utils.ensure_account_is_set_up(self, require_marketplaces=False)
        try:
            response_content = amazon_utils.make_sp_api_request(
                self, 'getMarketplaceParticipations'
            )
        except amazon_utils.AmazonRateLimitError:
            _logger.info(
                "Rate limit reached while updating available marketplaces for Amazon account with "
                "id %s.", self.id
            )
            raise UserError(_(
                "You reached the maximum number of requests for this operation; please try again "
                "later."
            ))
        else:
            available_marketplace_api_refs = [
                marketplace['marketplace']['id'] for marketplace in response_content['payload']
            ]
            return self.env['amazon.marketplace'].search(
                [('api_ref', 'in', available_marketplace_api_refs)]
            )

    def _sync_orders(self, auto_commit=True):
        """ Synchronize the sales orders that were recently updated on Amazon.

        If called on an empty recordset, the orders of all active accounts are synchronized instead.

        Note: This method is called by the `ir_cron_sync_amazon_orders` cron.

        :param bool auto_commit: Whether the database cursor should be committed as soon as an order
                                 is successfully synchronized.
        :return: None
        """
        accounts = self or self.search([])
        amazon_utils.refresh_aws_credentials(accounts)  # Prevent redundant refresh requests.
        for account in accounts:
            account = account[0]  # Avoid pre-fetching after each cache invalidation.
            amazon_utils.ensure_account_is_set_up(account)

            # The last synchronization date of the account is used as the lower limit on the orders'
            # last status update date. The upper limit is determined by the API and returned in the
            # request response, then saved on the account if the synchronization goes through.
            last_updated_after = account.last_orders_sync  # Lower limit for pulling orders.
            status_update_upper_limit = None  # Upper limit of synchronized orders.

            # Pull all recently updated orders and save the progress during synchronization.
            payload = {
                'LastUpdatedAfter': last_updated_after.isoformat(sep='T'),
                'MarketplaceIds': ','.join(account.active_marketplace_ids.mapped('api_ref')),
            }
            try:
                # Orders are pulled in batches of up to 100 orders. If more can be synchronized, the
                # request results are paginated and the next page holds another batch.
                has_next_page = True
                while has_next_page:
                    # Pull the next batch of orders data.
                    orders_batch_data, has_next_page = amazon_utils.pull_batch_data(
                        account, 'getOrders', payload
                    )
                    orders_data = orders_batch_data['Orders']
                    status_update_upper_limit = dateutil.parser.parse(
                        orders_batch_data['LastUpdatedBefore']
                    )

                    # Process the batch one order data at a time.
                    for order_data in orders_data:
                        try:
                            with self.env.cr.savepoint():
                                account._process_order_data(order_data)
                        except amazon_utils.AmazonRateLimitError:
                            raise  # Don't treat a rate limit error as a business error.
                        except Exception as error:
                            amazon_order_ref = order_data['AmazonOrderId']
                            if isinstance(error, psycopg2.OperationalError) \
                                and error.pgcode in CONCURRENCY_ERRORS:
                                _logger.info(
                                    "A concurrency error occurred while processing the order data "
                                    "with amazon_order_ref %s for Amazon account with id %s. "
                                    "Discarding the error to trigger the retry mechanism.",
                                    amazon_order_ref, account.id
                                )
                                # Let the error bubble up so that either the request can be retried
                                # up to 5 times or the cron job rollbacks the cursor and reschedules
                                # itself later, depending on which of the two called this method.
                                raise
                            else:
                                _logger.exception(
                                    "A business error occurred while processing the order data "
                                    "with amazon_order_ref %s for Amazon account with id %s. "
                                    "Skipping the order data and moving to the next order.",
                                    amazon_order_ref, account.id
                                )
                                # Dismiss business errors to allow the synchronization to skip the
                                # problematic orders and require synchronizing them manually.
                                self.env.cr.rollback()
                                account._handle_order_sync_failure(amazon_order_ref, log=False)
                                continue  # Skip these order data and resume with the next ones.

                        # The synchronization of this order went through, use its last status update
                        # as a backup and set it to be the last synchronization date of the account.
                        last_order_update = dateutil.parser.parse(order_data['LastUpdateDate'])
                        account.last_orders_sync = last_order_update.replace(tzinfo=None)
                        if auto_commit:
                            with amazon_utils.preserve_credentials(account):
                                self.env.cr.commit()  # Commit to mitigate an eventual cron kill.
            except amazon_utils.AmazonRateLimitError as error:
                _logger.info(
                    "Rate limit reached while synchronizing sales orders for Amazon account with "
                    "id %s. Operation: %s", account.id, error.operation
                )
                continue  # The remaining orders will be pulled later when the cron runs again.

            # There are no more orders to pull and the synchronization went through. Set the API
            # upper limit on order status update to be the last synchronization date of the account.
            account.last_orders_sync = status_update_upper_limit.replace(tzinfo=None)

    def _process_order_data(self, order_data):
        """ Process the provided order data and return the matching sales order, if any.

        If no matching sales order is found, a new one is created if it is in a 'synchronizable'
        status: 'Shipped' or 'Unshipped', if it is respectively an FBA or an FBA order. If the
        matching sales order already exists and the Amazon order was canceled, the sales order is
        also canceled.

        Note: self.ensure_one()

        :param dict order_data: The order data to process.
        :return: The matching Amazon order, if any, as a `sale.order` record.
        :rtype: recordset of `sale.order`
        """
        self.ensure_one()

        # Search for the sales order based on its Amazon order reference.
        amazon_order_ref = order_data['AmazonOrderId']
        order = self.env['sale.order'].search(
            [('amazon_order_ref', '=', amazon_order_ref)], limit=1
        )
        amazon_status = order_data['OrderStatus']
        if not order:  # No sales order was found with the given Amazon order reference.
            fulfillment_channel = order_data['FulfillmentChannel']
            if amazon_status in const.STATUS_TO_SYNCHRONIZE[fulfillment_channel]:
                # Create the sales order and generate stock moves depending on the Amazon channel.
                order = self._create_order_from_data(order_data)
                if order.amazon_channel == 'fba':
                    self._generate_stock_moves(order)
                elif order.amazon_channel == 'fbm':
                    order.with_context(mail_notrack=True).action_done()
                _logger.info(
                    "Created a new sales order with amazon_order_ref %s for Amazon account with "
                    "id %s.", amazon_order_ref, self.id
                )
            else:
                _logger.info(
                    "Ignored Amazon order with reference %(ref)s and status %(status)s for Amazon "
                    "account with id %(account_id)s.",
                    {'ref': amazon_order_ref, 'status': amazon_status, 'account_id': self.id},
                )
        else:  # The sales order already exists.
            if amazon_status == 'Canceled' and order.state != 'cancel':
                order._action_cancel()
                _logger.info(
                    "Canceled sales order with amazon_order_ref %s for Amazon account with id %s.",
                    amazon_order_ref, self.id
                )
            else:
                _logger.info(
                    "Ignored already synchronized sales order with amazon_order_ref %s for Amazon"
                    "account with id %s.", amazon_order_ref, self.id
                )
        return order

    def _create_order_from_data(self, order_data):
        """ Create a new sales order based on the provided order data.

        Note: self.ensure_one()

        :param dict order_data: The order data to create a sales order from.
        :return: The newly created sales order.
        :rtype: record of `sale.order`
        """
        self.ensure_one()

        # Prepare the order line values.
        shipping_code = order_data.get('ShipServiceLevel')
        shipping_product = self._get_product(
            shipping_code, 'shipping_product', 'Shipping', 'service'
        )
        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', order_data['OrderTotal']['CurrencyCode'])], limit=1
        )
        amazon_order_ref = order_data['AmazonOrderId']
        contact_partner, delivery_partner = self._find_or_create_partners_from_data(order_data)
        fiscal_position_id = self.env['account.fiscal.position'].with_company(
            self.company_id
        ).get_fiscal_position(contact_partner.id, delivery_partner.id).id
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position_id)
        order_lines_values = self._prepare_order_lines_values(
            order_data, currency, fiscal_position, shipping_product
        )

        # Create the sales order.
        fulfillment_channel = order_data['FulfillmentChannel']
        # The state is first set to 'sale' and later to 'done' to generate a picking if fulfilled
        # by merchant, or directly set to 'done' to generate no picking if fulfilled by Amazon.
        state = 'done' if fulfillment_channel == 'AFN' else 'sale'
        purchase_date = dateutil.parser.parse(order_data['PurchaseDate']).replace(tzinfo=None)
        order_vals = {
            'origin': f"Amazon Order {amazon_order_ref}",
            'state': state,
            'date_order': purchase_date,
            'partner_id': contact_partner.id,
            'pricelist_id': self._get_pricelist(currency).id,
            'order_line': [(0, 0, order_line_values) for order_line_values in order_lines_values],
            'invoice_status': 'no',
            'partner_shipping_id': delivery_partner.id,
            'require_signature': False,
            'require_payment': False,
            'fiscal_position_id': fiscal_position_id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'amazon_order_ref': amazon_order_ref,
            'amazon_channel': 'fba' if fulfillment_channel == 'AFN' else 'fbm',
        }
        if self.location_id.warehouse_id:
            order_vals['warehouse_id'] = self.location_id.warehouse_id.id
        return self.env['sale.order'].with_context(
            mail_create_nosubscribe=True,
        ).with_company(self.company_id).create(order_vals)

    def _prepare_order_lines_values(self, order_data, currency, fiscal_pos, shipping_product):
        """ Prepare the values for the order lines to create based on Amazon data.

        Note: self.ensure_one()

        :param dict order_data: The order data related to the items data.
        :param record currency: The currency of the sales order, as a `res.currency` record.
        :param record fiscal_pos: The fiscal position of the sales order, as an
                                  `account.fiscal.position` record.
        :param record shipping_product: The shipping product matching the shipping code, as a
                                        `product.product` record.
        :return: The order lines values.
        :rtype: dict
        """
        def pull_items_data(amazon_order_ref_):
            """ Pull all items data for the order to synchronize.

            :param str amazon_order_ref_: The Amazon reference of the order to synchronize.
            :return: The items data.
            :rtype: list
            """
            items_data_ = []
            # Order items are pulled in batches. If more order items than those returned can be
            # synchronized, the request results are paginated and the next page holds another batch.
            has_next_page_ = True
            while has_next_page_:
                # Pull the next batch of order items.
                items_batch_data_, has_next_page_ = amazon_utils.pull_batch_data(
                    self, 'getOrderItems', {}, path_parameter=amazon_order_ref_
                )
                items_data_ += items_batch_data_['OrderItems']
            return items_data_

        def pull_gift_wraps_data(amazon_order_ref_):
            """ Pull all gift wraps data for the items of the order to synchronize.

            :param str amazon_order_ref_: The Amazon reference of the order to synchronize.
            :return: The gift wraps data.
            :rtype: dict
            """
            restricted_items_data_ = amazon_utils.make_sp_api_request(
                self, 'getOrderItemsBuyerInfo', path_parameter=amazon_order_ref_
            )['payload']['OrderItems']
            return {value_['OrderItemId']: value_ for value_ in restricted_items_data_}

        def convert_to_order_line_values(**kwargs_):
            """ Convert and complete a dict of values to comply with fields of `sale.order.line`.

            :param dict kwargs_: The values to convert and complete.
            :return: The completed values.
            :rtype: dict
            """
            subtotal_ = kwargs_.get('subtotal', 0)
            quantity_ = kwargs_.get('quantity', 1)
            return {
                'name': kwargs_.get('description', ''),
                'product_id': kwargs_.get('product_id'),
                'price_unit': subtotal_ / quantity_ if quantity_ else 0,
                'tax_id': [(6, 0, kwargs_.get('tax_ids', []))],
                'product_uom_qty': quantity_,
                'discount': (kwargs_.get('discount', 0) / subtotal_) * 100 if subtotal_ else 0,
                'display_type': kwargs_.get('display_type', False),
                'amazon_item_ref': kwargs_.get('amazon_item_ref'),
                'amazon_offer_id': kwargs_.get('amazon_offer_id'),
            }

        self.ensure_one()

        amazon_order_ref = order_data['AmazonOrderId']
        marketplace_api_ref = order_data['MarketplaceId']

        items_data = pull_items_data(amazon_order_ref)
        if any(item_data.get('IsGift', 'false') == 'true' for item_data in items_data):
            # Information on gift wraps is considered restricted data and thus not included in
            # items data. Pull them separately.
            gift_wraps_data = pull_gift_wraps_data(amazon_order_ref)
        else:
            gift_wraps_data = {}  # Information on gift wraps are not required.

        order_lines_values = []
        for item_data in items_data:
            # Prepare the values for the product line.
            sku = item_data['SellerSKU']
            marketplace = self.active_marketplace_ids.filtered(
                lambda m: m.api_ref == marketplace_api_ref
            )
            offer = self._get_offer(sku, marketplace)
            product_taxes = offer.product_id.taxes_id.filtered(
                lambda t: t.company_id.id == self.company_id.id
            )
            main_condition = item_data.get('ConditionId')
            sub_condition = item_data.get('ConditionSubtypeId')
            description_template = "[%s] %s" \
                if not main_condition or main_condition.lower() == 'new' \
                else _("[%s] %s\nCondition: %s - %s")
            description_fields = (sku, item_data['Title']) \
                if not main_condition or main_condition.lower() == 'new' \
                else (sku, item_data['Title'], main_condition, sub_condition)
            sales_price = float(item_data.get('ItemPrice', {}).get('Amount', 0.0))
            tax_amount = float(item_data.get('ItemTax', {}).get('Amount', 0.0))
            original_subtotal = sales_price - tax_amount \
                if marketplace.tax_included else sales_price
            taxes = fiscal_pos.map_tax(product_taxes) if fiscal_pos else product_taxes
            subtotal = self._recompute_subtotal(
                original_subtotal, tax_amount, taxes, currency, fiscal_pos
            )
            amazon_item_ref = item_data['OrderItemId']
            order_lines_values.append(convert_to_order_line_values(
                product_id=offer.product_id.id,
                description=description_template % description_fields,
                subtotal=subtotal,
                tax_ids=taxes.ids,
                quantity=item_data['QuantityOrdered'],
                discount=float(item_data.get('PromotionDiscount', {}).get('Amount', '0')),
                amazon_item_ref=amazon_item_ref,
                amazon_offer_id=offer.id,
            ))

            # Prepare the values for the gift wrap line.
            if item_data.get('IsGift', 'false') == 'true':
                item_gift_info = gift_wraps_data[amazon_item_ref]
                gift_wrap_code = item_gift_info.get('GiftWrapLevel')
                gift_wrap_price = float(item_gift_info.get('GiftWrapPrice', {}).get('Amount', '0'))
                if gift_wrap_code and gift_wrap_price != 0:
                    gift_wrap_product = self._get_product(
                        gift_wrap_code, 'default_product', 'Amazon Sales', 'consu'
                    )
                    gift_wrap_product_taxes = gift_wrap_product.taxes_id.filtered(
                        lambda t: t.company_id.id == self.company_id.id
                    )
                    gift_wrap_taxes = fiscal_pos.map_tax(gift_wrap_product_taxes) \
                        if fiscal_pos else gift_wrap_product_taxes
                    gift_wrap_tax_amount = float(
                        item_gift_info.get('GiftWrapTax', {}).get('Amount', '0')
                    )
                    original_gift_wrap_subtotal = gift_wrap_price - gift_wrap_tax_amount \
                        if marketplace.tax_included else gift_wrap_price
                    gift_wrap_subtotal = self._recompute_subtotal(
                        original_gift_wrap_subtotal,
                        gift_wrap_tax_amount,
                        gift_wrap_taxes,
                        currency,
                        fiscal_pos,
                    )
                    order_lines_values.append(convert_to_order_line_values(
                        product_id=gift_wrap_product.id,
                        description=_("[%s] Gift Wrapping Charges for %s") % (
                            gift_wrap_code, offer.product_id.name
                        ),
                        subtotal=gift_wrap_subtotal,
                        tax_ids=gift_wrap_taxes.ids,
                    ))
                gift_message = item_gift_info.get('GiftMessageText')
                if gift_message:
                    order_lines_values.append(convert_to_order_line_values(
                        description=_("Gift message:\n%s") % gift_message,
                        display_type='line_note',
                    ))

            # Prepare the values for the delivery charges.
            shipping_code = order_data.get('ShipServiceLevel')
            if shipping_code:
                shipping_price = float(item_data.get('ShippingPrice', {}).get('Amount', '0'))
                shipping_product_taxes = shipping_product.taxes_id.filtered(
                    lambda t: t.company_id.id == self.company_id.id
                )
                shipping_taxes = fiscal_pos.map_tax(shipping_product_taxes) if fiscal_pos \
                    else shipping_product_taxes
                shipping_tax_amount = float(item_data.get('ShippingTax', {}).get('Amount', '0'))
                origin_ship_subtotal = shipping_price - shipping_tax_amount \
                    if marketplace.tax_included else shipping_price
                shipping_subtotal = self._recompute_subtotal(
                    origin_ship_subtotal, shipping_tax_amount, shipping_taxes, currency, fiscal_pos
                )
                order_lines_values.append(convert_to_order_line_values(
                    product_id=shipping_product.id,
                    description=_("[%s] Delivery Charges for %s") % (
                        shipping_code, offer.product_id.name
                    ),
                    subtotal=shipping_subtotal,
                    tax_ids=shipping_taxes.ids,
                    discount=float(item_data.get('ShippingDiscount', {}).get('Amount', '0')),
                ))

        return order_lines_values

    def _find_or_create_partners_from_data(self, order_data):
        """ Find or create the contact and delivery partners based on the provided order data.

        Note: self.ensure_one()

        :param dict order_data: The order data to find or create the partners from.
        :return: The contact and delivery partners, as `res.partner` records. When the contact
                 partner acts as delivery partner, the records are the same.
        :rtype: tuple[record of `res.partner`, record of `res.partner`]
        """
        self.ensure_one()

        amazon_order_ref = order_data['AmazonOrderId']
        anonymized_email = order_data.get('BuyerInfo', {}).get('BuyerEmail')
        buyer_name = order_data.get('BuyerInfo', {}).get('BuyerName')
        if not anonymized_email or not buyer_name:
            # The buyer name and email might be considered restricted data and thus not included in
            # the order data. Pull them separately if that's the case.
            buyer_info = amazon_utils.make_sp_api_request(
                self, 'getOrderBuyerInfo', path_parameter=amazon_order_ref
            )['payload']
            anonymized_email = anonymized_email or buyer_info.get('BuyerEmail', '')
            buyer_name = buyer_name or buyer_info.get('BuyerName', '')

        # Information on shipping address data is considered restricted data and thus not included
        # in the order data. Pull them separately.
        shipping_address_info = amazon_utils.make_sp_api_request(
            self, 'getOrderAddress', path_parameter=amazon_order_ref,
        )['payload']['ShippingAddress']
        shipping_address_name = shipping_address_info['Name']
        street = shipping_address_info.get('AddressLine1', '')
        address_line2 = shipping_address_info.get('AddressLine2', '')
        address_line3 = shipping_address_info.get('AddressLine3', '')
        street2 = "%s %s" % (address_line2, address_line3) if address_line2 or address_line3 \
            else None
        zip_code = shipping_address_info.get('PostalCode', '')
        city = shipping_address_info.get('City', '')
        country_code = shipping_address_info.get('CountryCode', '')
        state_code = shipping_address_info.get('StateOrRegion', '')
        phone = shipping_address_info.get('Phone', '')
        is_company = shipping_address_info.get('AddressType') == 'Commercial'

        country, state = self._get_country_and_state(country_code, state_code)
        partner_vals = self._get_amazon_partner_vals(
            street, street2, zip_code, city, country, state, phone, anonymized_email
        )
        contact = self._get_contact_partner(
            buyer_name, anonymized_email, amazon_order_ref, is_company, partner_vals
        )
        delivery = self._get_delivery_partner(
            contact, shipping_address_name, street, street2, zip_code, city, country, state,
            partner_vals,
        )

        return contact, delivery
