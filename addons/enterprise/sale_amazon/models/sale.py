# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from . import mws_connector as mwsc
from odoo import api, fields, models, _

from odoo.addons.sale_amazon.lib import mws

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    amazon_order_ref = fields.Char(help="The Amazon-defined order reference")
    amazon_channel = fields.Selection(
        [('fbm', "Fulfillment by Merchant"), ('fba', "Fulfillment by Amazon")],
        string="Fulfillment Channel")

    _sql_constraints = [(
        'unique_amazon_order_ref',
        'UNIQUE(amazon_order_ref)',
        "There can only exist one sale order for a given Amazon Order Reference."
    )]

    def action_cancel(self):
        out_of_sync_orders = self.env[self._name]
        if self.env.context.get('canceled_by_amazon'):
            for order in self:
                picking = self.env['stock.picking'].search([
                    ('sale_id', '=', order.id),
                    ('state', '=', 'done')
                ])
                if picking:
                    # picking was processed on Odoo, while Amazon canceled it
                    order.message_post(
                        body=_(
                            "The order has been canceled by the Amazon customer while some products"
                            " have already been delivered. Please create a return for this order"
                            " to adjust the stock."
                        )
                    )
                    out_of_sync_orders |= order
        return super(SaleOrder, self - out_of_sync_orders).action_cancel()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    amazon_item_ref = fields.Char("Amazon-defined item reference")
    amazon_offer_id = fields.Many2one('amazon.offer', "Amazon Offer", ondelete='set null')

    _sql_constraints = [(
        'unique_amazon_item_ref',
        'UNIQUE(amazon_item_ref)',
        "There can only exist one sale order line for a given Amazon Item Reference."
    )]
