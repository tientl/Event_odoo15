# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    #=== BUSINESS METHODS ===#

    def _send_payment_request(self):
        """ Override of payment to create the related `account.payment` and notify the customer.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        :raise: UserError if the transaction is not linked to a valid mandate
        """
        super()._send_payment_request()
        if self.provider != 'sepa_direct_debit':
            return

        if not self.token_id:
            raise UserError("SEPA: " + _("The transaction is not linked to a token."))

        mandate = self.token_id.sdd_mandate_id
        if not mandate:
            raise UserError("SEPA: " + _("The token is not linked to a mandate."))
        if not mandate.verified \
                or mandate.state != 'active' \
                or (mandate.end_date and mandate.end_date > fields.Datetime.now()):
            raise UserError("SEPA: " + _("The mandate is invalid."))

        # Since there is no provider to send a payment request to, the processing of the
        # `_handle_feedback_data` method is reproduced here.
        if self.operation == 'validation':
            self._set_done()
            self._execute_callback()
        else:
            self._set_pending()  # Remain in pending until the account.payment is reconciled
            self._execute_callback()
            self._sdd_notify_debit(self.token_id)

            # As the transaction is set in pending, the processing of the
            # `_finalize_post_processing` method is reproduced here as well.
            payment_method_line = mandate.payment_journal_id.inbound_payment_method_line_ids\
                .filtered(lambda l: l.code == 'sdd')
            self._create_payment(
                payment_method_line_id=payment_method_line.id,
                sdd_mandate_id=mandate.id,
            )

    def _sdd_notify_debit(self, token):
        """ Notify the customer that a debit has been made from his account.

        This is required as per the SEPA Direct Debit rulebook.
        The notice must include:
            - the last 4 digits of the debtor’s bank account
            - the mandate reference
            - the amount to be debited
            - your SEPA creditor identifier
            - your contact information
        Notifications should be sent at least 14 calendar days before the payment is created unless
        specified otherwise.

        :param recordset token: The token linked to the mandate from which the debit has been made,
                                as a `payment.token` record
        :return: None
        """
        iban = token.sdd_mandate_id.partner_bank_id.acc_number.replace(' ', '')
        obfuscated_iban = payment_utils.build_token_name(
            payment_details_short=iban[-4:], final_length=len(iban)
        )
        ctx = self.env.context.copy()
        ctx.update({
            'iban': obfuscated_iban,
            'mandate_ref': token.sdd_mandate_id.name,
            'creditor_identifier': self.env.company.sdd_creditor_identifier,
        })
        template = self.env.ref('payment_sepa_direct_debit.mail_template_sepa_notify_debit')
        template.with_context(ctx).send_mail(self.id)
