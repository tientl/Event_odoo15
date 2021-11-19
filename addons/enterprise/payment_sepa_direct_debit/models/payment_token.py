# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    sdd_mandate_id = fields.Many2one(
        string="SEPA Direct Debit Mandate", comodel_name='sdd.mandate', readonly=True,
        ondelete='set null')

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that SEPA tokens cannot be restored.

        A SEPA token might be archived for several reasons:
          - It was archived manually by the customer.
          - The commercial partner of the token's partner was updated, hence invalidating the token.
          - The SDD mandate was closed or revoked, hence invalidating the token.
        As we don't distinguish those cases, we block the reactivation of every token.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the token is managed by SEPA
        """
        super()._handle_reactivation_request()
        if self.provider != 'sepa_direct_debit':
            return

        raise UserError(_("Saved payment methods cannot be restored once they have been archived."))
