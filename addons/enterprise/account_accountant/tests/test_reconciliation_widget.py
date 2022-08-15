import logging
import odoo.tests
import time
from odoo.addons.account.tests.common import TestAccountReconciliationCommon
from odoo import fields
from odoo.tools.misc import NON_BREAKING_SPACE

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
class TestReconciliationWidget(TestAccountReconciliationCommon):

    def _get_st_widget_suggestions(self, st_line, mode='rp'):
        suggestions = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(st_line.id, mode=mode)
        return self.env['account.move.line'].browse([x['id'] for x in suggestions])

    def test_statement_suggestion_other_currency(self):
        # company currency is EUR
        # payment in USD
        invoice = self.create_invoice(invoice_amount=50, currency_id=self.currency_usd_id)

        # journal currency in USD
        bank_stmt = self.env['account.bank.statement'].create({
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'payment %s' % invoice.name,
            'line_ids': [(0, 0, {
                'payment_ref': 'payment',
                'partner_id': self.partner_agrolait_id,
                'amount': 50,
                'date': time.strftime('%Y-07-15'),
            })],
        })

        bank_stmt.button_post()

        result = self.env['account.reconciliation.widget'].get_bank_statement_line_data(bank_stmt.line_ids.ids)
        self.assertEqual(result['lines'][0]['reconciliation_proposition'][0]['amount_str'], f'${NON_BREAKING_SPACE}50.00')

    def test_filter_partner1(self):
        inv1 = self.create_invoice(currency_id=self.currency_euro_id)
        inv2 = self.create_invoice(currency_id=self.currency_euro_id)
        partner = inv1.partner_id

        receivable1 = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        receivable2 = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        bank_stmt = self.env['account.bank.statement'].create({
            'company_id': self.company.id,
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'test',
        })

        bank_stmt_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'testLine',
            'statement_id': bank_stmt.id,
            'amount': 100,
            'date': time.strftime('%Y-07-15'),
        })

        # This is like input a partner in the widget
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=partner.id,
            excluded_ids=[],
            search_str=False,
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

        # With a partner set, type the invoice reference in the filter
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=partner.id,
            excluded_ids=[],
            search_str=inv1.payment_reference,
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertNotIn(receivable2.id, mv_lines_ids)

        # Without a partner set, type "deco" in the filter
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=False,
            excluded_ids=[],
            search_str="deco",
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

        # With a partner set, type "deco" in the filter and click on the first receivable
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=partner.id,
            excluded_ids=[receivable1.id],
            search_str="deco",
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertNotIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

    def test_partner_name_with_parent(self):
        parent_partner = self.env['res.partner'].create({
            'name': 'test',
        })
        child_partner = self.env['res.partner'].create({
            'name': 'test',
            'parent_id': parent_partner.id,
            'type': 'delivery',
        })
        self.create_invoice_partner(currency_id=self.currency_euro_id, partner_id=child_partner.id)

        bank_stmt = self.env['account.bank.statement'].create({
            'company_id': self.company.id,
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'test',
        })

        bank_stmt_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'testLine',
            'statement_id': bank_stmt.id,
            'amount': 100,
            'date': time.strftime('%Y-07-15'),
            'partner_name': 'test',
        })

        bkstmt_data = self.env['account.reconciliation.widget'].get_bank_statement_line_data(bank_stmt_line.ids)

        self.assertEqual(len(bkstmt_data['lines']), 1)
        self.assertEqual(bkstmt_data['lines'][0]['partner_id'], parent_partner.id)

    def test_reconciliation_process_move_lines_with_mixed_currencies(self):
        # Delete any old rate - to make sure that we use the ones we need.
        old_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_usd_id)])
        old_rates.unlink()

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })

        move_product = self.env['account.move'].create({
            'ref': 'move product',
        })
        move_product_lines = self.env['account.move.line'].create([
            {
                'name': 'line product',
                'move_id': move_product.id,
                'account_id': self.env['account.account'].search([
                    ('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id),
                    ('company_id', '=', self.company.id)
                ], limit=1).id,
                'debit': 20,
                'credit': 0,
            },
            {
                'name': 'line receivable',
                'move_id': move_product.id,
                'account_id': self.account_rcv.id,
                'debit': 0,
                'credit': 20,
            }
        ])
        move_product.action_post()

        move_payment = self.env['account.move'].create({
            'ref': 'move payment',
        })
        liquidity_account = self.env['account.account'].search([
            ('user_type_id', '=', self.env.ref('account.data_account_type_liquidity').id),
            ('company_id', '=', self.company.id)], limit=1)
        move_payment_lines = self.env['account.move.line'].create([
            {
                'name': 'line product',
                'move_id': move_payment.id,
                'account_id': liquidity_account.id,
                'debit': 10.0,
                'credit': 0,
                'amount_currency': 20,
                'currency_id': self.currency_usd_id,
            },
            {
                'name': 'line product',
                'move_id': move_payment.id,
                'account_id': self.account_rcv.id,
                'debit': 0,
                'credit': 10.0,
                'amount_currency': -20,
                'currency_id': self.currency_usd_id,
            }
        ])
        move_payment.action_post()

        # We are reconciling a move line in currency A with a move line in currency B and putting
        # the rest in a writeoff, this test ensure that the debit/credit value of the writeoff is
        # correctly computed in company currency.
        self.env['account.reconciliation.widget'].process_move_lines([{
            'id': False,
            'type': False,
            'mv_line_ids': [move_payment_lines[1].id, move_product_lines[1].id],
            'new_mv_line_dicts': [{
                'account_id': liquidity_account.id,
                'analytic_tag_ids': [(6, None, [])],
                'credit': 0,
                'date': time.strftime('%Y') + '-01-01',
                'debit': 15.0,
                'journal_id': self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.company.id)], limit=1).id,
                'name': 'writeoff',
            }],
        }])

        writeoff_line = self.env['account.move.line'].search([('name', '=', 'writeoff'), ('company_id', '=', self.company.id)])
        self.assertEqual(writeoff_line.credit, 15.0)

    def test_inv_refund_foreign_payment_writeoff_domestic(self):
        company = self.company
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.113900,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id
        })
        inv1 = self.create_invoice(invoice_amount=480, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(move_type="out_refund", invoice_amount=140, currency_id=self.currency_usd_id)

        payment = self.env['account.payment'].create({
            'payment_method_line_id': self.inbound_payment_method_line.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 287.20,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
        })
        payment.action_post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        data_for_reconciliation = [
            {
                'type': 'partner',
                'id': inv1.partner_id.id,
                'mv_line_ids': (inv1_receivable + inv2_receivable + pay_receivable).ids,
                'new_mv_line_dicts': [
                    {
                        'credit': 18.04,
                        'debit': 0.00,
                        'journal_id': self.bank_journal_euro.id,
                        'name': 'Total WriteOff (Fees)',
                        'account_id': self.diff_expense_account.id
                    }
                ]
            }
        ]

        self.env["account.reconciliation.widget"].process_move_lines(data_for_reconciliation)

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)

        self.assertTrue(all(l.reconciled for l in inv1_receivable))
        self.assertTrue(all(l.reconciled for l in inv2_receivable))

        self.assertEqual(inv1.payment_state, 'in_payment')
        self.assertEqual(inv2.payment_state, 'paid')

    def test_get_reconciliation_dict_with_tag_ids(self):
        bank_stmt = self.env['account.bank.statement'].create({
            'company_id': self.company.id,
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'test',
        })
        bank_stmt_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'testLine',
            'statement_id': bank_stmt.id,
            'amount': 100,
            'date': time.strftime('%Y-07-15'),
            'partner_name': 'test',
        })
        tax = self.tax_purchase_a.copy()
        tax.refund_repartition_line_ids[0].write({
            'tag_ids': [(0, 0, {
                'name': 'the_tag',
                'applicability': 'taxes',
                'country_id': tax.country_id.id,
            })]
        })
        reconciliation_model = self.env['account.reconcile.model'].create({
            'name': 'Charge with Tax',
            'company_id': self.company.id,
            'line_ids': [(0, 0, {
                'company_id': self.company.id,
                'account_id': self.company_data['default_account_expense'].id,
                'amount_type': 'percentage',
                'amount_string': '100',
                'tax_ids': [(6, 0, [tax.id])]
            })]
        })
        res = self.env["account.reconciliation.widget"].get_reconciliation_dict_from_model(reconciliation_model.id, bank_stmt_line.id, -bank_stmt_line.amount, bank_stmt_line.partner_id)

        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['tax_ids'][0]['id'], tax.id)
        self.assertTrue('id' in res[0]['tax_tag_ids'][0])
        self.assertEqual(res[0]['tax_tag_ids'][0]['display_name'], 'the_tag')

    def test_writeoff_single_entry(self):
        """ Test writeoff are grouped by journal and date in common journal entries"""
        today = fields.Date.today().strftime('%Y-07-15')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax_purchase_a.ids)],
            })]
        })
        invoice.action_post()

        ctx = {'active_model': 'account.move', 'active_ids': invoice.ids}
        payment_register = self.env['account.payment.register'].with_context(**ctx).create({
            'amount': 1161.5,
        })
        payment_vals = payment_register._create_payment_vals_from_wizard()
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # Create a write-off for the residual amount.
        account = self.company_data['default_account_receivable']
        lines = (invoice + payment.move_id).line_ids.filtered(lambda line: line.account_id == account)

        self.env['account.reconciliation.widget'].process_move_lines([{
            'type': 'other',
            'mv_line_ids': lines.ids,
            'new_mv_line_dicts': [
                {
                    'name': 'TEST',
                    'journal_id': self.company_data['default_journal_misc'].id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'balance': 10,
                    'date': today,
                    'tax_ids': [(6, 0, self.tax_purchase_a.ids)],
                },
                {
                    'name': 'TEST TAX',
                    'journal_id': self.company_data['default_journal_misc'].id,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'date': today,
                    'balance': 1.5,
                    'tax_base_amount': -10,
                    'tax_repartition_line_id': self.tax_purchase_a.invoice_repartition_line_ids.filtered('account_id').id
                }
            ]}])

        self.assertTrue(all(line.reconciled for line in lines))

        write_off = lines.full_reconcile_id.reconciled_line_ids.move_id - lines.move_id

        self.assertEqual(len(write_off), 1, "It should create only a single journal entry")

        self.assertRecordValues(write_off.line_ids.sorted('balance'), [
            {
                'partner_id': self.partner_a.id,
                'debit': 0.0,
                'credit': 10,
            },
            {
                'partner_id': self.partner_a.id,
                'debit': 0.0,
                'credit': 1.5,
            },
            {
                'partner_id': self.partner_a.id,
                'debit': 1.5,
                'credit': 0.0,
            },
            {
                'partner_id': self.partner_a.id,
                'debit': 10,
                'credit': 0.0,
            },
        ])

    def test_prepare_writeoff_moves_multi_currency(self):
        for invoice_type in ('out_invoice', 'in_invoice'):
            # Create an invoice at rate 1:2.
            invoice = self.env['account.move'].create({
                'move_type': invoice_type,
                'partner_id': self.partner_a.id,
                'currency_id': self.currency_data['currency'].id,
                'invoice_date': '2019-01-21',
                'date': '2019-01-21',
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                })]
            })
            invoice.action_post()

            # Create a payment at rate 1:2.
            ctx = {'active_model': 'account.move', 'active_ids': invoice.ids}
            payment_register = self.env['account.payment.register'].with_context(**ctx).create({
                'amount': 800.0,
                'currency_id': self.currency_data['currency'].id,
            })
            payment_vals = payment_register._create_payment_vals_from_wizard()
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()

            # Create a write-off for the residual amount.
            account = invoice.line_ids\
                .filtered(lambda line: line.account_id.internal_type in ('receivable', 'payable')).account_id
            lines = (invoice + payment.move_id).line_ids.filtered(lambda line: line.account_id == account)
            write_off_vals = self.env['account.reconciliation.widget']._prepare_writeoff_moves(lines, {
                'journal_id': self.company_data['default_journal_misc'].id,
                'account_id': self.company_data['default_account_revenue'].id,
            })
            write_off = self.env['account.move'].create(write_off_vals)
            write_off.action_post()

            self.assertRecordValues(write_off.line_ids.sorted('balance'), [
                {
                    'partner_id': self.partner_a.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                },
                {
                    'partner_id': self.partner_a.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                },
            ])

            # Reconcile.
            all_lines = (invoice + payment.move_id + write_off).line_ids.filtered(lambda line: line.account_id == account)
            all_lines.reconcile()

            for line in all_lines:
                self.assertTrue(line.reconciled)

    def test_st_line_suggestion_manual_reimbursement_with_st_line(self):
        statement = self.env['account.bank.statement'].create({
            'name': 'test',
            'date': '2019-01-01',
            'balance_end_real': 0.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {
                    'payment_ref': 'line2',
                    'amount': -100.0,
                    'date': '2019-01-01',
                }),
                (0, 0, {
                    'payment_ref': 'line1',
                    'amount': 100.0,
                    'date': '2019-01-01',
                }),
            ],
        })
        statement.button_post()

        line1 = statement.line_ids[0]
        line2 = statement.line_ids[1]

        # Reconcile it with a payable account.
        line1.reconcile([{
            'name': "whatever",
            'account_id': self.company_data['default_account_payable'].id,
            'balance': 100.0,
        }])

        suggested_amls = self._get_st_widget_suggestions(line2, mode='rp')
        self.assertRecordValues(suggested_amls, [{'statement_line_id': line1.id}])

        suggested_amls = self._get_st_widget_suggestions(line2, mode='misc')
        self.assertFalse(suggested_amls)

    def test_st_line_suggestion_reconcile_account_on_bank_journal(self):
        self.company_data['default_account_assets'].reconcile = True

        internal_transfer = self.env['account.move'].create({
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'line1',
                    'account_id': self.company_data['default_journal_bank'].default_account_id.id,
                    'debit': 1000.0,
                }),
                (0, 0, {
                    'name': 'line1',
                    'account_id': self.company_data['default_account_assets'].id,
                    'credit': 1000.0,
                }),
            ],
        })
        internal_transfer.action_post()

        statement = self.env['account.bank.statement'].create({
            'name': 'test',
            'date': '2019-01-01',
            'balance_end_real': -1000.0,
            'journal_id': self.company_data['default_journal_cash'].id,
            'line_ids': [
                (0, 0, {
                    'payment_ref': 'line2',
                    'amount': -1000.0,
                    'date': '2019-01-01',
                }),
            ],
        })
        statement.button_post()

        suggested_amls = self._get_st_widget_suggestions(statement.line_ids, mode='rp')
        self.assertFalse(suggested_amls)

        suggested_amls = self._get_st_widget_suggestions(statement.line_ids, mode='misc')
        self.assertRecordValues(suggested_amls, [{
            'move_id': internal_transfer.id,
            'account_id': self.company_data['default_account_assets'].id,
        }])

    def test_st_line_suggestion_reconcile_with_payment(self):
        statement = self.env['account.bank.statement'].create({
            'name': 'test',
            'date': '2019-01-01',
            'balance_end_real': -1000.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {
                    'payment_ref': 'line2',
                    'amount': -1000.0,
                    'date': '2019-01-01',
                }),
            ],
        })
        statement.button_post()

        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'date': '2019-01-01',
            'amount': 1000.0,
            'currency_id': self.env.company.currency_id.id,
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        suggested_amls = self._get_st_widget_suggestions(statement.line_ids, mode='rp')
        self.assertRecordValues(suggested_amls, [{
            'payment_id': payment.id,
            'account_id': self.company_data['default_journal_bank'].company_id.account_journal_payment_credit_account_id.id,
        }])

        suggested_amls = self._get_st_widget_suggestions(statement.line_ids, mode='misc')
        self.assertFalse(suggested_amls)

    def test_with_reconciliation_model(self):
        bank_fees = self.env['account.reconcile.model'].create({
            'name': 'Bank Fees',
            'line_ids': [(0, 0, {
                'account_id': self.company_data['default_account_expense'].id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'amount_type': 'fixed',
                'amount_string': '50',
            })],
        })

        customer = self.partner_a

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': customer.id,
            'invoice_date': '2021-05-12',
            'date': '2021-05-12',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
            })],
        })
        invoice.action_post()
        inv_receivable = invoice.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        payment = self.env['account.payment'].create({
            'partner_id': customer.id,
            'amount': 600,
        })
        payment.action_post()
        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.env['account.reconciliation.widget'].process_move_lines([{
            'id': None,
            'type': None,
            'mv_line_ids': (inv_receivable + payment_receivable).ids,
            'new_mv_line_dicts': [{
                'name': 'SuperLabel',
                'balance': -bank_fees.line_ids.amount,
                'analytic_tag_ids': [[6, None, []]],
                'account_id': bank_fees.line_ids.account_id.id,
                'journal_id': bank_fees.line_ids.journal_id.id,
                'reconcile_model_id': bank_fees.id}
            ]
        }])

        self.assertEqual(invoice.amount_residual, 350)

    def test_manual_writeoff_with_tax_opw2689002(self):
        """ When the Reconciliation Model had a tax on the writeoff,
            the journal_id wasn't populated by widget.get_reconciliation_dict_from_model()
        """
        today = fields.Date.today().strftime('%Y-%m-%d')
        model = self.env["account.reconcile.model"].create({
            'active': True,
            'name': 'My Writeoff',
            'sequence': 5,
            'company_id': self.company.id,
            'rule_type': 'writeoff_button',
            'match_journal_ids': [(6, 0, self.bank_journal_euro.ids)],
            'line_ids': [(0, 0, {
                'label': 'My Writeoff line',
                'journal_id': self.general_journal.id,
                'account_id': self.expense_account.id,
                'amount_type': 'percentage',
                'amount_string': '100',
                'tax_ids': [(6, 0, self.tax_purchase_a.ids)],
                'force_tax_included': True,
            })],
        })
        bank_statement = self.env['account.bank.statement'].create({
            'journal_id': self.bank_journal_euro.id,
            'date': today,
            'name': 'Bank Statement TEST',
            'reference': 'Useless ref',
            'line_ids': [(0, 0, {
                'amount': -200,
                'payment_ref': 'payment_ref',
                'partner_id': self.partner_agrolait.id
            })],
        })
        bank_statement.button_post()

        widget = self.env['account.reconciliation.widget']
        widget.process_bank_statement_line(bank_statement.line_ids.ids, [{
            "lines_vals_list": [{
                "account_id": self.account_rsa.id,
                "balance": 200,
                "name": "payment_ref"
            }],
            "partner_id": self.partner_agrolait.id,
            "to_check": False
        }])
        bank_statement.button_validate_or_action()
        bank_statement_move_line = bank_statement.move_line_ids.search([("debit", "=", 200.0)])

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_agrolait.id,
            'date': today,
            'invoice_date': today,
            'currency_id': self.company.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': self.product_b.name,
                'product_id': self.product_b.id,
                'quantity': 20,
                'tax_ids': [(6, 0, [self.tax_purchase_a.id])],
                'price_unit': 10.0,
            })],
        })
        invoice.action_post()
        invoice_line = invoice.line_ids[-1]
        self.assertEqual(invoice.payment_state, 'not_paid')

        values = [{
            "id": None,
            "type": None,
            "mv_line_ids": [bank_statement_move_line.id, invoice_line.id],
            "new_mv_line_dicts": [{
                'account_id': line['account_id']['id'],
                'analytic_tag_ids': [(6, 0, line['analytic_tag_ids'] or [])],
                'balance': line['balance'],
                'journal_id': line['journal_id']['id'] if 'journal_id' in line else False,
                'name': line['name'],
                'reconcile_model_id': line['reconcile_model_id'],
                'tax_ids': [(6, 0, [x['id'] for x in line['tax_ids']]) if 'tax_ids' in line else None],
                'tax_repartition_line_id': line.get('tax_repartition_line_id', None),
            } for line in widget.get_reconciliation_dict_from_model(
                model.id, None, residual_balance=42, widget_partner_id=self.partner_agrolait.id)]
        }]
        widget.process_move_lines(values)
        self.assertEqual(invoice.payment_state, 'paid')
