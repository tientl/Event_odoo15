# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        """ Override of account_sepa_direct_debit to mark the related transactions as done. """
        res = super().reconcile()

        involved_payments = self.move_id.payment_id
        tx_ids = self.env['payment.transaction'].sudo().search([
            ('state', '=', 'pending'),
            ('acquirer_id.provider', '=', 'sepa_direct_debit'),
            ('payment_id', 'in', involved_payments.filtered('is_matched').ids),
        ]).ids
        txs = self.env['payment.transaction'].browse(tx_ids)
        txs._set_done()
        # Since the payment confirmation does not come from a provider notification, we reproduce
        # the processing of the `_handle_feedback_data` method here and trigger the post-processing.
        txs._execute_callback()
        txs._finalize_post_processing()

        return res
