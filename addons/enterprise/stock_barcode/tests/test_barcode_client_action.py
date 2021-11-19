# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.tests import Form, HttpCase, tagged


def clean_access_rights(env):
    """ remove all access right link to stock application to the users
    given as parameter"""
    grp_lot = env.ref('stock.group_production_lot')
    grp_multi_loc = env.ref('stock.group_stock_multi_locations')
    grp_pack = env.ref('stock.group_tracking_lot')
    grp_uom = env.ref('uom.group_uom')
    env.user.write({'groups_id': [(3, grp_lot.id)]})
    env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
    env.user.write({'groups_id': [(3, grp_pack.id)]})
    # Explicitly remove the UoM group.
    group_user = env.ref('base.group_user')
    group_user.write({'implied_ids': [(3, grp_uom.id)]})
    env.user.write({'groups_id': [(3, grp_uom.id)]})


@tagged('-at_install', 'post_install')
class TestBarcodeClientAction(HttpCase):
    def setUp(self):
        super(TestBarcodeClientAction, self).setUp()
        self.uid = self.env.ref('base.user_admin').id
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_location.write({
            'barcode': 'LOC-01-00-00',
        })
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.pack_location = self.env.ref('stock.location_pack_zone')
        self.shelf1 = self.env["stock.location"].create({
            'name': 'Section 1',
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
            'barcode': 'LOC-01-01-00',
        })
        self.shelf2 = self.env['stock.location'].create({
            'name': 'Section 2',
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
            'barcode': 'LOC-01-02-00',
        })
        self.shelf3 = self.env['stock.location'].create({
            'name': 'Section 3',
            'location_id': self.stock_location.id,
            'barcode': 'shelf3',
        })
        self.shelf4 = self.env['stock.location'].create({
            'name': 'Section 4',
            'location_id': self.stock_location.id,
            'barcode': 'shelf4',
        })
        self.picking_type_in = self.env.ref('stock.picking_type_in')
        self.picking_type_internal = self.env.ref('stock.picking_type_internal')
        self.picking_type_out = self.env.ref('stock.picking_type_out')

        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.uom_dozen = self.env.ref('uom.product_uom_dozen')

        # Two stockable products without tracking
        self.product1 = self.env['product.product'].create({
            'name': 'product1',
            'default_code': 'TEST',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product1',
        })
        self.product2 = self.env['product.product'].create({
            'name': 'product2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product2',
        })
        self.productserial1 = self.env['product.product'].create({
            'name': 'productserial1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productserial1',
            'tracking': 'serial',
        })
        self.productlot1 = self.env['product.product'].create({
            'name': 'productlot1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productlot1',
            'tracking': 'lot',
        })
        self.package = self.env['stock.quant.package'].create({
            'name': 'P00001',
        })
        self.owner = self.env['res.partner'].create({
            'name': 'Azure Interior',
        })

        # Creates records specific to GS1 use cases.
        self.product_tln_gtn8 = self.env['product.product'].create({
            'name': 'Battle Droid',
            'default_code': 'B1',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '76543210',  # (01)00000076543210 (GTIN-8 format)
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        self.call_count = 0

    def tearDown(self):
        self.call_count = 0
        super(TestBarcodeClientAction, self).tearDown()

    def _get_client_action_url(self, picking_id):
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_picking_client_action")
        return '/web#action=%s&active_id=%s' % (action['id'], picking_id)


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):
    def test_internal_picking_from_scratch_1(self):
        """ Open an empty internal picking
          - move 2 `self.product1` from shelf1 to shelf2
          - move 1 `self.product2` from shelf1 to shelf3
          - move 1 `self.product2` from shelf1 to shelf2
        Test all these operations only by scanning barcodes.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(internal_picking.id)

        # Mock the calls to write and run the phantomjs script.
        product1 = self.product1
        product2 = self.product2
        shelf1 = self.shelf1
        shelf2 = self.shelf2
        shelf3 = self.shelf3
        assertEqual = self.assertEqual
        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            cmd = vals['move_line_ids'][0]
            write_vals = cmd[2]
            if self1.call_count == 1:
                assertEqual(cmd[0], 0)
                assertEqual(cmd[1], 0)
                assertEqual(write_vals['product_id'], product1.id)
                assertEqual(write_vals['picking_id'], internal_picking.id)
                assertEqual(write_vals['location_id'], shelf1.id)
                assertEqual(write_vals['location_dest_id'], shelf2.id)
                assertEqual(write_vals['qty_done'], 2)
            elif self1.call_count == 2:
                assertEqual(cmd[0], 0)
                assertEqual(cmd[1], 0)
                assertEqual(write_vals['product_id'], product2.id)
                assertEqual(write_vals['picking_id'], internal_picking.id)
                assertEqual(write_vals['location_id'], shelf1.id)
                assertEqual(write_vals['location_dest_id'], shelf3.id)
                assertEqual(write_vals['qty_done'], 1)
            elif self1.call_count == 3:
                assertEqual(cmd[0], 0)
                assertEqual(cmd[1], 0)
                assertEqual(write_vals['product_id'], product2.id)
                assertEqual(write_vals['picking_id'], internal_picking.id)
                assertEqual(write_vals['location_id'], shelf1.id)
                assertEqual(write_vals['location_dest_id'], shelf2.id)
                assertEqual(write_vals['qty_done'], 1)
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_internal_picking_from_scratch_1', login='admin', timeout=180)
            self.assertEqual(self.call_count, 3)

        self.assertEqual(len(internal_picking.move_line_ids), 3)

    def test_internal_picking_from_scratch_2(self):
        """ Open an empty internal picking
          - move 2 `self.product1` from shelf1 to shelf2
          - move 1 `self.product2` from shelf1 to shelf3
          - move 1 `self.product2` from shelf1 to shelf2
        Test all these operations only by using the embedded form views.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(internal_picking.id)

        self.start_tour(url, 'test_internal_picking_from_scratch_2', login='admin', timeout=180)

        self.assertEqual(len(internal_picking.move_line_ids), 4)
        prod1_ml = internal_picking.move_line_ids.filtered(lambda ml: ml.product_id.id == self.product1.id)
        prod2_ml = internal_picking.move_line_ids.filtered(lambda ml: ml.product_id.id == self.product2.id)
        self.assertEqual(prod1_ml[0].qty_done, 2)
        self.assertEqual(prod1_ml[0].location_id, self.shelf1)
        self.assertEqual(prod1_ml[0].location_dest_id, self.shelf2)
        self.assertEqual(prod1_ml[1].qty_done, 1)
        self.assertEqual(prod1_ml[1].location_id, self.shelf1)
        self.assertEqual(prod1_ml[1].location_dest_id, self.shelf3)
        self.assertEqual(prod2_ml[0].qty_done, 1)
        self.assertEqual(prod2_ml[0].location_id, self.shelf1)
        self.assertEqual(prod2_ml[0].location_dest_id, self.shelf2)
        self.assertEqual(prod2_ml[1].qty_done, 1)
        self.assertEqual(prod2_ml[1].location_id, self.shelf1)
        self.assertEqual(prod2_ml[1].location_dest_id, self.shelf3)

    def test_internal_picking_reserved_1(self):
        """ Open a reserved internal picking
          - move 1 `self.product1` and 1 `self.product2` from shelf1 to shelf2
          - move 1 `self.product1` from shelf3 to shelf4.
        Before doing the reservation, move 1 `self.product1` from shelf3 to shelf2
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(internal_picking.id)

        # prepare the picking
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf3, 1)
        move1 = self.env['stock.move'].create({
            'name': 'test_internal_picking_reserved_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_internal_picking_reserved_1_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking.id,
        })
        internal_picking.action_confirm()
        internal_picking.action_assign()
        move1.move_line_ids.location_dest_id = self.shelf2.id
        for ml in move2.move_line_ids:
            if ml.location_id.id == self.shelf1.id:
                ml.location_dest_id = self.shelf2.id
            else:
                ml.location_dest_id = self.shelf4.id

        # Mock the calls to write and run the phantomjs script.
        product1 = self.product1
        shelf2 = self.shelf2
        shelf3 = self.shelf3
        assertEqual = self.assertEqual
        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            cmd = vals['move_line_ids'][0]
            write_vals = cmd[2]
            if self1.call_count == 1:
                assertEqual(cmd[0], 0)
                assertEqual(cmd[1], 0)
                assertEqual(write_vals['product_id'], product1.id)
                assertEqual(write_vals['picking_id'], internal_picking.id)
                assertEqual(write_vals['location_id'], shelf3.id)
                assertEqual(write_vals['location_dest_id'], shelf2.id)
                assertEqual(write_vals['qty_done'], 1)
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_internal_picking_reserved_1', login='admin', timeout=180)
            self.assertEqual(self.call_count, 2)

    def test_internal_picking_change_location(self):
        """ Changes the locations directly with the location list displayed in the header.
        """
        # Activates multilocations.
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        # Creates some locations.
        parent_location = self.env["stock.location"].create({
            'name': 'Stock House',
            'barcode': 'stock-house',
        })
        sub_location_1 = self.env["stock.location"].create({
            'name': 'Abandonned Ground Floor',
            'location_id': parent_location.id,
            'barcode': 'first-floor',
        })
        sub_location_2 = self.env["stock.location"].create({
            'name': 'Poorly lit floor',
            'location_id': parent_location.id,
            'barcode': 'second-floor',
        })
        # Creates some quants.
        self.env['stock.quant']._update_available_quantity(self.product1, sub_location_1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, sub_location_2, 1)

        # Creates an internal transfer, from WH/Stock to WH/Stock.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_internal
        picking_form.location_id = parent_location
        picking_form.location_dest_id = parent_location
        # Adds two products from two distinct locations.
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 1

        internal_transfer = picking_form.save()
        internal_transfer.action_confirm()
        internal_transfer.action_assign()

        move_lines = internal_transfer.move_line_ids
        self.assertEqual(move_lines[0].location_id.id, sub_location_1.id)
        self.assertEqual(move_lines[1].location_id.id, sub_location_2.id)
        self.assertEqual(move_lines[0].location_dest_id.id, parent_location.id)
        self.assertEqual(move_lines[1].location_dest_id.id, parent_location.id)

        url = self._get_client_action_url(internal_transfer.id)
        self.start_tour(url, 'test_internal_change_location', login='admin', timeout=180)

        self.assertEqual(move_lines[0].location_id.id, sub_location_1.id)
        self.assertEqual(move_lines[1].location_id.id, sub_location_1.id)
        self.assertEqual(move_lines[0].location_dest_id.id, parent_location.id)
        self.assertEqual(move_lines[1].location_dest_id.id, parent_location.id)

    def test_receipt_from_scratch_with_lots_1(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_1', login='admin', timeout=180)
        self.assertEqual(receipt_picking.move_line_ids.mapped('lot_name'), ['lot1', 'lot2'])

    def test_receipt_from_scratch_with_lots_2(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_2', login='admin', timeout=180)
        self.assertEqual(receipt_picking.move_line_ids.mapped('lot_name'), ['lot1', 'lot2'])
        self.assertEqual(receipt_picking.move_line_ids.mapped('qty_done'), [2, 2])

    def test_receipt_from_scratch_with_lots_3(self):
        """ Scans a non tracked product, then scans a tracked by lots product, then scans a
        production lot twice and checks the tracked product quantity was rightly increased.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_3', login='admin', timeout=180)
        move_lines = receipt_picking.move_line_ids
        self.assertEqual(move_lines[0].product_id.id, self.product1.id)
        self.assertEqual(move_lines[0].qty_done, 1.0)
        self.assertEqual(move_lines[1].product_id.id, self.productlot1.id)
        self.assertEqual(move_lines[1].qty_done, 2.0)
        self.assertEqual(move_lines[1].lot_name, 'lot1')

    def test_receipt_from_scratch_with_lots_4(self):
        """ With picking type options "use_create_lots" and "use existing lots" disabled,
        scan a tracked product 3 times and checks the tracked product quantity was rightly
        increased without the need to enter serial/lot number.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.picking_type_in.use_create_lots = False
        self.picking_type_in.use_existing_lots = False

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_4', login='admin', timeout=180)
        move_lines = receipt_picking.move_line_ids
        self.assertEqual(move_lines[0].product_id.id, self.productserial1.id)
        self.assertEqual(move_lines[0].qty_done, 3.0)

    def test_receipt_from_scratch_with_lots_5(self):
        """ With picking type options "use_create_lots" and "use_existing_lots" enabled, scan a tracked product and enter a serial number already registered (but not used) in the system
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.picking_type_in.use_create_lots = True
        self.picking_type_in.use_existing_lots = True
        snObj = self.env['stock.production.lot']
        snObj.create({'name': 'sn1', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })

        self.env['stock.move'].create({
            'name': 'test_receipt_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productserial1.id,
            'product_uom': self.productserial1.uom_id.id,
            'product_uom_qty': 1,
            'picking_id': receipt_picking.id,
            'picking_type_id': self.picking_type_in.id,
        })

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_sn_1', login='admin', timeout=180)
        move_lines = receipt_picking.move_line_ids
        self.assertEqual(move_lines[0].product_id.id, self.productserial1.id)
        self.assertEqual(move_lines[0].lot_id.name, 'sn1')
        self.assertEqual(move_lines[0].qty_done, 1.0)

    def test_receipt_reserved_1(self):
        """ Open a receipt. Move four units of `self.product1` and four units of
        unit of `self.product2` into shelf1.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(receipt_picking.id)

        move1 = self.env['stock.move'].create({
            'name': 'test_receipt_reserved_1_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipt_picking.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_receipt_reserved_1_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipt_picking.id,
        })
        receipt_picking.action_confirm()
        receipt_picking.action_assign()

        # Mock the calls to write and run the phantomjs script.
        assertEqual = self.assertEqual
        ml1 = move1.move_line_ids
        ml2 = move2.move_line_ids
        shelf1 = self.shelf1
        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            if self1.call_count == 1:
                assertEqual(len(vals['move_line_ids']), 2)
                assertEqual(vals['move_line_ids'][0][:2], [1, ml2.id])
                assertEqual(vals['move_line_ids'][1][:2], [1, ml1.id])
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_receipt_reserved_1', login='admin', timeout=180)
            self.assertEqual(self.call_count, 1)
            self.assertEqual(receipt_picking.move_line_ids[0].location_dest_id.id, shelf1.id)
            self.assertEqual(receipt_picking.move_line_ids[1].location_dest_id.id, shelf1.id)

    def test_receipt_reserved_2(self):
        """ Open a receipt. Move an unit of `self.product1` into shelf1, shelf2, shelf3 and shelf 4.
        Move an unit of `self.product2` into shelf1, shelf2, shelf3 and shelf4 too.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(receipt_picking.id)

        self.env['stock.move'].create({
            'name': 'test_receipt_reserved_1_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipt_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_receipt_reserved_1_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipt_picking.id,
        })
        receipt_picking.action_confirm()
        receipt_picking.action_assign()

        # Mock the calls to write and run the phantomjs script.
        product1, product2 = self.product1, self.product2
        assertEqual = self.assertEqual
        locations = [self.shelf1, self.shelf2, self.shelf3, self.shelf4]
        self1 = self

        def picking_write_mock(self, vals):
            assertEqual(len(vals['move_line_ids']), 2)
            vml1 = vals['move_line_ids'][0][2]
            vml2 = vals['move_line_ids'][1][2]
            assertEqual(vml1['product_id'], product2.id)
            assertEqual(vml2['product_id'], product1.id)
            assertEqual(vml1['location_dest_id'], locations[self1.call_count].id)
            assertEqual(vml2['location_dest_id'], locations[self1.call_count].id)
            self1.call_count += 1
            return picking_write_orig(self, vals)

        self.assertEqual(len(receipt_picking.move_line_ids), 2)
        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_receipt_reserved_2', login='admin', timeout=180)
            self.assertEqual(self.call_count, 4)
            self.assertEqual(len(receipt_picking.move_line_ids), 10)
            self.assertEqual(sum(receipt_picking.move_line_ids.mapped('qty_done')), 8)

    def test_delivery_lot_with_package(self):
        """ Have a delivery for on product tracked by SN, scan a non-reserved SN
        and check the new created line has the right SN's package & owner.
        """
        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_owner = self.env.ref('stock.group_tracking_owner')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_owner.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        # Creates 4 serial numbers and adds 2 qty. for the reservation.
        snObj = self.env['stock.production.lot']
        sn1 = snObj.create({'name': 'sn1', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn2 = snObj.create({'name': 'sn2', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn3 = snObj.create({'name': 'sn3', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn4 = snObj.create({'name': 'sn4', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        package1 = self.env['stock.quant.package'].create({'name': 'pack_sn_1'})
        package2 = self.env['stock.quant.package'].create({'name': 'pack_sn_2'})
        partner = self.env['res.partner'].create({'name': 'Particulier'})
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn1.id,
            'location_id': self.stock_location.id,
            'package_id': package1.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn2.id,
            'location_id': self.stock_location.id,
            'package_id': package1.id,
        }).action_apply_inventory()

        # Creates and confirms the delivery.
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': self.productserial1.name,
            'product_id': self.productserial1.id,
            'product_uom_qty': 2,
            'product_uom': self.productserial1.uom_id.id,
            'picking_id': delivery_picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        # Add 2 more qty. after the reservation.
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn3.id,
            'location_id': self.stock_location.id,
            'package_id': package2.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn4.id,
            'location_id': self.stock_location.id,
            'package_id': package2.id,
            'owner_id': partner.id,
        }).action_apply_inventory()

        # Runs the tour.
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_lot_with_package', login='admin', timeout=180)

        # Checks move lines values after delivery was completed.
        self.assertEqual(delivery_picking.state, "done")
        move_line_1 = delivery_picking.move_line_ids[0]
        move_line_2 = delivery_picking.move_line_ids[1]
        self.assertEqual(move_line_1.lot_id, sn3)
        self.assertEqual(move_line_1.package_id, package2)
        self.assertEqual(move_line_1.owner_id.id, False)
        self.assertEqual(move_line_2.lot_id, sn4)
        self.assertEqual(move_line_2.package_id, package2)
        self.assertEqual(move_line_2.owner_id, partner)

    def test_delivery_reserved_1(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'note': "A Test Note",
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_1_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self1 = self

        # Mock the calls to write and run the phantomjs script.
        def picking_write_mock(self, vals):
            self1.call_count += 1
            return picking_write_orig(self, vals)
        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_delivery_reserved_1', login='admin', timeout=180)
            self.assertEqual(self.call_count, 1)

    def test_delivery_reserved_2(self):
        clean_access_rights(self.env)
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(delivery_picking.id)

        pg_1 = self.env['procurement.group'].create({'name': 'ProcurementGroup1'})
        pg_2 = self.env['procurement.group'].create({'name': 'ProcurementGroup2'})
        partner_1 = self.env['res.partner'].create({'name': 'Parter1'})
        partner_2 = self.env['res.partner'].create({'name': 'Partner2'})
        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
            'group_id': pg_1.id,
            'restrict_partner_id': partner_1.id
        })
        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
            'group_id': pg_2.id,
            'restrict_partner_id': partner_2.id
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        self.assertEqual(len(delivery_picking.move_lines), 2)

        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_delivery_reserved_2', login='admin', timeout=180)
            self.assertEqual(self.call_count, 0)

    def test_delivery_reserved_3(self):
        clean_access_rights(self.env)
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_delivery_reserved_3', login='admin', timeout=180)
            self.assertEqual(self.call_count, 0)

    def test_delivery_from_scratch_1(self):
        """ Scan unreserved lots on a delivery order.
        """
        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        # Adds lot1 and lot2 for productlot1
        lotObj = self.env['stock.production.lot']
        lotObj.create({'name': 'lot1', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        lotObj.create({'name': 'lot2', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})

        # Creates an empty picking.
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.start_tour(url, 'test_delivery_from_scratch_with_lots_1', login='admin', timeout=180)

        lines = delivery_picking.move_line_ids
        self.assertEqual(lines[0].lot_id.name, 'lot1')
        self.assertEqual(lines[1].lot_id.name, 'lot2')
        self.assertEqual(lines[0].qty_done, 2)
        self.assertEqual(lines[1].qty_done, 2)

    def test_delivery_reserved_lots_1(self):
        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_lots_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3,
            'picking_id': delivery_picking.id,
        })

        # Add lot1 et lot2 sur productlot1
        lotObj = self.env['stock.production.lot']
        lot1 = lotObj.create({'name': 'lot1', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        lot2 = lotObj.create({'name': 'lot2', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 2, lot_id=lot2)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        self.assertEqual(delivery_picking.move_lines.state, 'assigned')
        self.assertEqual(len(delivery_picking.move_lines.move_line_ids), 2)

        self.start_tour(url, 'test_delivery_reserved_lots_1', login='admin', timeout=180)

        delivery_picking.invalidate_cache()
        lines = delivery_picking.move_line_ids
        self.assertEqual(lines[0].lot_id.name, 'lot1')
        self.assertEqual(lines[1].lot_id.name, 'lot2')
        self.assertEqual(lines[0].qty_done, 1)
        self.assertEqual(lines[1].qty_done, 2)

    def test_delivery_different_products_with_same_lot_name(self):
        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.productlot2 = self.env['product.product'].create({
            'name': 'productlot2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productlot2',
            'tracking': 'lot',
        })

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        move1 = self.env['stock.move'].create({
            'name': 'test_delivery_different_products_with_same_lot_name_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_delivery_different_products_with_same_lot_name_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
        })

        # Create 2 lots with the same name for productlot1 and productlot2
        lot1 = self.env['stock.production.lot'].create({'name': 'lot1', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        lot2 = self.env['stock.production.lot'].create({'name': 'lot1', 'product_id': self.productlot2.id, 'company_id': self.env.company.id})

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 2, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productlot2, self.stock_location, 2, lot_id=lot2)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self.assertEqual(len(delivery_picking.move_lines), 2)

        self.start_tour(url, 'test_delivery_different_products_with_same_lot_name', login='admin', timeout=180)

        delivery_picking.invalidate_cache()
        lines = delivery_picking.move_line_ids
        self.assertEqual(lines[0].lot_id.name, 'lot1')
        self.assertEqual(lines[0].product_id.name, 'productlot1')
        self.assertEqual(lines[0].qty_done, 2)
        self.assertEqual(lines[1].lot_id.name, 'lot1')
        self.assertEqual(lines[1].product_id.name, 'productlot2')
        self.assertEqual(lines[1].qty_done, 2)

    def test_delivery_from_scratch_sn_1(self):
        """ Scan unreserved serial number on a delivery order.
        """

        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        # Add 4 serial numbers productserial1
        snObj = self.env['stock.production.lot']
        sn1 = snObj.create({'name': 'sn1', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn2 = snObj.create({'name': 'sn2', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn3 = snObj.create({'name': 'sn3', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn4 = snObj.create({'name': 'sn4', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})

        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn1)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn2)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn3)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn4)

        # empty picking
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_lots_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productserial1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        url = self._get_client_action_url(delivery_picking.id)

        self.start_tour(url, 'test_delivery_reserved_with_sn_1', login='admin', timeout=180)

        # TODO: the framework should call invalidate_cache every time a test cursor is asked or
        #       given back
        delivery_picking.invalidate_cache()
        lines = delivery_picking.move_line_ids
        self.assertEqual(lines.mapped('lot_id.name'), ['sn1', 'sn2', 'sn3', 'sn4'])
        self.assertEqual(lines.mapped('qty_done'), [1, 1, 1, 1])

    def test_delivery_using_buttons(self):
        """ Creates a delivery with 3 lines, then:
            - Completes first line with "+1" button;
            - Completes second line with "Add reserved quantities" button;
            - Completes last line with "+1" button and scanning barcode.
        Checks also written quantity on buttons is correctly updated and only
        "+1" button is displayed on new line created by user.
        """
        clean_access_rights(self.env)

        # Creates a new product.
        product3 = self.env['product.product'].create({
            'name': 'product3',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product3',
        })

        # Creates some quants.
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 3)
        self.env['stock.quant']._update_available_quantity(product3, self.stock_location, 4)

        # Create the delivery transfer.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 2
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 3
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = product3
            move.product_uom_qty = 4

        delivery_picking = delivery_form.save()
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_using_buttons', login='admin', timeout=180)

        self.assertEqual(len(delivery_picking.move_line_ids), 4)
        self.assertEqual(delivery_picking.move_line_ids.mapped('qty_done'), [2, 3, 4, 2])

    def test_receipt_reserved_lots_multiloc_1(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipts_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })

        url = self._get_client_action_url(receipts_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_lots_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipts_picking.id,
        })

        # Creates lot1 and lot2 for productlot1.
        lotObj = self.env['stock.production.lot']
        lotObj.create({'name': 'lot1', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        lotObj.create({'name': 'lot2', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})

        receipts_picking.action_confirm()
        receipts_picking.action_assign()

        self.start_tour(url, 'test_receipt_reserved_lots_multiloc_1', login='admin', timeout=180)
        receipts_picking.invalidate_cache()
        lines = receipts_picking.move_line_ids
        self.assertEqual(lines[0].qty_done, 0.0)
        self.assertEqual(lines[0].product_qty, 4.0)
        self.assertEqual(lines.mapped('location_id.name'), ['Vendors'])
        self.assertEqual(lines[3].lot_name, 'lot1')
        self.assertEqual(lines[1].lot_name, 'lot2')
        self.assertEqual(lines[1].qty_done, 2)
        self.assertEqual(lines[2].qty_done, 2)
        self.assertEqual(lines[3].location_dest_id.name, 'Section 2')
        self.assertEqual(lines[1].location_dest_id.name, 'Section 1')

    def test_pack_multiple_scan(self):
        """ Make a reception of two products, put them in pack and validate.
        Then make a delivery, scan the package two times (check the warning) and validate.
        Finally, check that the package is in the customer location.
        """
        clean_access_rights(self.env)
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        # set sequence packages to 1000 to find it easily in the tour
        sequence = self.env['ir.sequence'].search([(
            'code', '=', 'stock.quant.package',
        )], limit=1)
        sequence.write({'number_next_actual': 1000})

        self.start_tour(url, 'test_pack_multiple_scan', login='admin', timeout=180)

        # Check the new package is well delivered
        package = self.env['stock.quant.package'].search([
            ('name', '=', 'PACK0001000')
        ])
        self.assertEqual(package.location_id, self.customer_location)

    def test_pack_common_content_scan(self):
        """ Simulate a picking where 2 packages have the same products
        inside. It should display one barcode line for each package and
        not a common barcode line for both packages.
        """
        clean_access_rights(self.env)
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        # Create a pack and 2 quants in this pack
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK1',
        })
        pack2 = self.env['stock.quant.package'].create({
            'name': 'PACK2',
        })

        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.stock_location,
            quantity=5,
            package_id=pack1,
        )
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product2,
            location_id=self.stock_location,
            quantity=1,
            package_id=pack1,
        )

        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.stock_location,
            quantity=5,
            package_id=pack2,
        )
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product2,
            location_id=self.stock_location,
            quantity=1,
            package_id=pack2,
        )

        self.start_tour(url, 'test_pack_common_content_scan', login='admin', timeout=180)

    def test_pack_multiple_location(self):
        """ Create a package in Shelf 1 and makes an internal transfer to move it to Shelf 2.
        """
        clean_access_rights(self.env)
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.picking_type_internal.active = True

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        # Create a pack and 2 quants in this pack
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK0000666',
        })

        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product2,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )

        self.picking_type_internal.show_entire_packs = True
        self.start_tour(url, 'test_pack_multiple_location', login='admin', timeout=180)

        # Check the new package is well transfered
        self.assertEqual(pack1.location_id, self.shelf2)

    def test_pack_multiple_location_02(self):
        """ Creates an internal transfer and reserves a package. Then this test will scan the
        location source, the package (already in the barcode view) and the location destination.
        """
        clean_access_rights(self.env)
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        # Creates a package with 1 quant in it.
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK0002020',
        })
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )

        # Creates an internal transfer for this package.
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        url = self._get_client_action_url(internal_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_1',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_id': internal_picking.id,
        })
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_pack_multiple_location_02', login='admin', timeout=180)

        # Checks the new package is well transfered.
        self.assertEqual(pack1.location_id, self.shelf2)

    def test_put_in_pack_from_multiple_pages(self):
        """ In an internal picking where prod1 and prod2 are reserved in shelf1 and shelf2, processing
        all these products and then hitting put in pack should move them all in the new pack.
        """
        clean_access_rights(self.env)
        # self.env['stock.picking.type'].search([('active', '=', False)]).write({'active': True})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 1)

        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_multiple_pages',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_multiple_pages',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking.id,
        })

        url = self._get_client_action_url(internal_picking.id)
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_put_in_pack_from_multiple_pages', login='admin', timeout=180)

        pack = self.env['stock.quant.package'].search([])[-1]
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(sum(pack.quant_ids.mapped('quantity')), 4)

    def test_reload_flow(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_reload_flow', login='admin', timeout=180)

        move_line1 = self.env['stock.move.line'].search_count([
            ('product_id', '=', self.product1.id),
            ('location_dest_id', '=', self.shelf1.id),
            ('location_id', '=', self.supplier_location.id),
            ('qty_done', '=', 2),
        ])
        move_line2 = self.env['stock.move.line'].search_count([
            ('product_id', '=', self.product2.id),
            ('location_dest_id', '=', self.shelf1.id),
            ('location_id', '=', self.supplier_location.id),
            ('qty_done', '=', 1),
        ])
        self.assertEqual(move_line1, 1)
        self.assertEqual(move_line2, 1)

    def test_duplicate_serial_number(self):
        """ Simulate a receipt and a delivery with a product tracked by serial
        number. It will try to break the ClientAction by using twice the same
        serial number.
        """
        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_receipt_duplicate_serial_number', login='admin', timeout=180)

        self.start_tour(url, 'test_delivery_duplicate_serial_number', login='admin', timeout=180)

    def test_bypass_source_scan(self):
        """ Scan a lot, package, product without source location scan. """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        lot1 = self.env['stock.production.lot'].create({'name': 'lot1', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        lot2 = self.env['stock.production.lot'].create({'name': 'serial1', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})

        pack1 = self.env['stock.quant.package'].create({
            'name': 'THEPACK',
        })

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf1, 2, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.shelf2, 1, lot_id=lot2)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 4, package_id=pack1)

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_bypass_source_scan_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productserial1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_bypass_source_scan_1_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_bypass_source_scan_1_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self.start_tour(url, 'test_bypass_source_scan', login='admin', timeout=180)

    def test_put_in_pack_from_different_location(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_internal.active = True
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf3, 1)

        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_different_location',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_different_location2',
            'location_id': self.shelf3.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })

        url = self._get_client_action_url(internal_picking.id)
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_put_in_pack_from_different_location', login='admin', timeout=180)
        pack = self.env['stock.quant.package'].search([])[-1]
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(pack.location_id, self.shelf2)

    def test_put_in_pack_before_dest(self):
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_internal.active = True

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf3, 1)

        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_before_dest',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_before_dest',
            'location_id': self.shelf3.id,
            'location_dest_id': self.shelf4.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })

        url = self._get_client_action_url(internal_picking.id)
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_put_in_pack_before_dest', login='admin', timeout=180)
        pack = self.env['stock.quant.package'].search([])[-1]
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(pack.location_id, self.shelf2)

    def test_put_in_pack_scan_package(self):
        """ Put in pack a product line, then scan the newly created package to
        assign it to another lines.
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)

        # Resets package sequence to be sure we'll have the attended packages name.
        seq = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')])
        seq.number_next_actual = 1

        # Creates a delivery with three move lines: two from Section 1 and one from Section 2.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 2
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 1

        delivery = delivery_form.save()
        delivery.action_confirm()
        delivery.action_assign()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_put_in_pack_scan_package', login='admin', timeout=180)

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(len(delivery.move_line_ids), 3)
        for move_line in delivery.move_line_ids:
            self.assertEqual(move_line.result_package_id.name, 'PACK0000001')

    def test_highlight_packs(self):
        clean_access_rights(self.env)
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK001',
        })
        pack2 = self.env['stock.quant.package'].create({
            'name': 'PACK002',
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4, package_id=pack1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4, package_id=pack1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2, package_id=pack2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2, package_id=pack2)

        out_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })

        self.picking_type_out.show_entire_packs = True

        self.env['stock.package_level'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'package_id': pack1.id,
            'is_done': False,
            'picking_id': out_picking.id,
            'company_id': self.env.company.id,
        })

        url = self._get_client_action_url(out_picking.id)
        out_picking.action_confirm()
        out_picking.action_assign()

        self.start_tour(url, 'test_highlight_packs', login='admin', timeout=180)

    def test_picking_owner_scan_package(self):
        grp_owner = self.env.ref('stock.group_tracking_owner')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_owner.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=self.package, owner_id=self.owner)
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_picking_owner_scan_package', login='admin', timeout=180)

        move_line = self.env['stock.move.line'].search([('product_id', '=', self.product1.id)], limit=1)
        self.assertTrue(move_line)

        line_owner = move_line.owner_id
        self.assertEqual(line_owner.id, self.owner.id)

    def test_gs1_reserved_delivery(self):
        """ Process a delivery by scanning multiple quantity multiple times.
        """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        # Creates a product and adds some quantity.
        product_gtin_8 = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '11011019',  # GTIN-8 format.
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        self.env['stock.quant']._update_available_quantity(product_gtin_8, self.stock_location, 99)

        # Creates and process the delivery.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_8
            move.product_uom_qty = 10

        delivery = picking_form.save()
        delivery.action_confirm()
        delivery.action_assign()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_gs1_reserved_delivery', login='admin', timeout=180)

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(len(delivery.move_lines), 1)
        self.assertEqual(delivery.move_lines.product_qty, 14)
        self.assertEqual(len(delivery.move_line_ids), 2)
        self.assertEqual(delivery.move_line_ids[0].qty_done, 10)
        self.assertEqual(delivery.move_line_ids[1].qty_done, 4)

    def test_gs1_receipt_conflicting_barcodes(self):
        """ Creates some receipts for two products but their barcodes mingle
        together once they are adapted for GS1.
        """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product_gtin_8 = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '11011019',  # GTIN-8 format -> Will become 00000011011019.
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        product_gtin_12 = self.env['product.product'].create({
            'name': 'PRO_GTIN_12',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '000011011019',  # GTIN-12 format -> Will also become 00000011011019.
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        # Test for product_gtin_8 only.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_8
            move.product_uom_qty = 1

        receipt_1 = picking_form.save()
        receipt_1.action_confirm()
        receipt_1.action_assign()

        url = self._get_client_action_url(receipt_1.id)
        self.start_tour(url, 'test_gs1_receipt_conflicting_barcodes_1', login='admin', timeout=180)

        self.assertEqual(receipt_1.state, 'done')
        self.assertEqual(len(receipt_1.move_line_ids), 1)
        self.assertEqual(receipt_1.move_line_ids.product_id.id, product_gtin_8.id)

        # Test for product_gtin_12 only.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_12
            move.product_uom_qty = 1

        receipt_2 = picking_form.save()
        receipt_2.action_confirm()
        receipt_2.action_assign()

        url = self._get_client_action_url(receipt_2.id)
        self.start_tour(url, 'test_gs1_receipt_conflicting_barcodes_2', login='admin', timeout=180)

        self.assertEqual(receipt_2.state, 'done')
        self.assertEqual(len(receipt_2.move_line_ids), 1)
        self.assertEqual(receipt_2.move_line_ids.product_id.id, product_gtin_12.id)

        # Test for both product_gtin_8 and product_gtin_12.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_8
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_12
            move.product_uom_qty = 1

        receipt_3 = picking_form.save()
        receipt_3.action_confirm()
        receipt_3.action_assign()

        self.assertEqual(len(receipt_3.move_line_ids), 2)
        url = self._get_client_action_url(receipt_3.id)
        self.start_tour(url, 'test_gs1_receipt_conflicting_barcodes_3', login='admin', timeout=180)

        self.assertEqual(receipt_3.state, 'done')
        self.assertEqual(len(receipt_3.move_line_ids), 3)
        self.assertEqual(receipt_3.move_line_ids[0].product_id.id, product_gtin_8.id)
        self.assertEqual(receipt_3.move_line_ids[0].qty_done, 1)
        self.assertEqual(receipt_3.move_line_ids[1].product_id.id, product_gtin_12.id)
        self.assertEqual(receipt_3.move_line_ids[1].qty_done, 1)
        self.assertEqual(receipt_3.move_line_ids[2].product_id.id, product_gtin_8.id)
        self.assertEqual(receipt_3.move_line_ids[2].qty_done, 1)

    def test_gs1_receipt_lot_serial(self):
        """ Creates a receipt for a product tracked by lot, then process it in the Barcode App.
        """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_tln_gtn8
            move.product_uom_qty = 40

        receipt = picking_form.save()
        receipt.action_confirm()
        receipt.action_assign()

        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_gs1_receipt_lot_serial', login='admin', timeout=180)

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(len(receipt.move_line_ids), 5)
        self.assertEqual(
            receipt.move_line_ids.lot_id.mapped('name'),
            ['b1-b001', 'b1-b002', 'b1-b003', 'b1-b004', 'b1-b005']
        )
        for move_line in receipt.move_line_ids:
            self.assertEqual(move_line.qty_done, 8)

    def test_gs1_receipt_quantity_with_uom(self):
        """ Creates a new receipt and scans barcodes with different combinaisons
        of product and quantity expressed with different UoM and checks the
        quantity is taken only if the UoM is compatible with the product's one.
        """
        clean_access_rights(self.env)
        # Enables the UoM and the GS1 nomenclature.
        grp_uom = self.env.ref('uom.group_uom')
        group_user = self.env.ref('base.group_user')
        group_user.write({'implied_ids': [(4, grp_uom.id)]})
        self.env.user.write({'groups_id': [(4, grp_uom.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        # Configures three products using units, kg and g.
        uom_unit = self.env.ref('product.product_category_all')
        uom_g = self.env.ref('uom.product_uom_gram')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        product_by_units = self.env['product.product'].create({
            'name': 'Product by Units',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15264329',
            'uom_id': uom_unit.id,
        })
        product_by_kg = self.env['product.product'].create({
            'name': 'Product by g',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15264893',
            'uom_id': uom_g.id,
            'uom_po_id': uom_g.id,
        })
        product_by_g = self.env['product.product'].create({
            'name': 'Product by kg',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15264879',
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
        })
        # Creates a new receipt.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        receipt = picking_form.save()
        # Runs the tour.
        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_gs1_receipt_quantity_with_uom', login='admin', timeout=180)
        # Checks the moves' quantities and UoM.
        self.assertTrue(len(receipt.move_lines), 3)
        move1, move2, move3 = receipt.move_lines
        self.assertTrue(move1.product_id.id, product_by_units.id)
        self.assertTrue(move1.quantity_done, 4)
        self.assertTrue(move1.product_uom.id, uom_unit.id)
        self.assertTrue(move2.product_id.id, product_by_kg.id)
        self.assertTrue(move2.quantity_done, 5)
        self.assertTrue(move2.product_uom.id, uom_kg.id)
        self.assertTrue(move3.product_id.id, product_by_g.id)
        self.assertTrue(move3.quantity_done, 1250)
        self.assertTrue(move3.product_uom.id, uom_g.id)

    def test_gs1_package_receipt_and_delivery(self):
        """ Receives some products and scans a GS1 barcode for a package, then
        creates a delivery and scans the same package.
        """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        product1 = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })
        product2 = self.env['product.product'].create({
            'name': 'PRO_GTIN_12',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '584687955629',  # GTIN-12
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_gs1_package_receipt', login='admin', timeout=180)
        # Checks the package is in the stock location with the products.
        package = self.env['stock.quant.package'].search([('name', '=', '546879213579461324')])
        self.assertEqual(len(package), 1)
        self.assertEqual(len(package.quant_ids), 2)
        self.assertEqual(package.quant_ids[0].product_id.id, product1.id)
        self.assertEqual(package.quant_ids[1].product_id.id, product2.id)
        self.assertEqual(package.location_id.id, self.stock_location.id)

        self.start_tour(url, 'test_gs1_package_delivery', login='admin', timeout=180)
        # Checks the package is in the customer's location.
        self.assertEqual(package.location_id.id, self.customer_location.id)


@tagged('post_install', '-at_install')
class TestInventoryAdjustmentBarcodeClientAction(TestBarcodeClientAction):
    def test_inventory_adjustment(self):
        """ Simulate the following actions:
        - Open the inventory from the barcode app.
        - Scan twice the product 1.
        - Edit the line.
        - Add a product with the form view.
        - Validate
        """

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', 'in', [self.product1.id, self.product2.id]),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 2)
        self.assertEqual(inventory_moves.mapped('quantity_done'), [2.0, 2.0])
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done'])

        quants = self.env['stock.quant'].search([('product_id', 'in', [self.product1.id, self.product2.id]),
                                                 ('location_id.usage', '=', 'internal')])
        self.assertEqual(quants.mapped('quantity'), [2.0, 2.0])
        self.assertEqual(quants.mapped('inventory_quantity'), [0, 0])
        self.assertEqual(quants.mapped('inventory_diff_quantity'), [0, 0])

    def test_inventory_adjustment_multi_location(self):
        """ Simulate the following actions:
        - Generate those lines with scan:
        WH/stock product1 qty: 2
        WH/stock product2 qty: 1
        WH/stock/shelf1 product2 qty: 1
        WH/stock/shelf2 product1 qty: 1
        - Validate
        """
        clean_access_rights(self.env)
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment_multi_location', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', 'in', [self.product1.id, self.product2.id]),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 4)
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done', 'done', 'done'])
        inventory_move_in_WH_stock = inventory_moves.filtered(lambda l: l.location_dest_id == self.stock_location)
        self.assertEqual(set(inventory_move_in_WH_stock.mapped('product_id')), set([self.product1, self.product2]))
        self.assertEqual(inventory_move_in_WH_stock.filtered(lambda l: l.product_id == self.product1).quantity_done, 2.0)
        self.assertEqual(inventory_move_in_WH_stock.filtered(lambda l: l.product_id == self.product2).quantity_done, 1.0)

        inventory_move_in_shelf1 = inventory_moves.filtered(lambda l: l.location_dest_id == self.shelf1)
        self.assertEqual(len(inventory_move_in_shelf1), 1)
        self.assertEqual(inventory_move_in_shelf1.product_id, self.product2)
        self.assertEqual(inventory_move_in_shelf1.quantity_done, 1.0)

        inventory_move_in_shelf2 = inventory_moves.filtered(lambda l: l.location_dest_id == self.shelf2)
        self.assertEqual(len(inventory_move_in_shelf2), 1)
        self.assertEqual(inventory_move_in_shelf2.product_id, self.product1)
        self.assertEqual(inventory_move_in_shelf2.quantity_done, 1.0)

    def test_inventory_adjustment_tracked_product(self):
        """ Simulate the following actions:
        - Generate those lines with scan:
        productlot1 with a lot named lot1 (qty 2)
        productserial1 with serial1 (qty 1)
        productserial1 with serial2 (qty 1)
        productserial1 with serial3 (qty 1)
        productlot1 with a lot named lot2 (qty 1)
        productlot1 with a lot named lot3 (qty 1)
        - Validate
        """
        clean_access_rights(self.env)
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment_tracked_product', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', 'in', [self.productlot1.id, self.productserial1.id]),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 6)
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done', 'done', 'done', 'done', 'done'])

        moves_with_lot = inventory_moves.filtered(lambda l: l.product_id == self.productlot1)
        mls_with_lot = self.env['stock.move.line']
        mls_with_sn = self.env['stock.move.line']
        for move in moves_with_lot:
            mls_with_lot |= move._get_move_lines()
        moves_with_sn = inventory_moves.filtered(lambda l: l.product_id == self.productserial1)
        for move in moves_with_sn:
            mls_with_sn |= move._get_move_lines()
        self.assertEqual(len(mls_with_lot), 3)
        self.assertEqual(len(mls_with_sn), 3)
        self.assertEqual(mls_with_lot.mapped('lot_id.name'), ['lot1', 'lot2', 'lot3'])
        self.assertEqual(mls_with_lot.filtered(lambda ml: ml.lot_id.name == 'lot1').qty_done, 3)
        self.assertEqual(mls_with_lot.filtered(lambda ml: ml.lot_id.name == 'lot2').qty_done, 1)
        self.assertEqual(mls_with_lot.filtered(lambda ml: ml.lot_id.name == 'lot3').qty_done, 1)
        self.assertEqual(set(mls_with_sn.mapped('lot_id.name')), set(['serial1', 'serial2', 'serial3']))

    def test_inventory_nomenclature(self):
        """ Simulate scanning a product and its weight
        thanks to the barcode nomenclature """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')

        product_weight = self.env['product.product'].create({
            'name': 'product_weight',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '2145631000000',
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_nomenclature', login='admin', timeout=180)
        quantity = self.env['stock.move.line'].search([
            ('product_id', '=', product_weight.id),
            ('state', '=', 'done'),
            ('location_id', '=', product_weight.property_stock_inventory.id),
        ])

        self.assertEqual(quantity.qty_done, 12.35)

    def test_inventory_package(self):
        """ Simulate an adjustment where a package is scanned and edited """
        clean_access_rights(self.env)
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        pack = self.env['stock.quant.package'].create({
            'name': 'PACK001',
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=pack)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 3, package_id=pack)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, "test_inventory_package", login="admin", timeout=180)

        # Check the package is updated after adjustment
        self.assertDictEqual(
            {q.product_id: q.quantity for q in pack.quant_ids},
            {self.product1: 7, self.product2: 21}
        )

    def test_inventory_owner_scan_package(self):
        group_owner = self.env.ref('stock.group_tracking_owner')
        group_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, group_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, group_owner.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=self.package, owner_id=self.owner)
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_owner_scan_package', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', '=', self.product1.id), ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 1)
        self.assertEqual(inventory_moves.state, 'done')
        self.assertEqual(inventory_moves._get_move_lines().owner_id.id, self.owner.id)

    def test_inventory_using_buttons(self):
        """ Creates an inventory from scratch, then scans products and verifies
        the buttons behavior is right.
        """
        # Adds some quantities for product2.
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 10)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_using_buttons', login='admin', timeout=180)
        product1_quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product1.id),
            ('quantity', '>', 0)
        ])
        self.assertEqual(len(product1_quant), 1)
        self.assertEqual(product1_quant.quantity, 1.0)
        self.assertEqual(product1_quant.location_id.id, self.stock_location.id)

        productlot1_quant = self.env['stock.quant'].search([
            ('product_id', '=', self.productlot1.id),
            ('quantity', '>', 0)
        ])
        self.assertEqual(len(product1_quant), 1)
        self.assertEqual(productlot1_quant.quantity, 1.0)
        self.assertEqual(productlot1_quant.lot_id.name, 'toto-42')
        self.assertEqual(productlot1_quant.location_id.id, self.stock_location.id)

    def test_gs1_inventory_gtin_8(self):
        """ Simulate scanning a product with his gs1 barcode """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_gs1_inventory_gtin_8', login='admin', timeout=180)

        # Checks the inventory adjustment correclty created a move line.
        move_line = self.env['stock.move.line'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('location_id', '=', product.property_stock_inventory.id),
        ])
        self.assertEqual(move_line.qty_done, 78)

    def test_gs1_inventory_product_units(self):
        """ Scans a product with a GS1 barcode containing multiple quantities."""
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_gs1_inventory_product_units', login='admin', timeout=180)

        quantity = self.env['stock.move.line'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('location_id', '=', product.property_stock_inventory.id),
        ])

        self.assertEqual(quantity.qty_done, 102)

    def test_gs1_inventory_package(self):
        """ Scans existing packages and checks their products are correclty added
        to the inventory adjustment. Then scans some products, scans a new package
        and checks the package was created and correclty assigned to those products.
        """
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        # Creates a first package in Section 1 and adds some products.
        pack_1 = self.env['stock.quant.package'].create({'name': '987654123487568456'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 8, package_id=pack_1)
        # Creates a second package in Section 2 and adds some other products.
        pack_2 = self.env['stock.quant.package'].create({'name': '487325612456785124'})
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 6, package_id=pack_2)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_gs1_inventory_package', login='admin', timeout=180)

        pack_3 = self.env['stock.quant.package'].search([('name', '=', '122333444455555670')])
        self.assertEqual(pack_3.location_id.id, self.shelf2.id)
        self.assertEqual(pack_3.quant_ids.product_id.ids, [product.id])

    def test_gs1_inventory_lot_serial(self):
        """ Checks tracking numbers and quantites are correctly got from GS1
        barcodes for tracked products."""
        clean_access_rights(self.env)
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product_lot = self.env['product.product'].create({
            'name': 'PRO_GTIN_12_lot',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '111155555717',  # GTIN-12 format
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'tracking': 'lot',
        })

        product_serial = self.env['product.product'].create({
            'name': 'PRO_GTIN_14_serial',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15222222222219',  # GTIN-14 format
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'tracking': 'serial',
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_gs1_inventory_lot_serial', login='admin', timeout=180)

        smls_lot = self.env['stock.move.line'].search([
            ('product_id', '=', product_lot.id),
            ('state', '=', 'done'),
            ('location_id', '=', product_lot.property_stock_inventory.id),
        ])
        self.assertEqual(len(smls_lot), 3)
        self.assertEqual(smls_lot[0].qty_done, 10)
        self.assertEqual(smls_lot[1].qty_done, 15)
        self.assertEqual(smls_lot[2].qty_done, 20)
        self.assertEqual(
            smls_lot.lot_id.mapped('name'),
            ['LOT-AAA', 'LOT-AAB', 'LOT-AAC']
        )

        smls_serial = self.env['stock.move.line'].search([
            ('product_id', '=', product_serial.id),
            ('state', '=', 'done'),
            ('location_id', '=', product_serial.property_stock_inventory.id),
        ])
        self.assertEqual(len(smls_serial), 5)
        self.assertEqual(smls_serial[0].qty_done, 1)
        self.assertEqual(smls_serial[1].qty_done, 1)
        self.assertEqual(smls_serial[2].qty_done, 1)
        self.assertEqual(smls_serial[3].qty_done, 20)
        self.assertEqual(smls_serial[4].qty_done, 1)
        self.assertEqual(
            smls_serial.lot_id.mapped('name'),
            ['Serial1', 'Serial2', 'Serial3', 'Serial4']
        )
