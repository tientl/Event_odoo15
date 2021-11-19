# -*- coding: utf-8 -*-

from odoo import models, fields

from ..models.account_invoice import DESCRIPTION_DEBIT_CODE


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_co_edi_description_code_debit = fields.Selection(DESCRIPTION_DEBIT_CODE,
                                                          string="Concepto Nota de Débito", help="Colombian code for Debit Notes")

    def create_debit(self):
        action = super(AccountDebitNote, self).create_debit()
        if action.get('res_id'):
            debit_move = self.env['account.move'].browse(action['res_id'])
            debit_move.l10n_co_edi_description_code_debit = self.l10n_co_edi_description_code_debit
            debit_move.l10n_co_edi_operation_type = '30'
        return action
