# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools.misc import formatLang, format_date

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    ####################################################
    # Public
    ####################################################

    @api.model
    def get_move_lines_by_batch_payment(self, st_line_id, batch_payment_id):
        """ As get_move_lines_for_bank_statement_line, but returns lines from a batch deposit """
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)

        # Fetch blue lines for this batch.
        query, params = self._get_query_reconciliation_widget_liquidity_lines(st_line, domain=[('payment_id.batch_payment_id', '=', batch_payment_id)])
        self._cr.execute(query, params)

        # Convert to js dictionaries.
        move_lines = self.env['account.move.line'].browse(res['id'] for res in self._cr.dictfetchall())
        return [self._prepare_js_reconciliation_widget_move_line(st_line, line) for line in move_lines]

    @api.model
    def get_batch_payments_data(self, bank_statement_ids):
        """ Return a list of dicts containing informations about unreconciled batch deposits """

        Batch_payment = self.env['account.batch.payment']

        batch_payments = []
        batch_payments_domain = [('state', '!=', 'reconciled')]
        for batch_payment in Batch_payment.search(batch_payments_domain, order='id asc'):
            payments = batch_payment.payment_ids
            journal = batch_payment.journal_id
            company_currency = journal.company_id.currency_id
            journal_currency = journal.currency_id or company_currency

            amount_journal_currency = formatLang(self.env, batch_payment.amount, currency_obj=journal_currency)
            amount_payment_currency = False
            # If all the payments of the deposit are in another currency than the journal currency, we'll display amount in both currencies
            if payments and all(p.currency_id != journal_currency and p.currency_id == payments[0].currency_id for p in payments):
                amount_payment_currency = sum(p.amount for p in payments)
                amount_payment_currency = formatLang(self.env, amount_payment_currency, currency_obj=payments[0].currency_id or company_currency)

            batch_payments.append({
                'id': batch_payment.id,
                'name': batch_payment.name,
                'date': format_date(self.env, batch_payment.date),
                'journal_id': journal.id,
                'amount': batch_payment.amount * (1 if batch_payment.batch_type == 'inbound' else -1),
                'amount_str': amount_journal_currency,
                'amount_currency_str': amount_payment_currency,
            })
        return batch_payments

    @api.model
    def get_bank_statement_data(self, bank_statement_line_ids, srch_domain=[]):
        """ Add batch payments data to the dict returned """
        res = super(AccountReconciliation, self).get_bank_statement_data(bank_statement_line_ids, srch_domain)
        res.update({'batch_payments': self.get_batch_payments_data(bank_statement_line_ids)})
        return res
