# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.sale_amazon_spapi.const import REGION_AND_SELLER_CENTRAL_URL_MAPPING


class AmazonMarketplace(models.Model):
    _inherit = 'amazon.marketplace'

    code = fields.Char(required=False)
    domain = fields.Char(required=False)

    region = fields.Selection(
        string="Region",
        help="The Amazon region of the marketplace. Please refer to the Selling Partner API "
             "documentation to find the correct region.",
        selection=[
            ('us-east-1', "North America"),
            ('eu-west-1', "Europe"),
            ('us-west-2', "Far East"),
        ],
        default='us-east-1',
        required=True,
    )

    seller_central_url = fields.Char(
        string="Seller Central URL",
        help="The Seller Central URL",
        store=True,
        default='',
        required=True,
    )

    @api.model
    def _set_region_and_seller_central_url(self):
        all_marketplaces = self.search([('seller_central_url', '=', '')])
        for marketplace in all_marketplaces:
            marketplace_info = REGION_AND_SELLER_CENTRAL_URL_MAPPING.get(marketplace.api_ref, {})
            marketplace.region = marketplace_info.get('region', '')
            marketplace.seller_central_url = marketplace_info.get('url', '')
