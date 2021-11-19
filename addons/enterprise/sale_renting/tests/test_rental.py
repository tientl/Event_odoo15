# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import fields

class TestRentalCommon(odoo.tests.common.SingleTransactionCase):

    def setUp(self):
        super(TestRentalCommon, self).setUp()

        self.product_id = self.env['product.product'].create({
            'name': 'Projector',
            'categ_id': self.env.ref('product.product_category_all').id,
            'type': 'consu',
            'rent_ok': True,
            'extra_hourly': 7.0,
            'extra_daily': 30.0,
        })

        self.product_template_id = self.product_id.product_tmpl_id

        self.product_template_id.rental_pricing_ids.unlink()
        # blank the demo pricings

        PRICINGS = [
            {
                'duration': 1.0,
                'unit': 'hour',
                'price': 3.5,
            }, {
                'duration': 5.0,
                'unit': 'hour',
                'price': 15.0,
            }, {
                'duration': 15.0,
                'unit': 'hour',
                'price': 40.0,
            }, {
                'duration': 1.0,
                'unit': 'day',
                'price': 60.0,
            },
        ]

        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['rental.pricing'].create(pricing)

    def test_availability(self):
        # Pickup, return some, check different periods
        return

    def test_pricing(self):
        # check pricing returned = expected
        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=9.0, unit='hour')._compute_price(9.0, 'hour'),
            30.0
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=11.0, unit='hour')._compute_price(11.0, 'hour'),
            38.5
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=16.0, unit='hour')._compute_price(16.0, 'hour'),
            56.0
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=20, unit='hour')._compute_price(20.0, 'hour'),
            60.0
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=24.0, unit='hour')._compute_price(24.0, 'hour'),
            60.0
        )

    def test_pricing_advanced(self):
        # with pricings applied only to some variants ...
        return

    def test_pricelists(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        pricelist_B = self.env['product.pricelist'].create({
            'name': 'Pricelist B',
        })

        PRICINGS = [
            {
                'duration': 1.0,
                'unit': 'hour',
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }, {
                'duration': 5.0,
                'unit': 'hour',
                'price': 15.0,
                'pricelist_id': pricelist_B.id,
            }
        ]
        self.product_template_id.rental_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['rental.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })

        reservation_begin = fields.Datetime.now()
        pickup_date = reservation_begin + relativedelta(days=1)
        return_date = pickup_date + relativedelta(hours=1)

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': 1,
            'order_id': sale_order.id,
            'reservation_begin': reservation_begin,
            'pickup_date': pickup_date,
            'return_date': return_date,
            'is_rental': True,
        })

        sale_order.write({'pricelist_id': pricelist_A.id})
        sale_order.update_prices()
        self.assertEqual(sol.price_unit, 3.5, "Pricing should take into account pricelist A")
        sale_order.write({'pricelist_id': pricelist_B.id})
        sale_order.update_prices()
        self.assertEqual(sol.price_unit, 15, "Pricing should take into account pricelist B")

    def test_delay_pricing(self):
        # Return Products late and verify duration is correct.
        self.product_id.extra_hourly = 2.5
        self.product_id.extra_daily = 15.0

        self.assertEqual(
            self.product_id._compute_delay_price(timedelta(hours=5.0)),
            12.5
        )

        self.assertEqual(
            self.product_id._compute_delay_price(timedelta(hours=5.0, days=6)),
            102.5
        )

    # TODO availability testing with sale_rental functions? (no stock)

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_rental_flow(self):
        # somehow, the name_create and onchange of the partner_id
        # in a quotation trigger a re-rendering that loses
        # the focus of some fields, preventing the tour to
        # run successfully if a partner is created during the flow
        # create it in advance here instead
        self.env['res.partner'].name_create('Agrolait')
        self.start_tour("/web", 'rental_tour', login="admin")
