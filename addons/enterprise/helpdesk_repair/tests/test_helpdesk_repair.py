# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form, tagged


@tagged('post_install', '-at_install')
class TestRepair(AccountTestInvoicingCommon):
    def test_lot_id(self):
        """ This test purpose is to ensure that, if present, the context key default_lot_id is not
        propagated to the action_repair_done(). """

        company = self.env.company
        product = self.env['product.product'].create({'name': 'Product'})
        product_lot = self.env['stock.production.lot'].create({
            'product_id': product.id,
            'company_id': company.id})
        component = self.env['product.product'].create({'name': 'Component'})

        ro_form = Form(self.env['repair.order'].with_context(default_lot_id=product_lot.id))
        ro_form.product_id = product
        ro_form.partner_id = company.partner_id
        with ro_form.operations.new() as ro_line:
            ro_line.product_id = component

        repair_order = ro_form.save()
        repair_order.action_repair_confirm()
        repair_order.action_repair_start()
        repair_order.action_repair_end()
