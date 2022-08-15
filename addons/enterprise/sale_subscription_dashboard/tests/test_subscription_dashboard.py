# -*- coding: utf-8 -*-
import datetime
import json

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSubscriptionDashboard(HttpCase):
    def setUp(self):
        super().setUp()
        TestSubscriptionDashboard._create_test_objects(self)
        mail_new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", password="P@ssw0rd!")

    @staticmethod
    def _create_test_objects(container):
        # disable most emails for speed
        context_no_mail = {"no_reset_password": True, "mail_create_nosubscribe": True, "mail_create_nolog": True}
        Subscription = container.env["sale.subscription"].with_context(context_no_mail)
        SubTemplate = container.env["sale.subscription.template"].with_context(context_no_mail)
        ProductTmpl = container.env["product.template"].with_context(context_no_mail)

        # Test Subscription Template
        container.subscription_tmpl = SubTemplate.create(
            {
                "name": "TestSubscriptionTemplate",
                "description": "Test Subscription Template 1",
            }
        )
        # Test product
        container.product_tmpl = ProductTmpl.create(
            {
                "name": "TestProduct",
                "type": "service",
                "recurring_invoice": True,
                "subscription_template_id": container.subscription_tmpl.id,
                "uom_id": container.env.ref("uom.product_uom_unit").id,
            }
        )
        container.product = container.product_tmpl.product_variant_id
        container.product.write(
            {
                "price": 50.0,
            }
        )

        # Test Subscription
        container.partner_id = container.env["res.partner"].create(
            {
                "name": "Beatrice Portal",
            }
        )
        container.subscription = Subscription.create(
            {
                "name": "TestSubscription",
                "partner_id": container.partner_id.id,
                "pricelist_id": container.env.ref("product.list0").id,
                "template_id": container.subscription_tmpl.id,
            }
        )

    def test_nrr(self):
        self.authenticate("test_user_1", "P@ssw0rd!")
        url = "/sale_subscription_dashboard/compute_graph_and_stats"
        res = self.url_open(
            url,
            data=json.dumps(
                {
                    "params": {
                        "stat_type": "nrr",
                        "start_date": fields.Date.to_string(fields.Date.start_of(datetime.date.today(), "month")),
                        "end_date": fields.Date.to_string(fields.Date.end_of(datetime.date.today(), "month")),
                        "filters": {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(res.status_code, 200, "Should OK")
        res_data = res.json()["result"]
        nrr_before = res_data["stats"]["value_2"]

        self.subscription.write(
            {
                "partner_id": self.partner_id.id,
                "recurring_next_date": fields.Date.to_string(datetime.date.today()),
                "template_id": self.subscription_tmpl.id,
                "recurring_invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "TestRecurringLine",
                            "price_unit": 50,
                            "uom_id": self.product.uom_id.id,
                        },
                    )
                ],
                "stage_id": self.ref("sale_subscription.sale_subscription_stage_in_progress"),
            }
        )
        invoice_id = self.subscription.with_context(auto_commit=False)._recurring_create_invoice(automatic=True)
        invoice_id._post()

        res = self.url_open(
            url,
            data=json.dumps(
                {
                    "params": {
                        "stat_type": "nrr",
                        "start_date": fields.Date.to_string(fields.Date.start_of(datetime.date.today(), "month")),
                        "end_date": fields.Date.to_string(fields.Date.end_of(datetime.date.today(), "month")),
                        "filters": {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(res.status_code, 200, "Should OK")
        res_data = res.json()["result"]
        self.assertEqual(res_data["stats"]["value_2"], nrr_before, "NRR should not change after adding a subscription")
