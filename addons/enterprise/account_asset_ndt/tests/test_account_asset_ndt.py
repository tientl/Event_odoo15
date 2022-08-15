# -*- coding: utf-8 -*-

from freezegun import freeze_time
from odoo import fields, Command
from odoo.tests.common import Form, tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@freeze_time('2021-05-12')
@tagged('post_install', '-at_install')
class TestAccountAsset(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccountAsset, cls).setUpClass()
        today = fields.Date.today()

        cls.account_asset_model_fixedassets = cls.env['account.asset'].create({
            'account_depreciation_id': cls.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'name': 'Hardware - 3 Years',
            'method_number': 3,
            'method_period': '12',
            'state': 'model',
        })

        cls.non_deductible_tax = cls.env['account.tax'].create({
            'name': 'Non-deductible Tax',
            'amount': 21,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True
                }),
            ],
        })

    def test_asset_with_non_deductible_tax(self):
        """Test that the assets' original_value and non_deductible_tax_value are correctly computed
        from a move line with a non-deductible tax."""

        asset_account = self.company_data['default_account_assets']
        asset_account.tax_ids = self.non_deductible_tax

        # 1. Automatic creation
        asset_account.create_asset = 'draft'
        asset_account.asset_model = self.account_asset_model_fixedassets.id
        asset_account.multiple_assets_per_line = True

        vendor_bill_auto = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-12-31',
            'partner_id': self.ref("base.res_partner_12"),
            'invoice_line_ids': [Command.create({
                'account_id': asset_account.id,
                'name': 'Asus Laptop',
                'price_unit': 1000.0,
                'quantity': 2,
                'tax_ids': [Command.set(self.non_deductible_tax.ids)],
            })],
        })
        vendor_bill_auto.action_post()

        new_assets_auto = vendor_bill_auto.asset_ids
        self.assertEqual(len(new_assets_auto), 2)
        self.assertEqual(new_assets_auto.mapped('original_value'), [1105.0, 1105.0])
        self.assertEqual(new_assets_auto.mapped('non_deductible_tax_val'), [105.0, 105.0])

        # 2. Manual creation
        asset_account.create_asset = 'no'
        asset_account.asset_model = None
        asset_account.multiple_assets_per_line = False

        vendor_bill_manu = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-12-31',
            'partner_id': self.ref("base.res_partner_12"),
            'invoice_line_ids': [
                Command.create({
                    'account_id': asset_account.id,
                    'name': 'Asus Laptop',
                    'price_unit': 1000.0,
                    'quantity': 2,
                    'tax_ids': [Command.set(self.non_deductible_tax.ids)]
                }),
                Command.create({
                    'account_id': asset_account.id,
                    'name': 'Lenovo Laptop',
                    'price_unit': 500.0,
                    'quantity': 3,
                    'tax_ids': [Command.set(self.non_deductible_tax.ids)]
                }),
            ],
        })
        vendor_bill_manu.action_post()

        move_line_ids = vendor_bill_manu.mapped('line_ids').filtered(lambda x: 'Laptop' in x.name)
        asset_form = Form(self.env['account.asset'].with_context(
            default_original_move_line_ids=move_line_ids.ids,
            asset_type='purchase'
        ))
        asset_form._values['original_move_line_ids'] = [Command.set(move_line_ids.ids)]
        asset_form._perform_onchange(['original_move_line_ids'])
        asset_form.account_depreciation_expense_id = self.company_data['default_account_expense']

        new_assets_manu = asset_form.save()
        self.assertEqual(len(new_assets_manu), 1)
        self.assertEqual(new_assets_manu.original_value, 3867.5)
        self.assertEqual(new_assets_manu.non_deductible_tax_val, 367.5)
