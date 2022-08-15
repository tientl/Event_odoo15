# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields

from odoo.addons.payment.tests.common import PaymentCommon


class SepaDirectDebitCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company = cls.env.company
        cls.company.sdd_creditor_identifier = 'BE30ZZZ300D000000042'
        bank_ing = cls.env['res.bank'].create({'name': 'ING', 'bic': 'BBRUBEBB'})

        cls.sepa_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'NL91 ABNA 0417 1643 00',
            'partner_id': cls.company.partner_id.id,
            'bank_id': bank_ing.id,
        })

        assert cls.sepa_bank_account.acc_type == 'iban'

        cls.sepa = cls._prepare_acquirer('sepa_direct_debit', update_values={
            'sdd_sms_verification_required': True, # Needed for test ???
        })
        cls.sepa_journal = cls.sepa.journal_id
        cls.sepa_journal.bank_account_id = cls.sepa_bank_account

        # create the partner bank account
        cls.partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE17412614919710',
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
        })

        cls.mandate = cls.env['sdd.mandate'].create({
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
            'partner_bank_id': cls.partner_bank.id,
            'start_date': fields.Date.today(),
            'payment_journal_id': cls.sepa_journal.id,
            'verified': True,
            'state': 'active',
        })

        cls.acquirer = cls.sepa
        cls.currency = cls.currency_euro

    def reconcile(self, payment):
        bank_journal = payment.journal_id
        move_line = payment.line_ids.filtered(lambda aml: aml.account_id == bank_journal.company_id.account_journal_payment_debit_account_id)

        bank_stmt = self.env['account.bank.statement'].create({
            'journal_id': bank_journal.id,
            'date': payment.date,
            'name': payment.name,
            'line_ids': [(0, 0, {
                'partner_id': self.partner.id,
                'foreign_currency_id': move_line.currency_id.id,
                'amount_currency': abs(move_line.amount_currency),
                'amount': abs(move_line.balance),
                'date': payment.date,
                'payment_ref': payment.name,
            })],
        })
        bank_stmt.button_post()
        bank_stmt.line_ids.reconcile([{'id': move_line.id}])

        self.assertTrue(payment.is_matched, 'payment should be reconciled')
