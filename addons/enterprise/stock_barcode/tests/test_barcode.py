# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestBarcodeClientAction(HttpCase):
    def test_scan_product_barcode_in_picking_form_view(self):
        """ Checks a product can be scanned in the picking's form view, and the corresponding
        move is incremented when the barcode is valid (depending of the company's nomenclature).
        """
        product_category_all = self.env.ref('product.product_category_all')
        picking_type_in = self.env.ref('stock.picking_type_in')
        supplier_location = self.env.ref('stock.stock_location_suppliers')

        # Creates a product and a receipt for this product.
        product_ean8 = self.env['product.product'].create({
            'name': 'Product EAN8',
            'barcode': '76543210',
            'categ_id': product_category_all.id,
            'type': 'product',
        })
        receipt = self.env['stock.picking'].create({
            'picking_type_id': picking_type_in.id,
            'location_id': supplier_location.id,
            'location_dest_id': picking_type_in.default_location_dest_id.id,
        })
        move = self.env['stock.move'].create({
            'name': product_ean8.name,
            'product_id': product_ean8.id,
            'product_uom_qty': 1,
            'product_uom': product_ean8.uom_id.id,
            'picking_id': receipt.id,
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
        })
        receipt.action_confirm()

        # Using default nomenclature, scans the product's barcode.
        self.assertEqual(move.quantity_done, 0)
        receipt.on_barcode_scanned('76543210')
        self.assertEqual(move.quantity_done, 1, "Product scanned one time: 1 qty. done.")
        receipt.on_barcode_scanned('000076543210')
        self.assertEqual(move.quantity_done, 1, "Wrong barcode, the qty. done shoudn't be incremented.")
        receipt.on_barcode_scanned('0100000076543210')
        self.assertEqual(move.quantity_done, 1, "Can't handle GS1 barcode: shouldn't increment the qty. done.")

        # Using GS1 nomenclature, scans the product's barcode.
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        receipt.on_barcode_scanned('76543210')
        self.assertEqual(move.quantity_done, 2, "Raw barcode should still works.")
        receipt.on_barcode_scanned('000076543210')
        self.assertEqual(move.quantity_done, 2, "Doesn't work with unpadded barcode.")
        receipt.on_barcode_scanned('0100000076543210')
        self.assertEqual(move.quantity_done, 3, "Product's data in GS1 barcode, should increment the qty. done.")
