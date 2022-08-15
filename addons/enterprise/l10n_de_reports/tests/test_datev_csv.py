# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged
from odoo.tools import pycompat
import io

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDateCSV(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref='l10n_de_skr03.l10n_de_chart_template')

        account_3400 = cls.env['account.account'].search([
            ('code', '=', 3400),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        account_4980 = cls.env['account.account'].search([
            ('code', '=', 4980),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        tax_19 = cls.env['account.tax'].search([
            ('name', '=', '19% Vorsteuer'),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        invoices = cls.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.to_date('2020-12-01'),
                'invoice_line_ids': [
                    (0, None, {
                        'price_unit': 100,
                        'account_id': account_3400.id,
                        'tax_ids': [(6, 0, tax_19.ids)],
                    }),
                    (0, None, {
                        'price_unit': 100,
                        'account_id': account_3400.id,
                        'tax_ids': [(6, 0, tax_19.ids)],
                    }),
                    (0, None, {
                        'price_unit': 100,
                        'account_id': account_4980.id,
                        'tax_ids': [(6, 0, tax_19.ids)],
                    }),
                ]
            },
        ])
        invoices.action_post()

    def test_datev_csv(self):
        report = self.env['account.general.ledger']
        options = report._get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        reader = pycompat.csv_reader(io.BytesIO(report.get_csv(options)), delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[8], x[9], x[10], x[11], x[13]] for x in reader][2:]
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['238,00', 's', 'EUR', '34000000', '19', '112', 'BILL/2020/12/0001', '', 'BILL/2020/12/0001'], data)
        self.assertIn(['119,00', 's', 'EUR', '49800000', '19', '112', 'BILL/2020/12/0001', '', 'BILL/2020/12/0001'], data)
