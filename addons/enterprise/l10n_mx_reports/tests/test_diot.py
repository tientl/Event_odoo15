# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestDiot(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_mx.mx_coa'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.purchase_taxes = cls._get_purchase_taxes()

        cls.partner_a.write({'country_id': cls.env.ref('base.mx').id, 'l10n_mx_type_of_operation': '85', 'vat': 'XAXX010101000'})
        cls.partner_b.write({'country_id': cls.env.ref('base.us').id, 'l10n_mx_type_of_operation': '85'})

    @classmethod
    def _get_purchase_taxes(cls):
        taxes = cls.env['account.tax']
        for i in [1, 2, 7, 8, 13, 14, 16]:
            taxes += cls.env.ref(f'l10n_mx.{cls.env.company.id}_tax{i}')

        return taxes

    def test_diot_report(self):
        date_invoice = '2022-07-01'
        moves_vals = []
        for i, tax in enumerate(self.purchase_taxes):
            for partner in (self.partner_a, self.partner_b):
                moves_vals += [
                    {
                        'move_type': 'in_invoice',
                        'partner_id': partner.id,
                        'invoice_date': date_invoice,
                        'date': date_invoice,
                        'invoice_line_ids': [(0, 0, {
                            'name': f'test {tax.amount}',
                            'quantity': 1,
                            'price_unit': 10 + 1 * i,
                            'tax_ids': [(6, 0, tax.ids)],
                        })]
                    },
                    {
                        'move_type': 'in_refund',
                        'partner_id': partner.id,
                        'invoice_date': date_invoice,
                        'date': date_invoice,
                        'invoice_line_ids': [(0, 0, {
                            'name': f'test {tax.amount}',
                            'quantity': 1,
                            'price_unit': 10 + 2 * i,
                            'tax_ids': [(6, 0, tax.ids)],
                        })]
                    },
                ]

        moves = self.env['account.move'].create(moves_vals)
        moves.action_post()

        for move in moves:
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
                'payment_date': date_invoice,
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_method_line_id': self.env.ref('account.account_payment_method_manual_in').id,
                'amount': move.amount_total,
            })._create_payments()

        self.assertTrue(all(m.payment_state in ('paid', 'in_payment') for m in moves))

        report = self.env['l10n_mx.account.diot']

        options = self._init_options(report, fields.Date.from_string('2022-01-01'), fields.Date.from_string('2022-12-31'))
        options['unfolded_lines'] = [f"partner_{self.partner_a.id}", f"partner_{self.partner_b.id}"]

        self.assertLinesValues(
            report._get_lines(options),
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
            [
                # pylint: disable=C0326
                ("04", "85", "XAXX010101000", "MX",  "Mexican", 15.0, 0.0, 16.0, 0.0, 0.0, 14.0, 0.0,  1.0, 60.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0, 22.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0, 16.0, 0.0, 0.0,  0.0, 0.0,  0.0,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0, 20.0),
                (  "",   "",              "",   "",         "", 15.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0, 18.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0, 14.0, 0.0,  0.0,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.71,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.39,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.49,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.28,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.20,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.10,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.4,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.4,  0.0),
                ("04", "85", "XAXX010101000", "MX",  "Mexican", 15.0, 0.0, 16.0, 0.0, 0.0, 14.0, 0.0, 0.63, 60.0),
                ("05", "85",              "", "US", "American", 15.0, 0.0, 16.0, 0.0, 0.0, 14.0, 0.0,  1.0, 60.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0, 22.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0, 16.0, 0.0, 0.0,  0.0, 0.0,  0.0,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0, 20.0),
                (  "",   "",              "",   "",         "", 15.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.0, 18.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0, 14.0, 0.0,  0.0,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.71,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.39,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.49,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.28,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.20,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 1.10,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.4,  0.0),
                (  "",   "",              "",   "",         "",  0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0,  0.4,  0.0),
                ("05", "85",              "", "US", "American", 15.0, 0.0, 16.0, 0.0, 0.0, 14.0, 0.0, 0.63, 60.0),
            ]
        )

        self.assertEqual(report.get_txt(options), """04|85|XAXX010101000|||||15|||||16||||||||14||1|60|
05|85|||partnerb|US|American|15|||||16||||||||14||1|60|
""")

        self.assertEqual(report.get_txt({**options, 'is_dpiva': True}), """|1.0|2022|MES|January|1|1|||14|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|04|85|XAXX010101000|||||15|||16||||||||14||1|60|
|1.0|2022|MES|January|1|1|||14|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|05|85|||partnerb|US|American|15|||16||||||||14||1|60|
""")
