# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The SellerCentral application ID of Odoo S.A.
APP_ID = 'amzn1.sp.solution.1cab4d17-1dba-47d1-968f-66b10b614b01'


# The URL of the Amazon proxy.
PROXY_URL = 'https://iap-services.odoo.com/'


# The endpoints of the Amazon proxy.
PROXY_ENDPOINTS = {
    'authorization': '/amazon/v1/forward_authorization_request',  # Exchange LWA tokens
    'aws_tokens': '/amazon/v1/forward_aws_credentials_request',  # Request AWS credentials
}


# Base URLs of the API.
API_DOMAINS_MAPPING = {
    'us-east-1': 'https://sellingpartnerapi-na.amazon.com',  # SP-API specific to NA marketplaces.
    'eu-west-1': 'https://sellingpartnerapi-eu.amazon.com',  # SP-API specific to EU marketplaces.
    'us-west-2': 'https://sellingpartnerapi-fe.amazon.com',  # SP-API specific to FE marketplaces.
}

# Regions and Seller Central URLs of the marketplaces.
REGION_AND_SELLER_CENTRAL_URL_MAPPING = {
    # North America
    'A2EUQ1WTGCTBG2': {'region': 'us-east-1', 'url': 'https://sellercentral.amazon.ca'},
    'ATVPDKIKX0DER': {'region': 'us-east-1', 'url': 'https://sellercentral.amazon.com'},
    'A1AM78C64UM0Y8': {'region': 'us-east-1', 'url': 'https://sellercentral.amazon.com.mx'},
    'A2Q3Y263D00KWC': {'region': 'us-east-1', 'url': 'https://sellercentral.amazon.com.br'},
    # Europe
    'A1RKKUPIHCS9HS': {'region': 'eu-west-1', 'url': 'https://sellercentral-europe.amazon.com'},
    'A1F83G8C2ARO7P': {'region': 'eu-west-1', 'url': 'https://sellercentral-europe.amazon.com'},
    'A13V1IB3VIYZZH': {'region': 'eu-west-1', 'url': 'https://sellercentral-europe.amazon.com'},
    'A1805IZSGTT6HS': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.nl'},
    'A1PA6795UKMFR9': {'region': 'eu-west-1', 'url': 'https://sellercentral-europe.amazon.com'},
    'APJ6JRA9NG5V4': {'region': 'eu-west-1', 'url': 'https://sellercentral-europe.amazon.com'},
    'A2NODRKZP88ZB9': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.se'},
    'A1C3SOZRARQ6R3': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.pl'},
    'ARBP9OOSHTCHU': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.eg'},
    'A33AVAJ2PDY3EV': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.com.tr'},
    'A2VIGQ35RCS4UG': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.ae'},
    'A21TJRUUN4KGV': {'region': 'eu-west-1', 'url': 'https://sellercentral.amazon.in'},
    # Far East
    'A19VAU5U5O7RUS': {'region': 'us-west-2', 'url': 'https://sellercentral.amazon.sg'},
    'A39IBJ37TRP1C6': {'region': 'us-west-2', 'url': 'https://sellercentral.amazon.com.au'},
    'A1VC38T7YXB528': {'region': 'us-west-2', 'url': 'https://sellercentral.amazon.co.jp'},
}

# Mapping of API operation to URL paths and restricted resource paths.
API_PATHS_MAPPING = {
    'createFeed': {
        'url_path': '/feeds/2021-06-30/feeds',
        'restricted_resource_path': None,
    },
    'createFeedDocument': {
        'url_path': '/feeds/2021-06-30/documents',
        'restricted_resource_path': None,
    },
    'createRestrictedDataToken': {
        'url_path': '/tokens/2021-03-01/restrictedDataToken',
        'restricted_resource_path': None,
    },
    'getMarketplaceParticipations': {
        'url_path': '/sellers/v1/marketplaceParticipations',
        'restricted_resource_path': None,
    },
    'getOrders': {
        'url_path': '/orders/v0/orders',
        'restricted_resource_path': None,
    },
    'getOrderAddress': {
        'url_path': '/orders/v0/orders/{param}/address',
        'restricted_resource_path': '/orders/v0/orders/{this_is_bullshit}/address',
    },
    'getOrderBuyerInfo': {
        'url_path': '/orders/v0/orders/{param}/buyerInfo',
        'restricted_resource_path': '/orders/v0/orders/{this_is_bullshit}/buyerInfo',
    },
    'getOrderItems': {
        'url_path': '/orders/v0/orders/{param}/orderItems',
        'restricted_resource_path': None,
    },
    'getOrderItemsBuyerInfo': {
        'url_path': '/orders/v0/orders/{param}/orderItems/buyerInfo',
        'restricted_resource_path': '/orders/v0/orders/{this_is_bullshit}/orderItems/buyerInfo',
    },
}


# Mapping of Amazon fulfillment channels to Amazon status to synchronize.
STATUS_TO_SYNCHRONIZE = {
    'AFN': ['Shipped'],
    'MFN': ['Unshipped'],
}
