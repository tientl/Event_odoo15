# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentAcquirer(models.Model):

    _inherit = 'payment.acquirer'

    @api.model
    def _is_tokenization_required(self, sale_order_id=None, **kwargs):
        """ Override of payment to return whether confirming the order will create a subscription.

        If any product of the order is a attached to a subscription template, and if that order is
        not linked to an already existing subscription, tokenization of the payment transaction is
        required.
        If the order is linked to an existing subscription, there is no need to require the
        tokenization because no payment token is ever assigned to the subscription when the sales
        order is confirmed.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :return: Whether confirming the order will create a subscription
        :rtype: bool
        """
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            for order_line in sale_order.order_line:
                if not order_line.subscription_id and order_line.product_id.recurring_invoice:
                    return True
        return super()._is_tokenization_required(sale_order_id=sale_order_id, **kwargs)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    renewal_allowed = fields.Boolean(
        help="Technical field used to control the renewal flow based on the transaction state",
        compute='_compute_renewal_allowed', store=False)

    @api.depends('state')
    def _compute_renewal_allowed(self):
        for tx in self:
            tx.renewal_allowed = tx.state in ('done', 'authorized')


class PaymentToken(models.Model):
    _name = 'payment.token'
    _inherit = 'payment.token'

    def _handle_deactivation_request(self):
        """ Override of payment to void the token on linked subscriptions.

        Note: self.ensure_one()

        :return: None
        """
        super()._handle_deactivation_request()  # Called first in case an UserError is raised
        linked_subscriptions = self.env['sale.subscription'].search(
            [('payment_token_id', '=', self.id)]
        )
        linked_subscriptions.payment_token_id = False

    def get_linked_records_info(self):
        """ Override of payment to add information about subscriptions linked to the current token.

        Note: self.ensure_one()

        :return: The list of information about linked subscriptions
        :rtype: list
        """
        res = super().get_linked_records_info()
        subscriptions = self.env['sale.subscription'].search([('payment_token_id', '=', self.id)])
        for sub in subscriptions:
            res.append({
                'description': subscriptions._description,
                'id': sub.id,
                'name': sub.name,
                'url': f'/my/subscription/{sub.id}/{sub.uuid}'
            })
        return res
