# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

import base64


@tagged('post_install', '-at_install')
class TestAccountBankStatementImportQIF(AccountTestInvoicingCommon):

    def test_qif_file_import(self):
        bank_journal = self.env['account.journal'].create({
            'name': 'bank QIF',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '123456',
            'currency_id': self.env.ref('base.USD').id,
        })

        qif_file_path = get_module_resource('account_bank_statement_import_qif', 'static/qif', 'test_qif.qif')
        qif_file = base64.b64encode(open(qif_file_path, 'rb').read())

        self.env['account.bank.statement.import']\
            .with_context(journal_id=bank_journal.id)\
            .create({'attachment_ids': [(0, 0, {'name': 'test file', 'datas': qif_file})]})\
            .import_file()

        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'balance_start': 0.0,
            'balance_end_real': -1896.09,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted('payment_ref'), [
            {'amount': -1000.00,    'payment_ref': 'Delta PC'},
            {'amount': -379.00,     'payment_ref': 'Epic Technologies'},
            {'amount': -421.35,     'payment_ref': 'SPRINGFIELD WATER UTILITY'},
            {'amount': -75.46,      'payment_ref': 'Walts Drugs'},
            {'amount': -20.28,      'payment_ref': 'YOUR LOCAL SUPERMARKET'},
        ])
