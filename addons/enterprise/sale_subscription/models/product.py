# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class product_template(models.Model):
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(
        'Subscription Product',
        help='If set, confirming a sale order with this product will create a subscription')

    subscription_template_id = fields.Many2one(
        'sale.subscription.template', 'Subscription Template',
        help="Product will be included in a selected template")

    @api.onchange('type')
    def _onchange_product_type(self):
        """
        Raise a warning if the user has selected 'Storable Product'
        while the product has already been set as a 'Subscription Product'.
        In this case, the 'type' field is reset.
        """
        if self.type == 'product' and self.recurring_invoice:
            self.type = False
            return {'warning': {
                'title': _("Warning"),
                'message': _("A 'Subscription Product' cannot be a 'Storable Product' !")
            }}

    @api.onchange('recurring_invoice')
    def _onchange_recurring_invoice(self):
        """
        Raise a warning if the user has checked 'Subscription Product'
        while the product has already been set as a 'Storable Product'.
        In this case, the 'Subscription Product' field is automatically
        unchecked.
        """
        if self.type == 'product' and self.recurring_invoice:
            self.recurring_invoice = False
            return {'warning': {
                'title': _("Warning"),
                'message': _("A 'Storable Product' cannot be a 'Subscription Product' !")
            }}
        elif not self.recurring_invoice:
            self.subscription_template_id = False

    @api.constrains('recurring_invoice', 'type')
    def _check_subscription_product(self):
        if any(product.recurring_invoice and product.type == 'product' for product in self):
            raise ValidationError(
                _('A subscription product cannot be a storable product.'))
