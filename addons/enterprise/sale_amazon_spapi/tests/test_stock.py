# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.sale_amazon_spapi.tests import common
from odoo.addons.stock.tests.common import TestStockCommon


class TestStock(common.TestAmazonCommon, TestStockCommon):

    # As this test class is exclusively intended to test Amazon-related check on pickings, the
    # normal flows of stock are put aside in favor of manual updates on quantities.

    def setUp(self):
        super().setUp()

        # Create sales order
        partner = self.env['res.partner'].create({
            'name': "Gederic Frilson",
        })
        self.sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'name': 'test',
                'product_id': self.productA.id,
                'product_uom_qty': 2,
                'amazon_item_ref': '123456789',
            })],
            'amazon_order_ref': '123456789',
        })

        # Create picking
        self.picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.customer_location,
        })
        move_vals = {
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.customer_location,
            'sale_line_id': self.sale_order.order_line[0].id,
        }
        self.move_1 = self.MoveObj.create(move_vals)
        self.move_2 = self.MoveObj.create(move_vals)
        self.picking.sale_id = self.sale_order.id  # After creating the moves as it clears the field

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon_spapi.models.amazon_account')
    def test_check_carrier_details_compliance_no_carrier(self):
        """ Test the validation of a picking when the delivery carrier is not set. """
        def get_product_mock(_self, product_code_, _default_xmlid, default_name_, default_type_):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = False
            return product_

        with patch(
                'odoo.addons.sale_amazon_spapi.utils.make_proxy_request',
                return_value=common.AWS_RESPONSE_MOCK,
        ), patch(
            'odoo.addons.sale_amazon_spapi.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._get_product',
            new=get_product_mock,
        ):
            self.account.aws_credentials_expiry = '1970-01-01'  # The field is not stored.
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id = None
            picking.carrier_tracking_ref = self.tracking_ref
            picking.location_dest_id.usage = 'customer'
            with self.assertRaises(UserError):
                picking._check_carrier_details_compliance()

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon_spapi.models.amazon_account')
    def test_check_carrier_details_compliance_intermediate_delivery_step(self):
        """ Test the validation of a picking when the delivery is in an intermediate step."""
        def get_product_mock(_self, product_code_, _default_xmlid, default_name_, default_type_):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = False
            return product_

        with patch(
                'odoo.addons.sale_amazon_spapi.utils.make_proxy_request',
                return_value=common.AWS_RESPONSE_MOCK,
        ), patch(
            'odoo.addons.sale_amazon_spapi.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._get_product',
            new=get_product_mock,
        ):
            self.account.aws_credentials_expiry = '1970-01-01'  # The field is not stored.
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id = None
            picking.carrier_tracking_ref = self.tracking_ref
            intermediate_destination_id = self.env.ref('stock.location_pack_zone').id
            picking.location_dest_id = intermediate_destination_id
            picking._check_carrier_details_compliance()  # Don't raise if intermediate delivery step

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon_spapi.models.amazon_account')
    def test_check_carrier_details_compliance_no_tracking_number(self):
        """ Test the validation of a picking when the tracking reference is not set. """
        def get_product_mock(_self, product_code_, _default_xmlid, default_name_, default_type_):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = False
            return product_

        with patch(
                'odoo.addons.sale_amazon_spapi.utils.make_proxy_request',
                return_value=common.AWS_RESPONSE_MOCK,
        ), patch(
            'odoo.addons.sale_amazon_spapi.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._get_product',
            new=get_product_mock,
        ):
            self.account.aws_credentials_expiry = '1970-01-01'  # The field is not stored.
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id = self.carrier
            picking.carrier_tracking_ref = None
            with self.assertRaises(UserError):
                picking._check_carrier_details_compliance()

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon_spapi.models.amazon_account')
    def test_check_carrier_details_compliance_requirements_met_in_last_step_delivery(self):
        """ Test the validation of a picking when the delivery carrier and tracking ref are set. """
        def get_product_mock(_self, product_code_, _default_xmlid, default_name_, default_type_):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = False
            return product_

        with patch(
                'odoo.addons.sale_amazon_spapi.utils.make_proxy_request',
                return_value=common.AWS_RESPONSE_MOCK,
        ), patch(
            'odoo.addons.sale_amazon_spapi.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._get_product',
            new=get_product_mock,
        ):
            self.account.aws_credentials_expiry = '1970-01-01'  # The field is not stored.
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id, picking.carrier_tracking_ref = self.carrier, self.tracking_ref
            picking._check_carrier_details_compliance()  # Everything is fine, don't raise
