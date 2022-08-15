# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2012 Noviat nv/sa (www.noviat.be). All rights reserved.
import base64

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.modules.module import get_module_resource
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCodaFile(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.bank_journal = cls.company_data['default_journal_bank']

        coda_file_path = get_module_resource('l10n_be_coda', 'test_coda_file', 'Ontvangen_CODA.2013-01-11-18.59.15.txt')
        cls.coda_file = base64.b64encode(open(coda_file_path, 'rb').read())

        cls.statement_import_model = cls.env['account.bank.statement.import']
        cls.bank_statement_model = cls.env['account.bank.statement']

    def test_coda_file_import(self):
        self.env['account.bank.statement.import']\
            .with_context(journal_id=self.company_data['default_journal_bank'].id)\
            .create({'attachment_ids': [(0, 0, {'name': 'test file', 'datas': self.coda_file})]})\
            .import_file()

        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'balance_start': 11812.70,
            'balance_end_real': 13646.05,
        }])

    def test_coda_file_import_twice(self):
        self.env['account.bank.statement.import']\
            .with_context(journal_id=self.company_data['default_journal_bank'].id)\
            .create({'attachment_ids': [(0, 0, {'name': 'test file', 'datas': self.coda_file})]})\
            .import_file()

        with self.assertRaises(Exception):
            self.env['account.bank.statement.import']\
                .with_context(journal_id=self.company_data['default_journal_bank'].id)\
                .create({'attachment_ids': [(0, 0, {'name': 'test file', 'datas': self.coda_file})]})\
                .import_file()

    def test_coda_file_wrong_journal(self):
        with self.assertRaises(Exception):
            self.env['account.bank.statement.import']\
                .with_context(journal_id=self.company_data['default_journal_misc'].id)\
                .create({'attachment_ids': [(0, 0, {'name': 'test file', 'datas': self.coda_file})]})\
                .import_file()
