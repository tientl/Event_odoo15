# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.exceptions import AccessError
from odoo.tests import Form
from odoo.tools import mute_logger
from odoo import fields
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestSubscription(TestSubscriptionCommon):

    def test_subscription_invoice_shipping_address(self):
        """Test to check that subscription invoice first try to use partner_shipping_id and partner_id from
        subscription"""
        self.company = self.env.company

        self.partner = self.env['res.partner'].create(
            {'name': 'Stevie Nicks',
             'email': 'sti@fleetwood.mac',
             'company_id': self.company.id})

        self.partner2 = self.env['res.partner'].create(
            {'name': 'Partner 2',
             'email': 'sti@fleetwood.mac',
             'company_id': self.company.id})


        invoice_id = self.subscription._recurring_create_invoice()
        addr = self.subscription.partner_id.address_get(['delivery', 'invoice'])
        self.assertEqual(invoice_id.partner_shipping_id.id, addr['invoice'])
        self.assertEqual(invoice_id.partner_id.id, addr['delivery'])

        self.subscription.write({
            'partner_id': self.partner.id,
            'partner_shipping_id': self.partner2.id,
        })

        invoice_id = self.subscription._recurring_create_invoice()
        self.assertEqual(invoice_id.partner_shipping_id.id, self.partner2.id)
        self.assertEqual(invoice_id.partner_id.id, self.partner.id)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_01_template(self):
        """ Test behaviour of on_change_template """
        Subscription = self.env['sale.subscription']

        # on_change_template on existing record (present in the db)
        self.subscription.template_id = self.subscription_tmpl
        self.subscription.on_change_template()
        self.assertTrue(self.subscription.description, 'sale_subscription: description not copied on existing sale.subscription record')

        # on_change_template on cached record (NOT present in the db)
        temp = Subscription.new({'name': 'CachedSubscription',
                                 'partner_id': self.user_portal.partner_id.id})
        temp.update({'template_id': self.subscription_tmpl.id})
        temp.on_change_template()
        self.assertTrue(temp.description, 'sale_subscription: description not copied on new cached sale.subscription record')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_02_sale_order(self):
        """ Test sales order line copying for recurring products on confirm"""
        self.sale_order.action_confirm()
        self.assertTrue(len(self.subscription.recurring_invoice_line_ids.ids) == 1, 'sale_subscription: recurring_invoice_line_ids not created when confirming sale_order with recurring_product')
        self.assertEqual(self.sale_order.subscription_management, 'upsell', 'sale_subscription: so should be set to "upsell" if not specified otherwise')

    def test_03_auto_close(self):
        """Ensure a 15 days old 'online payment' subscription gets closed if no token is set."""
        self.subscription_tmpl.payment_mode = 'success_payment'
        self.subscription.write({
            'recurring_next_date': fields.Date.to_string(datetime.date.today() - relativedelta(days=17)),
            'recurring_total': 42,
            'template_id': self.subscription_tmpl.id,
        })
        self.subscription.with_context(auto_commit=False)._recurring_create_invoice(automatic=True)
        self.assertEqual(self.subscription.stage_category, 'closed', 'website_contrect: subscription with online payment and no payment method set should get closed after 15 days')

    def test_05_sub_creation(self):
        """ Test multiple subscription creation from single SO"""
        # Test subscription creation on SO confirm
        self.sale_order_2.action_confirm()
        self.assertEqual(len(self.sale_order_2.order_line.mapped('subscription_id')), 1, 'sale_subscription: subscription should be created on SO confirmation')
        self.assertEqual(self.sale_order_2.subscription_management, 'create', 'sale_subscription: subscription creation should set the SO to "create"')

        # Two product with different subscription template
        self.sale_order_3.action_confirm()
        self.assertEqual(len(self.sale_order_3.order_line.mapped('subscription_id')), 2, 'sale_subscription: Two different subscription should be created on SO confirmation')
        self.assertEqual(self.sale_order_3.subscription_management, 'create', 'sale_subscription: subscription creation should set the SO to "create"')

        # Two product with same subscription template
        self.sale_order_4.action_confirm()
        self.assertEqual(len(self.sale_order_4.order_line.mapped('subscription_id')), 1, 'sale_subscription: One subscription should be created on SO confirmation')
        self.assertEqual(self.sale_order_4.subscription_management, 'create', 'sale_subscription: subscription creation should set the SO to "create"')

        today = fields.Date.context_today(self.env.user)
        self.sale_order_5.action_confirm()
        self.assertEqual(self.sale_order_5.order_line.subscription_id.date, today + relativedelta(months=+1), 'sale_subscription: subscription creation should set the end date to : today + 1 month')

    @mute_logger('odoo.models.unlink')
    def test_06_renewal(self):
        """ Test subscription renewal """
        res = self.subscription.prepare_renewal_order()
        renewal_so_id = res['res_id']
        renewal_so = self.env['sale.order'].browse(renewal_so_id)
        so_line_vals = {
            'name': self.product.name,
            'order_id': renewal_so_id,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'price_unit': self.product.list_price}
        new_line = self.env['sale.order.line'].create(so_line_vals)
        self.assertEqual(new_line.subscription_id, self.subscription, 'sale_subscription: SO lines added to renewal orders manually should have the correct subscription set on them')
        self.assertEqual(renewal_so.origin, self.subscription.code, 'sale_subscription: renewal order must have the "source document" set to the subscription code')
        self.assertEqual(renewal_so.subscription_management, 'renew', 'sale_subscription: renewal quotation generation is wrong')
        self.subscription.write({'recurring_invoice_line_ids': [(0, 0, {'name': 'TestRecurringLine', 'product_id': self.product.id, 'quantity': 1, 'price_unit': 50, 'uom_id': self.product.uom_id.id})]})
        renewal_so.write({'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 5, 'subscription_id': self.subscription.id, 'product_uom': self.product.uom_id.id})]})
        renewal_so.action_confirm()
        total_quantity = sum([line.quantity for line in self.subscription.mapped('recurring_invoice_line_ids')])
        self.assertEqual(total_quantity, 7, 'sale_subscription: Renewal quantity is not equal to the SO quantity')
        self.assertEqual(renewal_so.subscription_management, 'renew', 'sale_subscription: so should be set to "renew" in the renewal process')

    def test_07_upsell_via_so(self):
        """Test the upsell flow using an intermediary upsell quote."""
        wiz = self.env['sale.subscription.wizard'].create({
            'subscription_id': self.subscription.id,
            'option_lines': [(0, False, {'product_id': self.product.id, 'name': self.product.name, 'uom_id': self.product.uom_id.id})]
        })
        upsell_so_id = wiz.create_sale_order()['res_id']
        upsell_so = self.env['sale.order'].browse(upsell_so_id)
        # add line to quote manually, it must be taken into account in the subscription after validation
        so_line_vals = {
            'name': self.product2.name,
            'order_id': upsell_so_id,
            'product_id': self.product2.id,
            'product_uom_qty': 2,
            'product_uom': self.product2.uom_id.id,
            'price_unit': self.product2.list_price}
        new_line = self.env['sale.order.line'].create(so_line_vals)
        self.assertEqual(self.subscription, new_line.subscription_id,
                         '''sale_subscription: upsell line added to quote after '''
                         '''creation but before validation must be automatically '''
                         '''linked to correct subscription''')
        upsell_so.action_confirm()
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 2)

    def test_08_recurring_revenue(self):
        """Test computation of recurring revenue"""
        # Initial subscription is $100/y
        self.subscription_tmpl.recurring_rule_type = 'yearly'
        y_price = 100
        self.sale_order.action_confirm()
        subscription = self.sale_order.order_line.mapped('subscription_id')
        self.assertAlmostEqual(subscription.recurring_total, y_price, msg="unexpected price after setup")
        self.assertAlmostEqual(subscription.recurring_monthly, y_price / 12.0, msg="unexpected MRR")
        # Change interval to 3 weeks
        subscription.template_id.recurring_rule_type = 'weekly'
        subscription.template_id.recurring_interval = 3
        self.assertAlmostEqual(subscription.recurring_total, y_price, msg='total should not change when interval changes')
        self.assertAlmostEqual(subscription.recurring_monthly, y_price * (30 / 7.0) / 3, msg='unexpected MRR')

    def test_09_analytic_account(self):
        """Analytic accounting flow."""
        # analytic account is copied on order confirmation
        self.sale_order_3.analytic_account_id = self.account_1
        self.sale_order_3.action_confirm()
        subscriptions = self.sale_order_3.order_line.mapped('subscription_id')
        for subscription in subscriptions:
            self.assertEqual(self.sale_order_3.analytic_account_id, subscription.analytic_account_id)
            inv = subscription._recurring_create_invoice()
            # invoice lines have the correct analytic account
            self.assertEqual(inv.invoice_line_ids[0].analytic_account_id, subscription.analytic_account_id)
            subscription.analytic_account_id = self.account_2
            # even if changed after the fact
            inv = subscription._recurring_create_invoice()
            self.assertEqual(inv.invoice_line_ids[0].analytic_account_id, subscription.analytic_account_id)

    def test_10_compute_kpi(self):
        self.subscription.template_id.write({
            'good_health_domain': "[('recurring_monthly', '>=', 120.0)]",
            'bad_health_domain': "[('recurring_monthly', '<=', 80.0)]",
        })

        self.subscription.recurring_monthly = 80.0
        self.subscription.start_subscription()
        self.env['sale.subscription']._cron_update_kpi()
        self.assertEqual(self.subscription.health, 'bad')

        # 16 to 6 weeks: 80
        # 6 to 2 weeks: 100
        # 2weeks - today : 120
        date_log = datetime.date.today() - relativedelta(weeks=16)
        self.env['sale.subscription.log'].sudo().create({
            'event_type': '1_change',
            'event_date': date_log,
            'create_date': date_log,
            'subscription_id': self.subscription.id,
            'recurring_monthly': 80,
            'amount_signed': 80,
            'currency_id': self.subscription.currency_id.id,
            'category': self.subscription.stage_category,
            'user_id': self.subscription.user_id.id,
            'team_id': self.subscription.team_id.id,
        })

        date_log = datetime.date.today() - relativedelta(weeks=6)
        self.env['sale.subscription.log'].sudo().create({
            'event_type': '1_change',
            'event_date': date_log,
            'create_date': date_log,
            'subscription_id': self.subscription.id,
            'recurring_monthly': 100,
            'amount_signed': 20,
            'currency_id': self.subscription.currency_id.id,
            'category': self.subscription.stage_category,
            'user_id': self.subscription.user_id.id,
            'team_id': self.subscription.team_id.id,
         })

        self.subscription.recurring_monthly = 120.0
        date_log = datetime.date.today() - relativedelta(weeks=2)
        self.env['sale.subscription.log'].sudo().create({
            'event_type': '1_change',
            'event_date': date_log,
            'create_date': date_log,
            'subscription_id': self.subscription.id,
            'recurring_monthly': 120,
            'amount_signed': 20,
            'currency_id': self.subscription.currency_id.id,
            'category': self.subscription.stage_category,
            'user_id': self.subscription.user_id.id,
            'team_id': self.subscription.team_id.id,
        })
        self.subscription._cron_update_kpi()
        self.assertEqual(self.subscription.kpi_1month_mrr_delta, 20.0)
        self.assertEqual(self.subscription.kpi_1month_mrr_percentage, 0.2)
        self.assertEqual(self.subscription.kpi_3months_mrr_delta, 40.0)
        self.assertEqual(self.subscription.kpi_3months_mrr_percentage, 0.5)
        self.assertEqual(self.subscription.health, 'done')

    def test_11_onchange_date_start(self):
        recurring_bound_tmpl = self.env['sale.subscription.template'].create({
            'name': 'Recurring Bound Template',
            'recurring_rule_boundary': 'limited',
        })
        sub_form = Form(self.env['sale.subscription'])
        sub_form.partner_id = self.user_portal.partner_id
        sub_form.template_id = recurring_bound_tmpl
        sub = sub_form.save()
        self.assertEqual(sub.template_id.recurring_rule_boundary, 'limited')
        self.assertIsInstance(sub.date, datetime.date)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_12_default_salesperson(self):
        partner = self.env['res.partner'].create({'name': 'Tony Stark'})
        sub_form = Form(self.env['sale.subscription'])
        sub_form.template_id = self.subscription_tmpl
        sub_form.partner_id = partner
        sub = sub_form.save()
        self.assertEqual(sub.user_id, self.env.user)

        partner.user_id = self.user_portal
        sub_form = Form(self.env['sale.subscription'])
        sub_form.template_id = self.subscription_tmpl
        sub_form.partner_id = partner
        sub = sub_form.save()
        self.assertEqual(sub.user_id, self.user_portal)

    def test_13_next_invoice_date_last_date_of_month(self):
        """ This testcase will check the next invoice dates for monthly subscription. """
        self.subscription_tmpl.recurring_interval = 1
        # Created subscription with `date_start` set to last day of December and `recurring_next_date` as last day of January.
        sub = self.subscription.copy({'date_start': '2017-12-31', 'recurring_next_date': '2018-01-31'})
        self.assertEqual(sub.recurring_invoice_day, 31, 'Next Invoice Day should be 31.')
        # Since the monthly subscription starts on the 31st day of December, the next invoice should be generated on the same day of next month
        # except for the months which does not have the same day, in such cases, it should be generated on last day of that particular month
        sub.generate_recurring_invoice()
        self.assertEqual(sub.recurring_next_date, datetime.date(2018, 2, 28), '`Date of Next Invoice` should be the last day of February 2018.')
        sub.generate_recurring_invoice()
        self.assertEqual(sub.recurring_next_date, datetime.date(2018, 3, 31), '`Date of Next Invoice` should be the last day of March 2018.')
        sub.generate_recurring_invoice()
        self.assertEqual(sub.recurring_next_date, datetime.date(2018, 4, 30), '`Date of Next Invoice` should be the last day of April 2018.')

    def test_14_changed_next_invoice_date(self):
        """This testcase will check next invoice dates if user change next invoice date manually"""
        self.subscription_tmpl.recurring_interval = 1
        # Created subscription with `date_start` and `recurring_next_date` to 5th of February and March respectively.
        sub = self.subscription.copy({'date_start': '2018-02-05', 'recurring_next_date': '2018-03-05'})
        # Since the monthly subscription's `recurring_next_date` is set to 5th March(ie. it is not the last day of month), `recurring_next_date` should be set to the same day of next month
        sub.generate_recurring_invoice()
        self.assertEqual(sub.recurring_next_date, datetime.date(2018, 4, 5), '`Date of Next Invoice` should be 5th April 2018.')
        # Manually changing `recurring_next_date` to the last day of April 2018.
        sub.recurring_next_date = '2018-04-30'
        # `recurring_invoice_day` should be set to 30 as `recurring_next_date` was modified manually(and not by cron)
        self.assertEqual(sub.recurring_invoice_day, 30, 'Next Invoice Day should be 30.')
        # We have changed next invoice date to 30th of April, the next invoice should be generated on 30th of next month
        sub.generate_recurring_invoice()
        self.assertEqual(sub.recurring_next_date, datetime.date(2018, 5, 30), '`Date of Next Invoice` should be 30th May 2018.')
        sub.generate_recurring_invoice()
        self.assertEqual(sub.recurring_next_date, datetime.date(2018, 6, 30), '`Date of Next Invoice` should be 30th June 2018.')

    def test_16_product_change(self):
        """Check behaviour of the product onchange (taxes mostly)."""
        # check default tax
        sub_form = Form(self.subscription)
        with sub_form.recurring_invoice_line_ids.new() as line:
            line.product_id = self.product
        sub = sub_form.save()
        self.assertEqual(sub.recurring_invoice_line_ids.product_id.taxes_id, self.tax_10, 'Default tax for product should have been applied.')
        self.assertEqual(sub.recurring_tax, 5.0,
                         'Default tax for product should have been applied.')
        self.assertEqual(sub.recurring_total_incl, 55.0,
                         'Default tax for product should have been applied.')
        # Change the product
        line_id = sub.recurring_invoice_line_ids.ids
        sub.write({
            'recurring_invoice_line_ids': [(1, line_id[0], {'product_id': self.product4.id})]
        })
        # As we update only the product id, the price on the line remains the same.
        self.assertEqual(sub.recurring_invoice_line_ids.product_id.taxes_id, self.tax_20,
                         'Default tax for product should have been applied.')
        self.assertEqual(sub.recurring_tax, 10.0,
                         'Default tax for product should have been applied.')
        self.assertEqual(sub.recurring_total_incl, 60.0,
                         'Default tax for product should have been applied.')

    def test_17_renew_archived_products(self):
        """Check behaviour of renewal of archived products."""
        sub = self.subscription.copy({'date_start': '2020-04-01', 'recurring_next_date': '2020-05-1'})
        sub.write({'recurring_invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine',
                                                          'price_unit': 50, 'uom_id': self.product.uom_id.id,
                                                          'quantity': 5}),
                                                  (0, 0, {
                                                      'name': 'TestRecurringLine 2',
                                                      'product_id': self.product2.id,
                                                      'price_unit': 150, 'quantity': 42,
                                                      'uom_id': self.product2.uom_id.id}),
                                                  ]})
        # archive one of the product
        self.product2.write({'active': False})
        archived_product_ids = sub.with_context(active_test=False).archived_product_ids.ids
        archived_product_count = sub.archived_product_count
        self.assertEqual(archived_product_ids, [self.product2.id], 'sale_subscription: Product 2 should be archived and recognized as such')
        self.assertTrue(archived_product_count == 1, 'sale_subscription: One product should be marked as archived')
        wiz = self.env['sale.subscription.renew.wizard'].create({
            'subscription_id': sub.id,
            'kept_archived_product_ids': [(0, False, {'renew_product': False, 'name': self.product2.name,
                                                      'product_id': self.product2.id, 'quantity': 42})],
            'replacement_line_ids': [(0, False, {'product_id': self.product.id, 'name': self.product.name,
                                                 'quantity': 2, 'uom_id': self.product.uom_id.id}),
                                     (0, False, {'product_id': self.product3.id, 'name': self.product3.name,
                                                 'quantity': 10, 'uom_id': self.product3.uom_id.id})
                                     ]
        })
        renewal_so_id = wiz.create_renewal_order()['res_id']
        renewal_so = self.env['sale.order'].browse(renewal_so_id)
        lines_renew = [(line.name, line.product_id.id, line.product_uom_qty) for line in renewal_so.mapped('order_line')]
        self.assertEqual(renewal_so.subscription_management, 'renew',
                         'sale_subscription: so should be set to "renew" in the renewal process')
        self.assertEqual(lines_renew[0][1], self.product.id, 'sale_subscription: First product should be TestProduct')
        self.assertEqual(lines_renew[0][2], 7,
                         'sale_subscription: Renewal quantity of replacement product already present should be equal to 10.')
        self.assertEqual(lines_renew[1][1], self.product3.id, 'sale_subscription: First product should be TestProduct')
        self.assertEqual(lines_renew[1][2], 10,
                         'sale_subscription: Renewal quantity of new replacement product should be equal to 3.')

    def test_18_log_change_template(self):
        """ Test subscription log generation when template_id is changed """
        # Create a subscription and add a line, should have logs with MMR 120
        subscription = self.env['sale.subscription'].create({
            'name': 'TestSubscription',
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'template_id': self.subscription_tmpl.id,
        })
        self.cr.precommit.clear()
        subscription.write({'recurring_invoice_line_ids': [(0, 0, {
            'name': 'TestRecurringLine',
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 120,
            'uom_id': self.product.uom_id.id})]})
        subscription.start_subscription()
        self.flush_tracking()
        init_nb_log = len(subscription.subscription_log_ids)
        # Configure a template to be yearly, assign that template
        self.subscription_tmpl_3.recurring_rule_type = 'yearly'
        self.subscription_tmpl_3.recurring_interval = 1
        subscription.write({'template_id': self.subscription_tmpl_3})
        self.flush_tracking()
        # Should get one more log with MRR 10 (so change is -110)
        self.assertEqual(len(subscription.subscription_log_ids), init_nb_log + 1,
                         "Subscription log not generated after change of the subscription template")
        self.assertRecordValues(subscription.subscription_log_ids[-1],
                                [{'recurring_monthly': 10.0, 'amount_signed': -110}])

    def test_19_fiscal_position(self):
        # Test that the fiscal postion FP is applied on recurring invoice.
        # FP must mapped an included tax of 21% to an excluded one of 0%
        tax_include_id = self.env['account.tax'].create({'name': "Include tax",
                                                    'amount': 21.0,
                                                    'price_include': True,
                                                    'type_tax_use': 'sale'})
        tax_exclude_id = self.env['account.tax'].create({'name': "Exclude tax",
                                                    'amount': 0.0,
                                                    'type_tax_use': 'sale'})

        self.product_tmpl.write({'taxes_id': [(6, 0, [tax_include_id.id])], 'list_price': 121})

        fp = self.env['account.fiscal.position'].create({'name': "fiscal position",
                                                    'sequence': 1,
                                                    'auto_apply': True,
                                                    'tax_ids': [(0, 0, {'tax_src_id': tax_include_id.id, 'tax_dest_id': tax_exclude_id.id})]})

        self.env['sale.subscription.line'].create({'analytic_account_id': self.subscription.id,
                                                'product_id': self.product_tmpl.product_variant_id.id,
                                                'price_unit': 121,
                                                'uom_id': self.env.ref('uom.product_uom_unit').id,
                                                'quantity': 1})
        self.subscription.partner_id.property_account_position_id = fp
        inv = self.subscription._recurring_create_invoice()
        self.assertEqual(100, inv.invoice_line_ids[0].price_unit, "The included tax must be subtracted to the price")

    def test_prevents_assigning_not_owned_payment_tokens_to_subscriptions(self):
        malicious_user_subscription = self.env['sale.subscription'].create({
            'name': 'Free Subscription',
            'partner_id': self.malicious_user.partner_id.id,
            'template_id': self.subscription_tmpl.id,
        })
        self.partner = self.env['res.partner'].create(
            {'name': 'Stevie Nicks',
             'email': 'sti@fleetwood.mac',
             'property_account_receivable_id': self.account_receivable.id,
             'property_account_payable_id': self.account_receivable.id,
             'company_id': self.env.company.id})
        self.acquirer = self.env['payment.acquirer'].create(
            {'name': 'The Wire',
             'provider': 'transfer',
             'company_id': self.env.company.id,
             'state': 'test'})
        stolen_payment_method = self.env['payment.token'].create(
            {'name': 'Jimmy McNulty',
             'partner_id': self.partner.id,
             'acquirer_id': self.acquirer.id,
             'acquirer_ref': 'Omar Little'})

        with self.assertRaises(AccessError):
            malicious_user_subscription.with_user(self.malicious_user).write({
                'payment_token_id': stolen_payment_method.id,  # payment token not related to al capone
            })

    def test_pricelist_discount(self):

        discount_pricelist = self.env['product.pricelist'].create({
            'name': 'Discount Pricelist',
            'discount_policy': 'without_discount',
            'currency_id': self.product.currency_id.id,
        })

        # Discount Pricelist item
        self.env['product.pricelist.item'].create({
            'percent_price': 20,
            'compute_price': 'percentage',
            'pricelist_id': discount_pricelist.id
        })

        subscription = self.env['sale.subscription'].create({
            'name': 'TestSubscriptionDiscount',
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': discount_pricelist.id,
            'template_id': self.subscription_tmpl.id,
            'company_id': self.company_data['company'].id
        })
        self.cr.precommit.clear()
        subscription.write({'recurring_invoice_line_ids': [(0, 0, {
            'name': 'TestRecurringLine',
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 50,
            'uom_id': self.product.uom_id.id})]
        })
        line = subscription.recurring_invoice_line_ids

        # Manually trigger onchange
        line.onchange_product_quantity()

        self.assertEqual(line.price_unit, 50, 'Price unit should not have change')
        self.assertEqual(line.discount, 20, 'Discount should be applied on the line')
        self.assertEqual(line.price_subtotal, 40, 'Price unit should be QTY * PRICE_UNIT * (1-DISCOUNT/100) = 1 * 50 * (1-0.20) = 40')

    def test_onchange_product_quantity_with_different_currencies(self):
        # onchange_product_quantity compute price unit into the currency of the subscription pricelist
        # when currency of the product (Gold Coin) is different than subscription pricelist (USD)
        self.subscription.write({'recurring_invoice_line_ids': [(0, 0, {
            'name': 'TestRecurringLine',
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 50,
            'uom_id': self.product.uom_id.id,
        })]})
        line = self.subscription.recurring_invoice_line_ids
        self.assertEqual(line.price_unit, 50, 'Price unit should not have changed')
        self.product.currency_id = self.currency_data['currency']
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            self.product.currency_id,
            self.subscription.pricelist_id.currency_id,
            self.product.company_id or self.env.company,
            fields.Date.today())
        self.subscription.recurring_invoice_line_ids.onchange_product_quantity()
        self.assertEqual(line.price_unit, self.subscription.pricelist_id.currency_id.round(50 * conversion_rate),
            'Price unit must be converted into the currency of the pricelist (USD)')

    def test_archive_partner_invoice_shipping_onchange_so(self):
        # archived a partner must not remain set on invoicing/shipping address in subscription
        # here, they are set via their parent (onchange) on SO
        self.sale_order.partner_id = self.partner_a
        self.sale_order.onchange_partner_id()
        self.assertEqual(self.partner_a_invoice, self.sale_order.partner_invoice_id,
             "Setting the customer on SO should set its invoice address via onchange.")
        self.assertEqual(self.partner_a_shipping, self.sale_order.partner_shipping_id,
             "Setting the customer on SO should set its delivery address via onchange.")

        self.sale_order.order_line.mapped('subscription_id').unlink()
        self.sale_order.action_confirm()
        subscription = self.sale_order.order_line.mapped('subscription_id')
        self.assertEqual(self.partner_a_invoice, subscription.partner_invoice_id,
             "On the subscription, invoice address should be customer's invoice address.")
        self.assertEqual(self.partner_a_shipping, subscription.partner_shipping_id,
             "On the subscription, delivery address should be customer's delivery address.")

        invoice = subscription._recurring_create_invoice()
        self.assertEqual(self.partner_a_invoice, invoice.partner_id,
             "On the invoice, invoice address should be customer's invoice address.")
        self.assertEqual(self.partner_a_shipping, invoice.partner_shipping_id,
             "On the invoice, delivery address should be customer's delivery address.")

        self.partner_a.child_ids.write({'active': False})
        self.assertFalse(subscription.partner_invoice_id,
             "As invoice address have been archived, it should not be on the subscrption anymore.")
        self.assertFalse(subscription.partner_shipping_id,
             "As delivery address have been archived, it should not be on the subscrption anymore.")

        invoice = subscription._recurring_create_invoice()
        self.assertEqual(self.partner_a, invoice.partner_id,
             "As there is no invoice address on the subscription, customer's address should be chosen as invoice address on the invoice.")
        self.assertEqual(self.partner_a, invoice.partner_shipping_id,
             "As there is no delivery address on the subscription, customer's address should be chosen as delivery address on the invoice.")

    def test_onchange_partner_id_on_subscription(self):
        # test onchange_partner_id on subscription
        self.sale_order.order_line.mapped('subscription_id').unlink()
        self.sale_order.action_confirm()

        subscription = self.sale_order.order_line.mapped('subscription_id')

        subscription.partner_id = self.partner_a
        subscription.onchange_partner_id()
        self.assertEqual(self.partner_a_invoice, subscription.partner_invoice_id,
             "Setting the customer on subscription should set its invoice address via onchange.")
        self.assertEqual(self.partner_a_shipping, subscription.partner_shipping_id,
             "Setting the customer on subscription should set its delivery address via onchange.")

    def test_archive_partner_invoice_shipping_manual_sub(self):
        # archived a partner must not remain set on invoicing/shipping address in subscription
        # here, they are set manually on subscription
        self.sale_order.order_line.mapped('subscription_id').unlink()
        self.sale_order.action_confirm()

        subscription = self.sale_order.order_line.mapped('subscription_id')
        initial_sub_partner = subscription.partner_id

        subscription.write({
            'partner_invoice_id': self.partner_a_invoice,
            'partner_shipping_id': self.partner_a_shipping,
        })
        self.assertEqual(self.partner_a_invoice, subscription.partner_invoice_id,
             "Invoice address should have been set manually on the subscription.")
        self.assertEqual(self.partner_a_shipping, subscription.partner_shipping_id,
             "Delivery address should have been set manually on the subscription.")

        invoice = subscription._recurring_create_invoice()
        self.assertEqual(self.partner_a_invoice, invoice.partner_id,
             "On the invoice, invoice address should be the same as on the subscription.")
        self.assertEqual(self.partner_a_shipping, invoice.partner_shipping_id,
             "On the invoice, delivery address should be the same as on the subscription.")

        self.partner_a.child_ids.write({'active': False})
        self.assertFalse(subscription.partner_invoice_id,
             "As invoice address have been archived, it should not be on the subscrption anymore.")
        self.assertFalse(subscription.partner_shipping_id,
             "As delivery address have been archived, it should not be on the subscrption anymore.")

        invoice = subscription._recurring_create_invoice()
        self.assertEqual(initial_sub_partner, invoice.partner_id,
             "As there is no invoice address on the subscription, initial customer's address should be chosen as invoice address on the invoice.")
        self.assertEqual(initial_sub_partner, invoice.partner_shipping_id,
             "As there is no delivery address on the subscription, initial customer's address should be chosen as delivery address on the invoice.")

    def test_portal_pay_subscription(self):
        # When portal pays a subscription, a success mail is sent.
        # This calls AccountMove.amount_by_group, which triggers _compute_invoice_taxes_by_group().
        # As this method writes on this field and also reads tax_ids, which portal has no rights to,
        # it might cause some access rights issues. This test checks that no error is raised.
        portal_partner = self.user_portal.partner_id
        portal_partner.country_id = self.env['res.country'].search([('code', '=', 'US')])
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
        })
        acquirer = self.env['payment.acquirer'].create({
            'name': 'Test',
        })
        tx = self.env['payment.transaction'].create({
            'amount': 100,
            'acquirer_id': acquirer.id,
            'currency_id': self.env.company.currency_id.id,
            'partner_id': portal_partner.id,
        })
        self.subscription.with_user(self.user_portal).sudo().send_success_mail(tx, invoice)
