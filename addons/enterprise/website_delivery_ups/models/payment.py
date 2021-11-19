# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    @api.model
    def _get_compatible_acquirers(self, *args, sale_order_id=None, **kwargs):
        """ Override of payment to update the base criteria with UPS-specific criteria.

        In addition to the base criteria, the acquirers must either be only COD acquirers if the
        order delivery type is UPS, or not be COD acquirers.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :return: The COD acquirer or all other compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        compatible_acquirers = super()._get_compatible_acquirers(
            *args, sale_order_id=sale_order_id, **kwargs
        )
        cod_acquirer = self.env.ref('website_delivery_ups.payment_acquirer_ups_cod')
        sale_order = self.env['sale.order'].browse(sale_order_id).exists()
        if sale_order.carrier_id.delivery_type == 'ups' and sale_order.carrier_id.ups_cod:
            return compatible_acquirers & cod_acquirer
        else:
            return compatible_acquirers - cod_acquirer
