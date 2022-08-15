# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.fields import Command


class TestType(models.Model):
    _inherit = "quality.point.test_type"

    allow_registration = fields.Boolean(search='_get_domain_from_allow_registration',
            store=False, default=False)

    def _get_domain_from_allow_registration(self, operator, value):
        if value:
            return []
        else:
            return [('technical_name', 'not in', ['register_byproducts', 'register_consumed_materials', 'print_label'])]


class MrpRouting(models.Model):
    _inherit = "mrp.routing.workcenter"

    quality_point_ids = fields.One2many('quality.point', 'operation_id', copy=True)
    quality_point_count = fields.Integer('Steps', compute='_compute_quality_point_count')

    @api.depends('quality_point_ids')
    def _compute_quality_point_count(self):
        read_group_res = self.env['quality.point'].sudo().read_group(
            [('id', 'in', self.quality_point_ids.ids)],
            ['operation_id'], 'operation_id'
        )
        data = dict((res['operation_id'][0], res['operation_id_count']) for res in read_group_res)
        for operation in self:
            operation.quality_point_count = data.get(operation.id, 0)

    def write(self, vals):
        res = super().write(vals)
        if 'bom_id' in vals:
            self.quality_point_ids._change_product_ids_for_bom(self.bom_id)
        return res

    def copy(self, default=None):
        res = super().copy(default)
        if default and "bom_id" in default:
            res.quality_point_ids._change_product_ids_for_bom(res.bom_id)
        return res

    def toggle_active(self):
        self.with_context(active_test=False).quality_point_ids.toggle_active()
        return super().toggle_active()

    def action_mrp_workorder_show_steps(self):
        self.ensure_one()
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_workorder_show_steps")
        ctx = {
            'default_company_id': self.company_id.id,
            'default_operation_id': self.id,
            'default_picking_type_ids': [picking_type_id],
        }
        action.update({'context': ctx, 'domain': [('operation_id', '=', self.id)]})
        return action


