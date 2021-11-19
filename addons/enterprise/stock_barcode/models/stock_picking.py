# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.tools import html2plaintext, is_html_empty


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'barcodes.barcode_events_mixin']
    _barcode_field = 'name'

    def action_cancel_from_barcode(self):
        self.ensure_one()
        view = self.env.ref('stock_barcode.stock_barcode_cancel_operation_view')
        return {
            'name': _('Cancel this operation ?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock_barcode.cancel.operation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_picking_id=self.id),
        }

    @api.model
    def action_open_new_picking(self):
        """ Creates a new picking of the current picking type and open it.

        :return: the action used to open the picking, or false
        :rtype: dict
        """
        context = self.env.context
        if context.get('active_model') == 'stock.picking.type':
            picking_type = self.env['stock.picking.type'].browse(context.get('active_id'))
            if picking_type.exists():
                new_picking = self._create_new_picking(picking_type)
                return new_picking._get_client_action()['action']
        return False

    def action_open_picking(self):
        """ method to open the form view of the current record
        from a button on the kanban view
        """
        self.ensure_one()
        view_id = self.env.ref('stock.view_picking_form').id
        return {
            'name': _('Open picking form'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
        }

    def action_open_picking_client_action(self):
        """ method to open the form view of the current record
        from a button on the kanban view
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_picking_client_action")
        action = dict(action, target='fullscreen')
        action['context'] = {'active_id': self.id}
        action['res_id'] = self.id
        return action

    def action_print_barcode_pdf(self):
        return self.action_open_label_layout()

    def action_print_delivery_slip(self):
        return self.env.ref('stock.action_report_delivery').report_action(self)

    def _get_stock_barcode_data(self):
        # Avoid to get the products full name because code and name are separate in the barcode app.
        self = self.with_context(display_default_code=False)
        move_lines = self.move_line_ids
        lots = move_lines.lot_id
        owners = move_lines.owner_id
        # Fetch all implied products in `self` and adds last used products to avoid additional rpc.
        products = move_lines.product_id
        packagings = products.packaging_ids

        uoms = products.uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms = self.env['uom.uom'].search([])

        # Fetch `stock.quant.package` and `stock.package.type` if group_tracking_lot.
        packages = self.env['stock.quant.package']
        package_types = self.env['stock.package.type']
        if self.env.user.has_group('stock.group_tracking_lot'):
            packages |= move_lines.package_id | move_lines.result_package_id
            packages |= self.env['stock.quant.package']._get_usable_packages()
            package_types = package_types.search([])

        # Fetch `stock.location`
        source_locations = self.env['stock.location'].search([('id', 'child_of', self.location_id.ids)])
        destination_locations = self.env['stock.location'].search([('id', 'child_of', self.location_dest_id.ids)])
        locations = move_lines.location_id | move_lines.location_dest_id | source_locations | destination_locations
        data = {
            "records": {
                "stock.picking": self.read(self._get_fields_stock_barcode(), load=False),
                "stock.move.line": move_lines.read(move_lines._get_fields_stock_barcode(), load=False),
                "product.product": products.read(products._get_fields_stock_barcode(), load=False),
                "product.packaging": packagings.read(packagings._get_fields_stock_barcode(), load=False),
                "res.partner": owners.read(owners._get_fields_stock_barcode(), load=False),
                "stock.location": locations.read(locations._get_fields_stock_barcode(), load=False),
                "stock.package.type": package_types.read(package_types._get_fields_stock_barcode(), False),
                "stock.quant.package": packages.read(packages._get_fields_stock_barcode(), load=False),
                "stock.production.lot": lots.read(lots._get_fields_stock_barcode(), load=False),
                "uom.uom": uoms.read(uoms._get_fields_stock_barcode(), load=False),
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "source_location_ids": source_locations.ids,
            "destination_locations_ids": destination_locations.ids,
        }
        # Extracts pickings' note if it's empty HTML.
        for picking in data['records']['stock.picking']:
            picking['note'] = False if is_html_empty(picking['note']) else html2plaintext(picking['note'])
        return data

    def get_po_to_split_from_barcode(self, barcode):
        """ Returns the lot wizard's action for the move line matching
        the barcode. This method is intended to be called by the
        `picking_barcode_handler` javascript widget when the user scans
        the barcode of a tracked product.
        """
        product_id = self.env['product.product'].search([('barcode', '=', barcode)])
        candidates = self.env['stock.move.line'].search([
            ('picking_id', 'in', self.ids),
            ('product_barcode', '=', barcode),
            ('location_processed', '=', False),
            ('result_package_id', '=', False),
        ])

        action_ctx = dict(
            self.env.context,
            default_picking_id=self.id,
            serial=self.product_id.tracking == 'serial',
            default_product_id=product_id.id,
            candidates=candidates.ids)
        view_id = self.env.ref('stock_barcode.view_barcode_lot_form').id
        return {
            'name': _('Lot/Serial Number Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock_barcode.lot',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': action_ctx}

    def _check_product(self, product, qty=1.0):
        """ This method is called when the user scans a product. Its goal
        is to find a candidate move line (or create one, if necessary)
        and process it by incrementing its `qty_done` field with the
        `qty` parameter.
        """
        # Get back the move line to increase. If multiple are found, chose
        # arbitrary the first one. Filter out the ones processed by
        # `_check_location` and the ones already having a # destination
        # package.
        picking_move_lines = self.move_line_ids_without_package
        if not self.show_reserved:
            picking_move_lines = self.move_line_nosuggest_ids

        corresponding_ml = picking_move_lines.filtered(lambda ml: ml.product_id.id == product.id and not ml.result_package_id and not ml.location_processed and not ml.lots_visible)[:1]

        if corresponding_ml:
            corresponding_ml.qty_done += qty
        else:
            # If a candidate is not found, we create one here. If the move
            # line we add here is linked to a tracked product, we don't
            # set a `qty_done`: a next scan of this product will open the
            # lots wizard.
            picking_type_lots = (self.picking_type_id.use_create_lots or self.picking_type_id.use_existing_lots)
            new_move_line = self.move_line_ids.new({
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'qty_done': (product.tracking == 'none' and picking_type_lots) and qty or 0.0,
                'product_uom_qty': 0.0,
                'date': fields.datetime.now(),
            })
            if self.show_reserved:
                self.move_line_ids_without_package += new_move_line
            else:
                self.move_line_nosuggest_ids += new_move_line
        return True

    def _check_source_package(self, package):
        corresponding_po = self.move_line_ids.filtered(lambda r: r.package_id.id == package.id and r.result_package_id.id == package.id)
        for po in corresponding_po:
            po.qty_done = po.product_uom_qty
        if corresponding_po:
            self.package_level_ids_details.filtered(lambda p: p.package_id == package).is_done = True
            return True
        else:
            return False

    def _check_destination_package(self, package):
        """ This method is called when the user scans a package currently
        located in (or in any of the children of) the destination location
        of the picking. Its goal is to set this package as a destination
        package for all the processed move lines not having a destination
        package.
        """
        corresponding_ml = self.move_line_ids.filtered(lambda ml: not ml.result_package_id and float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding) == 1)
        # If the user processed the whole reservation (or more), simply
        # write the `package_id` field.
        # If the user processed less than the reservation, split the
        # concerned move line in two: one where the `package_id` field
        # is set with the processed quantity as `qty_done` and another
        # one with the initial values.
        for ml in corresponding_ml:
            rounding = ml.product_uom_id.rounding
            if float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=rounding) == -1:
                self.move_line_ids += self.move_line_ids.new({
                    'product_id': ml.product_id.id,
                    'package_id': ml.package_id.id,
                    'product_uom_id': ml.product_uom_id.id,
                    'location_id': ml.location_id.id,
                    'location_dest_id': ml.location_dest_id.id,
                    'qty_done': 0.0,
                    'move_id': ml.move_id.id,
                    'date': fields.datetime.now(),
                })
            ml.result_package_id = package.id
        return True

    def _check_destination_location(self, location):
        """ This method is called when the user scans a location. Its goal
        is to find the move lines previously processed and write the scanned
        location as their `location_dest_id` field.
        """
        # Get back the move lines the user processed. Filter out the ones where
        # this method was already applied thanks to `location_processed`.
        corresponding_ml = self.move_line_ids.filtered(lambda ml: not ml.location_processed and float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding) == 1)

        # If the user processed the whole reservation (or more), simply
        # write the `location_dest_id` and `location_processed` fields
        # on the concerned move line.
        # If the user processed less than the reservation, split the
        # concerned move line in two: one where the `location_dest_id`
        # and `location_processed` fields are set with the processed
        # quantity as `qty_done` and another one with the initial values.
        for ml in corresponding_ml:
            rounding = ml.product_uom_id.rounding
            if float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=rounding) == -1:
                self.move_line_ids += self.move_line_ids.new({
                    'product_id': ml.product_id.id,
                    'package_id': ml.package_id.id,
                    'product_uom_id': ml.product_uom_id.id,
                    'location_id': ml.location_id.id,
                    'location_dest_id': ml.location_dest_id.id,
                    'qty_done': 0.0,
                    'move_id': ml.move_id.id,
                    'date': fields.datetime.now(),
                })
            ml.update({
                'location_processed': True,
                'location_dest_id': location.id,
            })
        return True

    @api.model
    def _create_new_picking(self, picking_type):
        """ Create a new picking for the given picking type.

        :param picking_type:
        :type picking_type: :class:`~odoo.addons.stock.models.stock_picking.PickingType`
        :return: a new picking
        :rtype: :class:`~odoo.addons.stock.models.stock_picking.Picking`
        """
        # Find source and destination Locations
        location_dest_id, location_id = picking_type.warehouse_id._get_partner_locations()
        if picking_type.default_location_src_id:
            location_id = picking_type.default_location_src_id
        if picking_type.default_location_dest_id:
            location_dest_id = picking_type.default_location_dest_id

        # Create and confirm the picking
        return self.env['stock.picking'].create({
            'user_id': False,
            'picking_type_id': picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'immediate_transfer': True,
        })

    def _get_client_action(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_picking_client_action")
        action = dict(action, target='fullscreen')
        action['context'] = {'active_id': self.id}
        return {'action': action}

    def _get_fields_stock_barcode(self):
        """ List of fields on the stock.picking object that are needed by the
        client action. The purpose of this function is to be overridden in order
        to inject new fields to the client action.
        """
        return [
            'move_line_ids',
            'picking_type_id',
            'location_id',
            'location_dest_id',
            'name',
            'state',
            'picking_type_code',
            'company_id',
            'immediate_transfer',
            'note',
            'picking_type_entire_packs',
            'use_create_lots',
            'use_existing_lots',
        ]

    def on_barcode_scanned(self, barcode):
        if not self.env.company.nomenclature_id:
            # Logic for products
            product = self.env['product.product'].search(['|', ('barcode', '=', barcode), ('default_code', '=', barcode)], limit=1)
            if product:
                if self._check_product(product):
                    return

            product_packaging = self.env['product.packaging'].search([('barcode', '=', barcode)], limit=1)
            if product_packaging:
                if self._check_product(product_packaging.product_id, product_packaging.qty):
                    return

            # Logic for packages in source location
            if self.move_line_ids:
                package_source = self.env['stock.quant.package'].search([('name', '=', barcode), ('location_id', 'child_of', self.location_id.id)], limit=1)
                if package_source:
                    if self._check_source_package(package_source):
                        return

            # Logic for packages in destination location
            package = self.env['stock.quant.package'].search([('name', '=', barcode), '|', ('location_id', '=', False), ('location_id', 'child_of', self.location_dest_id.id)], limit=1)
            if package:
                if self._check_destination_package(package):
                    return

            # Logic only for destination location
            location = self.env['stock.location'].search(['|', ('name', '=', barcode), ('barcode', '=', barcode)], limit=1)
            if location and location.search_count([('id', '=', location.id), ('id', 'child_of', self.location_dest_id.ids)]):
                if self._check_destination_location(location):
                    return
        else:
            parsed_result = self.env.company.nomenclature_id.parse_barcode(barcode)
            if parsed_result['type'] in ['weight', 'product']:
                if parsed_result['type'] == 'weight':
                    product_barcode = parsed_result['base_code']
                    qty = parsed_result['value']
                else:  # product
                    product_barcode = parsed_result['code']
                    qty = 1.0
                product = self.env['product.product'].search(['|', ('barcode', '=', product_barcode), ('default_code', '=', product_barcode)], limit=1)
                if product:
                    if self._check_product(product, qty):
                        return

            if parsed_result['type'] == 'package':
                if self.move_line_ids:
                    package_source = self.env['stock.quant.package'].search([('name', '=', parsed_result['code']), ('location_id', 'child_of', self.location_id.id)], limit=1)
                    if package_source:
                        if self._check_source_package(package_source):
                            return
                package = self.env['stock.quant.package'].search([('name', '=', parsed_result['code']), '|', ('location_id', '=', False), ('location_id', 'child_of', self.location_dest_id.id)], limit=1)
                if package:
                    if self._check_destination_package(package):
                        return

            if parsed_result['type'] == 'location':
                location = self.env['stock.location'].search(['|', ('name', '=', parsed_result['code']), ('barcode', '=', parsed_result['code'])], limit=1)
                if location and location.search_count([('id', '=', location.id), ('id', 'child_of', self.location_dest_id.ids)]):
                    if self._check_destination_location(location):
                        return

            product_packaging = self.env['product.packaging'].search([('barcode', '=', parsed_result['code'])], limit=1)
            if product_packaging:
                if self._check_product(product_packaging.product_id, product_packaging.qty):
                    return

        return {'warning': {
            'title': _('Wrong barcode'),
            'message': _('The barcode "%(barcode)s" doesn\'t correspond to a proper product, package or location.') % {'barcode': barcode}
        }}

    @api.model
    def filter_on_product(self, barcode):
        """ Search for ready pickings for the scanned product. If at least one
        picking is found, returns the picking kanban view filtered on this product.
        """
        product = self.env['product.product'].search_read([('barcode', '=', barcode)], ['id'], limit=1)
        if product:
            product_id = product[0]['id']
            picking_type = self.env['stock.picking.type'].search_read(
                [('id', '=', self.env.context.get('active_id'))],
                ['name'],
            )[0]
            if not self.search_count([
                ('product_id', '=', product_id),
                ('picking_type_id', '=', picking_type['id']),
                ('state', 'not in', ['cancel', 'done', 'draft']),
            ]):
                return {'warning': {
                    'title': _("No %s ready for this product", picking_type['name']),
                }}
            action = self.env['ir.actions.actions']._for_xml_id('stock_barcode.stock_picking_action_kanban')
            action['context'] = dict(self.env.context)
            action['context']['search_default_product_id'] = product_id
            return {'action': action}
        return {'warning': {
            'title': _("No product found for barcode %s", barcode),
            'message': _("Scan a product to filter the transfers."),
        }}


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    def get_action_picking_tree_ready_kanban(self):
        return self._get_action('stock_barcode.stock_picking_action_kanban')
