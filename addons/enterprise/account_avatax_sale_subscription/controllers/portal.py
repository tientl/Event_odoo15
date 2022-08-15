# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.addons.sale_subscription.controllers.portal import SaleSubscription, PaymentPortal

class SaleSubscriptionAvatax(SaleSubscription):
    @http.route()
    def subscription(self, subscription_id, access_token='', message='', message_class='', **kw):
        response = super().subscription(subscription_id, access_token=access_token, message=message, message_class=message_class, **kw)

        if 'account' not in response.qcontext:
            return response

        sub = response.qcontext['account']
        if sub.is_avatax:
            sub.button_update_avatax()

        return response


class PaymentPortalAvatax(PaymentPortal):
    def _create_invoice(self, subscription):
        res = super()._create_invoice(subscription)
        res.button_update_avatax()
        return res

