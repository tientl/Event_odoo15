# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase

AWS_RESPONSE_MOCK = {
    'AssumeRoleResponse': {
        'AssumeRoleResult': {
            'Credentials': {
                'AccessKeyId': 'dummy_access_key',
                'SecretAccessKey': 'dummy_secret_key',
                'SessionToken': 'dummy_session_token',
            }
        }
    }
}

ORDER_MOCK = {
    'AmazonOrderId': '123456789',
    'PurchaseDate': '1378-04-08T00:00:00Z',
    'LastUpdateDate': '2017-01-20T00:00:00Z',
    'OrderStatus': 'Unshipped',
    'FulfillmentChannel': 'MFN',
    'ShipServiceLevel': 'SHIPPING-CODE',
    'OrderTotal': {'CurrencyCode': 'USD', 'Amount': '120.00'},
    'MarketplaceId': 'ATVPDKIKX0DER',
}

GET_ORDERS_RESPONSE_MOCK = {
    'payload': {
        'LastUpdatedBefore': '2020-01-01T00:00:00Z',
        'Orders': [ORDER_MOCK]
    }
}

GET_ORDER_ITEMS_MOCK = {
    'payload': {
        'AmazonOrderId': '123456789',
        'OrderItems': [
            {
                'ItemTax': {'CurrencyCode': 'USD', 'Amount': '20.00'},
                'ItemPrice': {'CurrencyCode': 'USD', 'Amount': '100.00'},
                'ShippingTax': {'CurrencyCode': 'USD', 'Amount': '2.50'},
                'ShippingPrice': {'CurrencyCode': 'USD', 'Amount': '12.50'},
                'PromotionDiscountTax': {'CurrencyCode': 'USD', 'Amount': '0.00'},
                'PromotionDiscount': {'CurrencyCode': 'USD', 'Amount': '0.00'},
                'SellerSKU': 'TEST',
                'Title': 'Run Test, Run!',
                'IsGift': 'true',
                'ConditionNote': 'DO NOT BUY THIS',
                'ConditionId': 'Used',
                'ConditionSubtypeId': 'Acceptable',
                'QuantityOrdered': 2,
                'OrderItemId': '987654321',
            },
        ]
    }
}

GET_ORDER_BUYER_INFO_MOCK = {
    'payload': {
        'BuyerEmail': 'iliketurtles@marketplace.amazon.com',
        'BuyerName': 'Gederic Frilson'
    }
}

GET_ORDER_ADDRESS_MOCK = {
    'payload': {
        'ShippingAddress': {
            'AddressLine1': '123 RainBowMan Street',
            'Phone': '+1 234-567-8910 ext. 12345',
            'PostalCode': '12345-1234',
            'City': 'New Duck City DC',
            'StateOrRegion': 'CA',
            'CountryCode': 'US',
            'Name': 'Gederic Frilson',
            'AddressType': 'Commercial'
        }
    }
}

GET_ORDER_ITEMS_BUYER_INFO_MOCK = {
    'payload': {
        'AmazonOrderId': '123456789',
        'OrderItems': [
            {
                'OrderItemId': '987654321',
                'GiftMessageText': 'Wrapped Hello',
                'GiftWrapLevel': 'WRAP-CODE',
                'GiftWrapTax': {'CurrencyCode': 'USD', 'Amount': '1.33'},
                'GiftWrapPrice': {'CurrencyCode': 'USD', 'Amount': '3.33'},
            },
        ]
    }
}

OPERATIONS_RESPONSES_MAP = {
    'getOrders': GET_ORDERS_RESPONSE_MOCK,
    'getOrderItems': GET_ORDER_ITEMS_MOCK,
    'getOrderBuyerInfo': GET_ORDER_BUYER_INFO_MOCK,
    'getOrderAddress': GET_ORDER_ADDRESS_MOCK,
    'getOrderItemsBuyerInfo': GET_ORDER_ITEMS_BUYER_INFO_MOCK,
    'createFeedDocument': {'feedDocumentId': '123123', 'url': 'my_amazing_feed_url.test'},
    'createFeed': None
}


class TestAmazonCommon(TransactionCase):

    def setUp(self):
        super().setUp()
        marketplace = self.env['amazon.marketplace'].search(
            [('api_ref', '=', ORDER_MOCK['MarketplaceId'])]
        )
        self.account = self.env['amazon.account'].create({
            'name': 'TestAccountName',
            'seller_key': 'Random Seller Key',
            'refresh_token': 'A refresh token',
            'base_marketplace_id': marketplace.id,
            'available_marketplace_ids': [marketplace.id],
            'active_marketplace_ids': [marketplace.id],
            'company_id': self.env.company.id,
        })

        # Create a delivery carrier
        product = self.env['product.product'].create({'name': "This is a product"})
        self.carrier = self.env['delivery.carrier'].create(
            {'name': "My Truck", 'product_id': product.id}  # delivery_type == 'fixed'
        )
        self.tracking_ref = "dummy tracking ref"
