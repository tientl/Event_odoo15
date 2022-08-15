# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

class TestPartnerPosLoyalty(TransactionCase):

    def test_merge_loyalty_points(self):
        """ Check that when you merge two customers, the loyalty points are correctly summed,
        especially in a multi-company situation. """
        company_a = self.env.user.company_id
        company_b = self.env['res.company'].create({
            'name': 'Company A',
        })
        p1 = self.env['res.partner'].create({
            'name': 'AAAAAA'
        })
        p2 = self.env['res.partner'].create({
            'name': 'BBBBBB'
        })
        p1.with_company(company_a).loyalty_points = 1.0
        p1.with_company(company_b).loyalty_points = 9.0
        p2.with_company(company_a).loyalty_points = 10.0
        p2.with_company(company_b).loyalty_points = 90.0

        self.env['base.partner.merge.automatic.wizard']._merge((p1 + p2).ids, p1)
        self.assertEqual(p1.with_company(company_a).loyalty_points, 11.0)
        self.assertEqual(p1.with_company(company_b).loyalty_points, 99.0)

