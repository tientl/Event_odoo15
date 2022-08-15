from odoo.tests.common import tagged
from odoo.addons.account_avatax.tests.common import TestAccountAvataxCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon

from .mocked_subscription_response import generate_response


class TestSaleSubscriptionAvalaraCommon(TestAccountAvataxCommon, TestSubscriptionCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)

        partner = cls.user_portal.partner_id
        partner.property_account_position_id = cls.fp_avatax
        partner.country_id = cls.env.ref('base.us')
        partner.zip = '94134'
        partner.state_id = cls.env.ref('base.state_us_5')  # California

        cls.product.avatax_category_id = cls.env.ref('account_avatax.DC010000')
        cls.product2.avatax_category_id = cls.env.ref('account_avatax.PA3000100')

        cls.subscription.write(
            {'recurring_invoice_line_ids':
                [(0, 0, {
                    'name': 'TestRecurringLine1',
                    'product_id': cls.product.id,
                    'quantity': 1,
                    'price_unit': 120,
                    'uom_id': cls.product.uom_id.id}
                ), (0, 0, {
                    'name': 'TestRecurringLine2',
                    'product_id': cls.product2.id,
                    'quantity': 2,
                    'price_unit': 30,
                    'uom_id': cls.product2.uom_id.id}
                )]
            }
        )

        cls.acquirer = cls.env['payment.acquirer'].create({
            'name': 'The Wire',
            'provider': 'transfer',
            'state': 'test',
        })

        return res


@tagged("-at_install", "post_install")
class TestSaleSubscriptionAvalara(TestSaleSubscriptionAvalaraCommon):
    def assertOrder(self, subscription, mocked_response=None):
        if mocked_response:
            self.assertRecordValues(subscription, [{
                'recurring_total': 180.0,
                'recurring_tax': 15.53,
                'recurring_total_incl': 195.53,
            }])
        else:
            self.assertGreater(subscription.recurring_tax, 0, "Subscription didn't have any tax set.")

    def test_01_subscription_avatax_create_invoice(self):
        with self._capture_request({'lines': [], 'summary': []}) as capture:
            invoices = self.subscription.with_context(auto_commit=False)._recurring_create_invoice(automatic=True)

        self.assertEqual(
            capture.val and capture.val['json']['referenceCode'],
            invoices[0].name,
            'Should have queried avatax for the right taxes on the new invoice.'
        )

    def test_02_subscription_avatax_button_update_avatax(self):
        mocked_response = generate_response(self.subscription.recurring_invoice_line_ids)
        with self._capture_request(return_value=mocked_response) as capture:
            self.subscription.button_update_avatax()

        self.assertOrder(self.subscription, mocked_response)
        self.assertEqual(
            capture.val and capture.val['json']['referenceCode'],
            self.subscription.name,
            'Should have queried avatax for the right taxes on the subscription.'
        )

    def test_03_subscription_do_payment(self):
        invoice_values = self.subscription._prepare_invoice()
        new_invoice = self.env["account.move"].create(invoice_values)

        payment_method = self.env['payment.token'].create({
            'name': 'Jimmy McNulty',
            'partner_id': self.subscription.partner_id.id,
            'acquirer_id': self.acquirer.id,
            'acquirer_ref': 'Omar Little'
        })

        with self._capture_request({'lines': [], 'summary': []}) as capture:
            self.subscription._do_payment(payment_method, new_invoice)

        self.assertEqual(
            capture.val and capture.val['json']['referenceCode'],
            new_invoice.name,
            'Should have queried avatax before initiating the payment transactiond.'
        )

    def test_01_subscription_integration(self):
        with self._skip_no_credentials():
            # clear the taxes before doing the integration test, it can only check if the tax amount > 0.
            self.subscription.recurring_invoice_line_ids.product_id.taxes_id = False
            self.subscription._amount_all()
            self.subscription.button_update_avatax()
            self.assertOrder(self.subscription)
