# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

import base64


@tagged('post_install', '-at_install')
class TestAccountBankStatementImportOFX(AccountTestInvoicingCommon):

    def test_ofx_file_import(self):
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '123456',
            'currency_id': self.env.ref('base.USD').id,
        })

        partner_norbert = self.env['res.partner'].create({
            'name': 'Norbert Brant',
            'is_company': True,
        })
        bank_norbert = self.env['res.bank'].create({'name': 'test'})
        partner_bank_norbert = self.env['res.partner.bank'].create({
            'acc_number': 'BE93999574162167',
            'partner_id': partner_norbert.id,
            'bank_id': bank_norbert.id,
        })

        # Get OFX file content
        ofx_file_path = get_module_resource('account_bank_statement_import_ofx', 'static/ofx', 'test_ofx.ofx')
        ofx_file = base64.b64encode(open(ofx_file_path, 'rb').read())

        # Use an import wizard to process the file
        self.env['account.bank.statement.import']\
            .with_context(journal_id=bank_journal.id)\
            .create({'attachment_ids': [(0, 0, {'name': 'test_ofx.ofx', 'datas': ofx_file})]})\
            .import_file()

        # Check the imported bank statement
        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_ofx.ofx',
            'balance_start': 2516.56,
            'balance_end_real': 2156.56,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted('payment_ref'), [
            {
                'payment_ref': 'Axelor Scuba',
                'amount': -100.0,
                'partner_id': False,
                'partner_bank_id': False,
            },
            {
                'payment_ref': 'China Export',
                'amount': -90.0,
                'partner_id': False,
                'partner_bank_id': False,
            },
            {
                'payment_ref': 'China Scuba',
                'amount': -90.0,
                'partner_id': False,
                'partner_bank_id': False,
            },
            {
                'payment_ref': partner_norbert.name,
                'amount': -80.0,
                'partner_id': partner_norbert.id,
                'partner_bank_id': partner_bank_norbert.id,
            },
        ])
