# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import TransactionCase


BASE_ORDER_DATA = {
    'AmazonOrderId': {'value': '123456789'},
    'PurchaseDate': {'value': '1378-04-08T00:00:00.000Z'},
    'LastUpdateDate': {'value': '1976-08-21T07:00:00.000Z'},
    'OrderStatus': {'value': 'Unshipped'},
    'FulfillmentChannel': {'value': 'MFN'},
    'ShipServiceLevel': {'value': 'SHIPPING-CODE'},
    'ShippingAddress': {
        'City': {'value': 'OdooCity'},
        'AddressType': {'value': 'Commercial'},
        'PostalCode': {'value': '12345-1234'},
        'StateOrRegion': {'value': 'CA'},
        'Phone': {'value': '+1 234-567-8910 ext. 12345'},
        'CountryCode': {'value': 'US'},
        'Name': {'value': 'Gederic Frilson'},
        'AddressLine1': {'value': '123 RainBowMan Street'},
    },
    'OrderTotal': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '0.00'}},
    'MarketplaceId': {'value': 'ATVPDKIKX0DER'},
    'BuyerEmail': {'value': 'iliketurtles@marketplace.amazon.com'},
    'BuyerName': {'value': 'Gederic Frilson'},
    'EarliestDeliveryDate': {'value': '1979-04-20T00:00:00.000Z'},
}

BASE_ITEM_DATA = {
    'OrderItemId': {'value': '123456789'},
    'SellerSKU': {'value': 'SKU'},
    'ConditionId': {'value': 'Used'},
    'ConditionSubtypeId': {'value': 'Good'},
    'Title': {'value': 'OdooBike Spare Wheel, 26x2.1, Pink, 200-Pack'},
    'QuantityOrdered': {'value': '2'},
    'ItemPrice': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '100.00'}},
    'ShippingPrice': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '12.50'}},
    'GiftWrapPrice': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '3.33'}},
    'ItemTax': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '0.00'}},
    'ShippingTax': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '0.00'}},
    'GiftWrapTax': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '0.00'}},
    'ShippingDiscount': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '0.00'}},
    'PromotionDiscount': {'CurrencyCode': {'value': 'USD'}, 'Amount': {'value': '0.00'}},
    'IsGift': {'value': 'true'},
    'GiftWrapLevel': {'value': 'WRAP-CODE'},
    'GiftMessageText': {'value': 'Hi,\nEnjoy your gift!\nFrom Gederic Frilson'},
}


class TestAmazonCommon(TransactionCase):

    def setUp(self):

        def _get_available_marketplace_api_refs_mock(*_args, **_kwargs):
            """ Return the API ref of all marketplaces without calling MWS API. """
            return self.env['amazon.marketplace'].search([]).mapped('api_ref'), False

        super().setUp()

        # Create account
        with patch('odoo.addons.sale_amazon.models.mws_connector.get_api_connector',
                   new=lambda *args, **kwargs: None), \
            patch('odoo.addons.sale_amazon.models.mws_connector.get_available_marketplace_api_refs',
                  new=_get_available_marketplace_api_refs_mock):
            self.account = self.env['amazon.account'].create({
                'name': "TestAccountName",
                **dict.fromkeys(('seller_key', 'auth_token'), ''),
                'base_marketplace_id': 1,
                'company_id': self.env.company.id,
            })

        # Create a delivery carrier
        product = self.env['product.product'].create({'name': "This is a product"})
        self.carrier = self.env['delivery.carrier'].create(
            {'name': "My Truck", 'product_id': product.id}  # delivery_type == 'fixed'
        )