class QualityPoint(models.Model):
    _inherit = "quality.point"

    def _default_product_ids(self):
        # Determines a default product from the default operation's BOM.
        operation_id = self.env.context.get('default_operation_id')
        if operation_id:
            bom = self.env['mrp.routing.workcenter'].browse(operation_id).bom_id
            return bom.product_id.ids if bom.product_id else bom.product_tmpl_id.product_variant_id.ids

    is_workorder_step = fields.Boolean(compute='_compute_is_workorder_step')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Step', check_company=True)
    bom_id = fields.Many2one(related='operation_id.bom_id')
    bom_active = fields.Boolean('Related Bill of Material Active', related='bom_id.active')
    component_ids = fields.One2many('product.product', compute='_compute_component_ids')
    product_ids = fields.Many2many(
        default=_default_product_ids,
        domain="operation_id and [('id', 'in', bom_product_ids)] or [('type', 'in', ('product', 'consu')), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    bom_product_ids = fields.One2many('product.product', compute="_compute_bom_product_ids")
    test_type_id = fields.Many2one(
        'quality.point.test_type',
        domain="[('allow_registration', '=', operation_id and is_workorder_step)]")
    test_report_type = fields.Selection([('pdf', 'PDF'), ('zpl', 'ZPL')], string="Report Type", default="pdf", required=True)
    worksheet = fields.Selection([
        ('noupdate', 'Do not update page'),
        ('scroll', 'Scroll to specific page')], string="Worksheet",
        default="noupdate")
    worksheet_page = fields.Integer('Worksheet Page')
    # Used with type register_consumed_materials the product raw to encode.
    component_id = fields.Many2one('product.product', 'Product To Register', check_company=True)

    @api.onchange('bom_product_ids', 'is_workorder_step')
    def _onchange_bom_product_ids(self):
        if self.is_workorder_step and self.bom_product_ids:
            self.product_ids = self.product_ids._origin & self.bom_product_ids
            self.product_category_ids = False

    @api.depends('bom_id.product_id', 'bom_id.product_tmpl_id.product_variant_ids', 'is_workorder_step', 'bom_id')
    def _compute_bom_product_ids(self):
        self.bom_product_ids = False
        points_for_workorder_step = self.filtered(lambda p: p.operation_id and p.bom_id)
        for point in points_for_workorder_step:
            bom_product_ids = point.bom_id.product_id or point.bom_id.product_tmpl_id.product_variant_ids
            point.bom_product_ids = bom_product_ids.filtered(lambda p: not p.company_id or p.company_id == point.company_id._origin)

    @api.depends('product_ids', 'test_type_id', 'is_workorder_step')
    def _compute_component_ids(self):
        self.component_ids = False
        for point in self:
            if not point.is_workorder_step or not self.bom_id or point.test_type not in ('register_consumed_materials', 'register_byproducts'):
                point.component_id = None
                continue
            if point.test_type == 'register_byproducts':
                point.component_ids = point.bom_id.byproduct_ids.product_id
            else:
                bom_products = point.bom_id.product_id or point.bom_id.product_tmpl_id.product_variant_ids
                # If product_ids is set the step will exist only for these product variant then we can filter out for the bom explode
                if point.product_ids:
                    bom_products &= point.product_ids._origin

                component_product_ids = set()
                for product in bom_products:
                    dummy, lines_done = point.bom_id.explode(product, 1.0)
                    component_product_ids |= {line[0].product_id.id for line in lines_done}
                point.component_ids = self.env['product.product'].browse(component_product_ids)

    @api.depends('operation_id', 'picking_type_ids')
    def _compute_is_workorder_step(self):
        for quality_point in self:
            quality_point.is_workorder_step = quality_point.operation_id or quality_point.picking_type_ids and\
                all(pt.code == 'mrp_operation' for pt in quality_point.picking_type_ids)

    def _change_product_ids_for_bom(self, bom_id):
        products = bom_id.product_id or bom_id.product_tmpl_id.product_variant_ids
        self.product_ids = [Command.set(products.ids)]

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id:
            self._change_product_ids_for_bom(self.bom_id)


class QualityAlert(models.Model):
    _inherit = "quality.alert"

    workorder_id = fields.Many2one('mrp.workorder', 'Operation', check_company=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', check_company=True)
    production_id = fields.Many2one('mrp.production', "Production Order", check_company=True)


class QualityCheck(models.Model):
    _inherit = "quality.check"

    workorder_id = fields.Many2one(
        'mrp.workorder', 'Operation', check_company=True)
    workcenter_id = fields.Many2one('mrp.workcenter', related='workorder_id.workcenter_id', store=True, readonly=True)  # TDE: necessary ?
    production_id = fields.Many2one(
        'mrp.production', 'Production Order', check_company=True)

    # doubly linked chain for tablet view navigation
    next_check_id = fields.Many2one('quality.check')
    previous_check_id = fields.Many2one('quality.check')

    # For components registration
    move_id = fields.Many2one(
        'stock.move', 'Stock Move', check_company=True)
    move_line_id = fields.Many2one(
        'stock.move.line', 'Stock Move Line', check_company=True)
    component_id = fields.Many2one(
        'product.product', 'Component', check_company=True)
    component_uom_id = fields.Many2one('uom.uom', related='move_id.product_uom', readonly=True)

    qty_done = fields.Float('Done', digits='Product Unit of Measure')
    finished_lot_id = fields.Many2one('stock.production.lot', 'Finished Lot/Serial', related='production_id.lot_producing_id', store=True)
    additional = fields.Boolean('Register additional product', compute='_compute_additional')

    # Computed fields
    title = fields.Char('Title', compute='_compute_title')
    result = fields.Char('Result', compute='_compute_result')
    quality_state_for_summary = fields.Char('Status Summary', compute='_compute_result')

    # Used to group the steps belonging to the same production
    # We use a float because it is actually filled in by the produced quantity at the step creation.
    finished_product_sequence = fields.Float('Finished Product Sequence Number')

    @api.model_create_multi
    def create(self, values):
        points = self.env['quality.point'].search([
            ('id', 'in', [value.get('point_id') for value in values]),
            ('component_id', '!=', False)
        ])
        for value in values:
            if not value.get('component_id') and value.get('point_id'):
                point = points.filtered(lambda p: p.id == value.get('point_id'))
                if point:
                    value['component_id'] = point.component_id.id
        return super(QualityCheck, self).create(values)

    def _compute_title(self):
        super()._compute_title()
        for check in self:
            if not check.point_id or check.component_id:
                check.title = '{} "{}"'.format(check.test_type_id.display_name, check.component_id.name)

    @api.depends('point_id', 'quality_state', 'component_id', 'component_uom_id', 'lot_id', 'qty_done')
    def _compute_result(self):
        for check in self:
            state = check.quality_state
            check.quality_state_for_summary = _('Done') if state != 'none' else _('To Do')
            if check.quality_state == 'none':
                check.result = ''
            else:
                check.result = check._get_check_result()

    @api.depends('move_id')
    def _compute_additional(self):
        """ The stock_move is linked to additional workorder line only at
        record_production. So line without move during production are additionnal
        ones. """
        for check in self:
            check.additional = not check.move_id

    def _get_check_result(self):
        if self.test_type in ('register_consumed_materials', 'register_byproducts') and self.lot_id:
            return '{} - {}, {} {}'.format(self.component_id.name, self.lot_id.name, self.qty_done, self.component_uom_id.name)
        elif self.test_type in ('register_consumed_materials', 'register_byproducts'):
            return '{}, {} {}'.format(self.component_id.name, self.qty_done, self.component_uom_id.name)
        else:
            return ''

    def _insert_in_chain(self, position, relative):
        """Insert the quality check `self` in a chain of quality checks.

        The chain of quality checks is implicitly given by the `relative` argument,
        i.e. by following its `previous_check_id` and `next_check_id` fields.

        :param position: Where we need to insert `self` according to `relative`
        :type position: string
        :param relative: Where we need to insert `self` in the chain
        :type relative: A `quality.check` record.
        """
        self.ensure_one()
        assert position in ['before', 'after']
        if position == 'before':
            new_previous = relative.previous_check_id
            self.next_check_id = relative
            self.previous_check_id = new_previous
            new_previous.next_check_id = self
            relative.previous_check_id = self
        else:
            new_next = relative.next_check_id
            self.next_check_id = new_next
            self.previous_check_id = relative
            new_next.previous_check_id = self
            relative.next_check_id = self
