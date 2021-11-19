# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _inherit = 'mrp.workcenter'

    def action_work_order(self):
        if not self.env.context.get('desktop_list_view', False):
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            return action
        else:
            return super(MrpWorkcenter, self).action_work_order()


class MrpProductionWorkcenterLine(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'barcodes.barcode_events_mixin']

    quality_point_ids = fields.Many2many('quality.point', compute='_compute_quality_point_ids', store=True)
    quality_point_count = fields.Integer('Steps', compute='_compute_quality_point_count')

    check_ids = fields.One2many('quality.check', 'workorder_id')
    skipped_check_ids = fields.One2many('quality.check', 'workorder_id', domain=[('quality_state', '=', 'none')])
    finished_product_check_ids = fields.Many2many('quality.check', compute='_compute_finished_product_check_ids')
    quality_check_todo = fields.Boolean(compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', 'workorder_id')
    quality_alert_count = fields.Integer(compute="_compute_quality_alert_count")

    current_quality_check_id = fields.Many2one(
        'quality.check', "Current Quality Check", check_company=True)

    # QC-related fields
    allow_producing_quantity_change = fields.Boolean('Allow Changes to Producing Quantity', default=True)
    component_id = fields.Many2one('product.product', related='current_quality_check_id.component_id')
    component_tracking = fields.Selection(related='component_id.tracking', string="Is Component Tracked")
    component_remaining_qty = fields.Float('Remaining Quantity for Component', compute='_compute_component_data', digits='Product Unit of Measure')
    component_uom_id = fields.Many2one('uom.uom', compute='_compute_component_data', string="Component UoM")
    control_date = fields.Datetime(related='current_quality_check_id.control_date', readonly=False)
    is_first_step = fields.Boolean('Is First Step')
    is_last_step = fields.Boolean('Is Last Step')
    is_last_lot = fields.Boolean('Is Last lot', compute='_compute_is_last_lot')
    is_first_started_wo = fields.Boolean('Is The first Work Order', compute='_compute_is_last_unfinished_wo')
    is_last_unfinished_wo = fields.Boolean('Is Last Work Order To Process', compute='_compute_is_last_unfinished_wo', store=False)
    lot_id = fields.Many2one(related='current_quality_check_id.lot_id', readonly=False)
    move_id = fields.Many2one(related='current_quality_check_id.move_id', readonly=False)
    move_line_id = fields.Many2one(related='current_quality_check_id.move_line_id', readonly=False)
    move_line_ids = fields.One2many(related='move_id.move_line_ids')
    note = fields.Html(related='current_quality_check_id.note')
    skip_completed_checks = fields.Boolean('Skip Completed Checks', readonly=True)
    quality_state = fields.Selection(related='current_quality_check_id.quality_state', string="Quality State", readonly=False)
    qty_done = fields.Float(related='current_quality_check_id.qty_done', readonly=False)
    test_type_id = fields.Many2one('quality.point.test_type', 'Test Type', related='current_quality_check_id.test_type_id')
    test_type = fields.Char(related='test_type_id.technical_name')
    user_id = fields.Many2one(related='current_quality_check_id.user_id', readonly=False)
    worksheet_page = fields.Integer('Worksheet page')
    picture = fields.Binary(related='current_quality_check_id.picture', readonly=False)
    additional = fields.Boolean(related='current_quality_check_id.additional')
    component_qty_to_do = fields.Float(compute='_compute_component_qty_to_do')

    @api.depends('operation_id')
    def _compute_quality_point_ids(self):
        for workorder in self:
            quality_points = workorder.operation_id.quality_point_ids
            quality_points = quality_points.filtered(lambda qp: not qp.product_ids or workorder.production_id.product_id in qp.product_ids)
            workorder.quality_point_ids = quality_points

    @api.depends('operation_id')
    def _compute_quality_point_count(self):
        for workorder in self:
            quality_point = workorder.operation_id.quality_point_ids
            workorder.quality_point_count = len(quality_point)

    @api.depends('qty_done', 'component_remaining_qty')
    def _compute_component_qty_to_do(self):
        for wo in self:
            wo.component_qty_to_do = wo.qty_done - wo.component_remaining_qty

    @api.depends('qty_producing', 'qty_remaining')
    def _compute_is_last_lot(self):
        for wo in self:
            precision = wo.production_id.product_uom_id.rounding
            wo.is_last_lot = float_compare(wo.qty_producing, wo.qty_remaining, precision_rounding=precision) >= 0

    @api.depends('production_id.workorder_ids')
    def _compute_is_last_unfinished_wo(self):
        for wo in self:
            wo.is_first_started_wo = all(wo.state != 'done' for wo in (wo.production_id.workorder_ids - wo))
            other_wos = wo.production_id.workorder_ids - wo
            other_states = other_wos.mapped(lambda w: w.state == 'done')
            wo.is_last_unfinished_wo = all(other_states)

    @api.depends('check_ids')
    def _compute_finished_product_check_ids(self):
        for wo in self:
            wo.finished_product_check_ids = wo.check_ids.filtered(lambda c: c.finished_product_sequence == wo.qty_produced)

    @api.depends('state', 'quality_state', 'current_quality_check_id', 'qty_producing',
                 'component_tracking', 'test_type', 'component_id',
                 'move_finished_ids.state', 'move_finished_ids.product_id',
                 'move_raw_ids.state', 'move_raw_ids.product_id',
                 )
    def _compute_component_data(self):
        self.component_remaining_qty = False
        self.component_uom_id = False
        for wo in self.filtered(lambda w: w.state not in ('done', 'cancel')):
            if wo.test_type in ('register_byproducts', 'register_consumed_materials'):
                if wo.quality_state == 'none':
                    completed_lines = wo.move_line_ids.filtered(lambda l: l.lot_id) if wo.component_id.tracking != 'none' else wo.move_line_ids
                    if not self.move_id.additional:
                        wo.component_remaining_qty = self._prepare_component_quantity(wo.move_id, wo.qty_producing) - sum(completed_lines.mapped('qty_done'))
                    else:
                        wo.component_remaining_qty = self._prepare_component_quantity(wo.move_id, wo.qty_remaining) - sum(completed_lines.mapped('qty_done'))
                wo.component_uom_id = wo.move_id.product_uom

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        if self.component_id:
            self._update_component_quantity()

    def action_back(self):
        self.ensure_one()
        if self.is_user_working and self.working_state != 'blocked':
            self.button_pending()

    def action_cancel(self):
        self.mapped('check_ids').filtered(lambda c: c.quality_state == 'none').sudo().unlink()
        return super(MrpProductionWorkcenterLine, self).action_cancel()

    def action_generate_serial(self):
        self.ensure_one()
        self.finished_lot_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
            'name': self.env['stock.production.lot']._get_next_serial(self.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        })

    def action_print(self):
        if self.product_id.uom_id.category_id == self.env.ref('uom.product_uom_categ_unit'):
            qty = int(self.qty_producing)
        else:
            qty = 1

        quality_point_id = self.current_quality_check_id.point_id
        report_type = quality_point_id.test_report_type

        if self.product_id.tracking == 'none':
            if report_type == 'zpl':
                xml_id = 'stock.label_barcode_product_product'
            else:
                xml_id = 'product.report_product_product_barcode'
            res = self.env.ref(xml_id).report_action([self.product_id.id] * qty)
        else:
            if self.finished_lot_id:
                if report_type == 'zpl':
                    xml_id = 'stock.label_lot_template'
                else:
                    xml_id = 'stock.action_report_lot_label'
                res = self.env.ref(xml_id).report_action([self.finished_lot_id.id] * qty)
            else:
                raise UserError(_('You did not set a lot/serial number for '
                                'the final product'))

        res['id'] = self.env.ref(xml_id).id

        # The button goes immediately to the next step
        self._next()
        return res

    def _create_subsequent_checks(self):
        """ When processing a step with regiter a consumed material
        that's a lot we will some times need to create a new
        intermediate check.
        e.g.: Register 2 product A tracked by SN. We will register one
        with the current checks but we need to generate a second step
        for the second SN. Same for lot if the user wants to use more
        than one lot.
        """
        # Create another quality check if necessary
        next_check = self.current_quality_check_id.next_check_id
        if next_check.component_id != self.current_quality_check_id.product_id or\
                next_check.point_id != self.current_quality_check_id.point_id:
            # TODO: manage reservation here

            # Creating quality checks
            quality_check_data = {
                'workorder_id': self.id,
                'product_id': self.product_id.id,
                'company_id': self.company_id.id,
                'finished_product_sequence': self.qty_produced,
            }
            if self.current_quality_check_id.point_id:
                quality_check_data.update({
                    'point_id': self.current_quality_check_id.point_id.id,
                    'team_id': self.current_quality_check_id.point_id.team_id.id,
                })
            else:
                quality_check_data.update({
                    'component_id': self.current_quality_check_id.component_id.id,
                    'test_type_id': self.current_quality_check_id.test_type_id.id,
                    'team_id': self.current_quality_check_id.team_id.id,
                })
            move = self.current_quality_check_id.move_id
            quality_check_data.update(self._defaults_from_move(move))
            new_check = self.env['quality.check'].create(quality_check_data)
            new_check._insert_in_chain('after', self.current_quality_check_id)

    def _next(self, continue_production=False):
        """ This function:
        - first: fullfill related move line with right lot and validated quantity.
        - second: Generate new quality check for remaining quantity and link them to the original check.
        - third: Pass to the next check or return a failure message.
        """
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if float_compare(self.qty_producing, 0, precision_rounding=rounding) <= 0:
            raise UserError(_('Please ensure the quantity to produce is greater than 0.'))
        elif self.test_type in ('register_byproducts', 'register_consumed_materials'):
            # Form validation
            # in case we use continue production instead of validate button.
            # We would like to consume 0 and leave lot_id blank to close the consumption
            if self.component_tracking != 'none' and not self.lot_id and self.qty_done != 0:
                raise UserError(_('Please enter a Lot/SN.'))
            if float_compare(self.qty_done, 0, precision_rounding=rounding) < 0:
                raise UserError(_('Please enter a positive quantity.'))

            # Get the move lines associated with our component
            self.component_remaining_qty -= float_round(self.qty_done, precision_rounding=self.move_id.product_uom.rounding or rounding)
            # Write the lot and qty to the move line
            if self.move_line_id:
                rounding = self.move_line_id.product_uom_id.rounding
                if float_compare(self.qty_done, self.move_line_id.product_uom_qty, precision_rounding=rounding) >= 0:
                    self.move_line_id.write({
                        'qty_done': self.qty_done,
                        'lot_id': self.lot_id.id,
                    })
                else:
                    new_qty_reserved = self.move_line_id.product_uom_qty - self.qty_done
                    default = {
                        'product_uom_qty': new_qty_reserved,
                        'qty_done': 0,
                    }
                    self.move_line_id.copy(default=default)
                    self.move_line_id.with_context(bypass_reservation_update=True).write({
                        'product_uom_qty': self.qty_done,
                        'qty_done': self.qty_done,
                    })
                    self.move_line_id.lot_id = self.lot_id
            else:
                line = self.env['stock.move.line'].create(self._create_extra_move_lines())
                self.move_line_id = line[:1]
            if continue_production:
                self._create_subsequent_checks()

        if self.test_type == 'picture' and not self.picture:
            raise UserError(_('Please upload a picture.'))

        if not self.current_quality_check_id._is_pass_fail_applicable():
            self.current_quality_check_id.do_pass()

        self._change_quality_check(position='next', skipped=self.skip_completed_checks)
        if self.test_type in ('register_byproducts', 'register_consumed_materials'):
            self._update_component_quantity()

    def action_skip(self):
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if float_compare(self.qty_producing, 0, precision_rounding=rounding) <= 0:
            raise UserError(_('Please ensure the quantity to produce is greater than 0.'))
        self._change_quality_check(position='next', skipped=self.skip_completed_checks)

    def action_first_skipped_step(self):
        self.ensure_one()
        self.skip_completed_checks = True
        self._change_quality_check(position='first', skipped=True)

    def action_previous(self):
        self.ensure_one()
        # If we are on the summary page, we are out of the checks chain
        if self.current_quality_check_id:
            self._change_quality_check(position='previous')
        else:
            self._change_quality_check(position='last')

    def _change_quality_check(self, position, skipped=False):
        """Change the quality check currently set on the workorder `self`.

        The workorder points to a check. A check belongs to a chain.
        This method allows to change the selected check by moving on the checks
        chain according to `position`.

        :param position: Where we need to change the cursor on the check chain
        :type position: string
        :param skipped: Only navigate throughout skipped checks
        :type skipped: boolean
        """
        self.ensure_one()
        assert position in ['first', 'next', 'previous', 'last']
        checks_to_consider = self.check_ids.filtered(lambda c: c.finished_product_sequence == self.qty_produced)
        if position == 'first':
            check = checks_to_consider.filtered(lambda check: not check.previous_check_id)
        elif position == 'next':
            check = self.current_quality_check_id.next_check_id
        elif position == 'previous':
            check = self.current_quality_check_id.previous_check_id
        else:
            check = checks_to_consider.filtered(lambda check: not check.next_check_id)
        # Get nearest skipped check in case of skipped == True
        while skipped and check and check.quality_state != 'none':
            if position in ('first', 'next'):
                check = check.next_check_id
            else:
                check = check.previous_check_id
        change_worksheet_page = check.point_id.worksheet == 'scroll'
        self.write({
            'allow_producing_quantity_change': not check.previous_check_id and all(c.quality_state == 'none' for c in checks_to_consider) and self.is_first_started_wo,
            'current_quality_check_id': check.id,
            'is_first_step': position == 'first',
            'is_last_step': not check,
            'worksheet_page': check.point_id.worksheet_page if change_worksheet_page else self.worksheet_page,
        })

    def action_menu(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet_menu').id, 'form']],
            'name': _('Menu'),
            'target': 'new',
            'res_id': self.id,
        }

    def action_add_component(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [[self.env.ref('mrp_workorder.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add Component'),
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_type': 'component',
            }
        }

    def action_add_byproduct(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [[self.env.ref('mrp_workorder.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add By-Product'),
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_type': 'byproduct',
            }
        }

    def button_start(self):
        res = super().button_start()
        if self.product_tracking == 'serial' and self.component_id:
            self._update_component_quantity()
        return res

    def button_finish(self):
        self._check_remaining_quality_checks()
        return super().button_finish()

    def _compute_check(self):
        for workorder in self:
            todo = False
            fail = False
            for check in workorder.check_ids:
                if check.quality_state == 'none':
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            workorder.quality_check_fail = fail
            workorder.quality_check_todo = todo

    def _compute_quality_alert_count(self):
        for workorder in self:
            workorder.quality_alert_count = len(workorder.quality_alert_ids)

    def _create_checks(self):
        for wo in self:
            # Track components which have a control point
            processed_move = self.env['stock.move']

            production = wo.production_id

            move_raw_ids = wo.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            move_finished_ids = wo.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_id != wo.production_id.product_id)
            previous_check = self.env['quality.check']
            for point in wo.quality_point_ids:
                # Check if we need a quality control for this point
                if point.check_execute_now():
                    moves = self.env['stock.move']
                    values = {
                        'production_id': production.id,
                        'workorder_id': wo.id,
                        'point_id': point.id,
                        'team_id': point.team_id.id,
                        'company_id': wo.company_id.id,
                        'product_id': production.product_id.id,
                        # Two steps are from the same production
                        # if and only if the produced quantities at the time they were created are equal.
                        'finished_product_sequence': wo.qty_produced,
                        'previous_check_id': previous_check.id,
                    }
                    if point.test_type == 'register_byproducts':
                        moves = move_finished_ids.filtered(lambda m: m.product_id == point.component_id)
                    elif point.test_type == 'register_consumed_materials':
                        moves = move_raw_ids.filtered(lambda m: m.product_id == point.component_id)
                    else:
                        check = self.env['quality.check'].create(values)
                        previous_check.next_check_id = check
                        previous_check = check
                    # Create 'register ...' checks
                    for move in moves:
                        check_vals = values.copy()
                        check_vals.update(wo._defaults_from_move(move))
                        # Create quality check and link it to the chain
                        check_vals.update({'previous_check_id': previous_check.id})
                        check = self.env['quality.check'].create(check_vals)
                        previous_check.next_check_id = check
                        previous_check = check
                    processed_move |= moves

            # Generate quality checks associated with unreferenced components
            moves_without_check = ((move_raw_ids | move_finished_ids) - processed_move).filtered(lambda move: move.has_tracking != 'none' or move.operation_id)
            quality_team_id = self.env['quality.alert.team'].search(['|', ('company_id', '=', wo.company_id.id), ('company_id', '=', False)], limit=1).id
            for move in moves_without_check:
                values = {
                    'production_id': production.id,
                    'workorder_id': wo.id,
                    'product_id': production.product_id.id,
                    'company_id': wo.company_id.id,
                    'component_id': move.product_id.id,
                    'team_id': quality_team_id,
                    # Two steps are from the same production
                    # if and only if the produced quantities at the time they were created are equal.
                    'finished_product_sequence': wo.qty_produced,
                    'previous_check_id': previous_check.id,
                }
                if move in move_raw_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_consumed_materials')
                if move in move_finished_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_byproducts')
                values.update({'test_type_id': test_type.id})
                values.update(wo._defaults_from_move(move))
                check = self.env['quality.check'].create(values)
                previous_check.next_check_id = check
                previous_check = check

            # Set default quality_check
            wo.skip_completed_checks = False
            wo._change_quality_check(position='first')

    def _get_byproduct_move_to_update(self):
        moves = super(MrpProductionWorkcenterLine, self)._get_byproduct_move_to_update()
        return moves.filtered(lambda m: m.product_id.tracking == 'none')

    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        self._check_sn_uniqueness()
        self._check_company()
        if any(x.quality_state == 'none' for x in self.check_ids):
            raise UserError(_('You still need to do the quality checks!'))
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

        if self.production_id.product_id.tracking != 'none' and not self.finished_lot_id and self.move_raw_ids:
            raise UserError(_('You should provide a lot/serial number for the final product'))

        # Suggest a finished lot on the next workorder
        if self.next_work_order_id and self.product_tracking != 'none' and not self.next_work_order_id.finished_lot_id:
            self.production_id.lot_producing_id = self.finished_lot_id
            self.next_work_order_id.finished_lot_id = self.finished_lot_id
        backorder = False
        # Trigger the backorder process if we produce less than expected
        if float_compare(self.qty_producing, self.qty_remaining, precision_rounding=self.product_uom_id.rounding) == -1 and self.is_first_started_wo:
            backorder = self.production_id._generate_backorder_productions(close_mo=False)
            self.production_id.product_qty = self.qty_producing
        else:
            if self.operation_id:
                backorder = (self.production_id.procurement_group_id.mrp_production_ids - self.production_id).filtered(
                    lambda p: p.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_id).state not in ('cancel', 'done')
                )[:1]
            else:
                index = list(self.production_id.workorder_ids).index(self)
                backorder = (self.production_id.procurement_group_id.mrp_production_ids - self.production_id).filtered(
                    lambda p: p.workorder_ids[index].state not in ('cancel', 'done')
                )[:1]

        # One a piece is produced, you can launch the next work order
        self._start_nextworkorder()
        self.button_finish()

        if backorder:
            for wo in (self.production_id | backorder).workorder_ids:
                if wo.state in ('done', 'cancel'):
                    continue
                wo.current_quality_check_id.update(wo._defaults_from_move(wo.move_id))
                if wo.move_id:
                    wo._update_component_quantity()
            if not self.env.context.get('no_start_next'):
                if self.operation_id:
                    return backorder.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_id).open_tablet_view()
                else:
                    index = list(self.production_id.workorder_ids).index(self)
                    return backorder.workorder_ids[index].open_tablet_view()
        return True

    def _create_extra_move_lines(self):
        """Create new sml if quantity produced is bigger than the reserved one"""
        vals_list = []
        # apply putaway
        location_dest_id = self.move_id.location_dest_id._get_putaway_strategy(self.product_id)
        quants = self.env['stock.quant']._gather(self.product_id, self.move_id.location_id, lot_id=self.lot_id, strict=False)
        # Search for a sub-locations where the product is available.
        # Loop on the quants to get the locations. If there is not enough
        # quantity into stock, we take the move location. Anyway, no
        # reservation is made, so it is still possible to change it afterwards.
        vals = {
            'move_id': self.move_id.id,
            'product_id': self.move_id.product_id.id,
            'location_dest_id': location_dest_id.id,
            'product_uom_qty': 0,
            'product_uom_id': self.move_id.product_uom.id,
            'lot_id': self.lot_id.id,
            'company_id': self.move_id.company_id.id,
        }
        for quant in quants:
            quantity = quant.quantity - quant.reserved_quantity
            quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom_id, rounding_method='HALF-UP')
            rounding = quant.product_uom_id.rounding
            if (float_compare(quant.quantity, 0, precision_rounding=rounding) <= 0 or
                    float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0):
                continue
            vals.update({
                'location_id': quant.location_id.id,
                'qty_done': min(quantity, self.qty_done),
            })

            vals_list.append(vals)
            self.qty_done -= vals['qty_done']
            # If all the qty_done is distributed, we can close the loop
            if float_compare(self.qty_done, 0, precision_rounding=self.product_id.uom_id.rounding) <= 0:
                break

        if float_compare(self.qty_done, 0, precision_rounding=self.product_id.uom_id.rounding) > 0:
            vals.update({
                'location_id': self.move_id.location_id.id,
                'qty_done': self.qty_done,
            })

            vals_list.append(vals)
        return vals_list

    def _defaults_from_move(self, move):
        self.ensure_one()
        vals = {'move_id': move.id}
        move_line_id = move.move_line_ids.filtered(lambda sml: sml._without_quality_checks())[:1]
        if move_line_id:
            vals.update({
                'move_line_id': move_line_id.id,
                'lot_id': move_line_id.lot_id.id,
                'qty_done': move_line_id.product_uom_qty or 1.0
            })
        return vals

    def _check_remaining_quality_checks(self):
        checks_not_process = self.check_ids.filtered(lambda c: c.quality_state == 'none' and c.test_type not in ('register_consumed_materials', 'register_byproducts'))
        if checks_not_process:
            error_msg = _('Please go in the Operations tab and perform the following work orders and their quality checks:\n')
            for check in checks_not_process:
                error_msg += check.workorder_id.workcenter_id.name + ' - ' + check.name
                if check.title:
                    error_msg += ' - ' + check.title
                error_msg += '\n'
            raise UserError(error_msg)

    # --------------------------
    # Buttons from quality.check
    # --------------------------

    def open_tablet_view(self):
        self.ensure_one()
        if not self.is_user_working and self.working_state != 'blocked' and self.state in ('ready', 'waiting', 'progress', 'pending'):
            self.button_start()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
            'res_id': self.id,
            'target': 'fullscreen',
            'flags': {
                'withControlPanel': False,
                'form_view_initial_mode': 'edit',
            },
            'context': {'from_production_order': self.env.context.get('from_production_order')},
        }

    def action_next(self):
        self.ensure_one()
        return self._next()

    def action_continue(self):
        self.ensure_one()
        self._next(continue_production=True)

    def action_open_manufacturing_order(self):
        action = self.with_context(no_start_next=True).do_finish()
        try:
            with self.env.cr.savepoint():
                res = self.production_id.button_mark_done()
                if res is not True:
                    res['context'] = dict(res['context'], from_workorder=True)
                    return res
        except (UserError, ValidationError) as e:
            # log next activity on MO with error message
            self.production_id.activity_schedule(
                'mail.mail_activity_data_warning',
                note=e.name,
                summary=('The %s could not be closed') % (self.production_id.name),
                user_id=self.env.user.id)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.production_id.id,
                'target': 'main',
            }
        return action

    def do_finish(self):
        action = True
        if self.state != 'done':
            action = self.record_production()
        domain = [('state', 'not in', ['done', 'cancel', 'pending'])]
        if action is not True:
            return action
        # workorder tree view action should redirect to the same view instead of workorder kanban view when WO mark as done.
        if self.env.context.get('from_production_order'):
            action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_mrp_workorder_production_specific")
            action['domain'] = expression.AND([domain, [('production_id', 'in', self.production_id.procurement_group_id.mrp_production_ids.ids)]])
            action['target'] = 'main'
            action['context'] = {
                'no_breadcrumbs': True,
            }
        else:
            # workorder tablet view action should redirect to the same tablet view with same workcenter when WO mark as done.
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            action['domain'] = domain
            action['context'] = {
                'form_view_initial_mode': 'edit',
                'no_breadcrumbs': True,
                'search_default_workcenter_id': self.workcenter_id.id
            }
        return action

    def on_barcode_scanned(self, barcode):
        # qty_done field for serial numbers is fixed
        if self.component_tracking != 'serial':
            if not self.lot_id:
                # not scanned yet
                self.qty_done = 1
            elif self.lot_id.name == barcode:
                self.qty_done += 1
            else:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("You are using components from another lot. \nPlease validate the components from the first lot before using another lot.")
                    }
                }

        lot = self.env['stock.production.lot'].search([('name', '=', barcode)])

        if self.component_tracking:
            if not lot:
                # create a new lot
                # create in an onchange is necessary here ("new" cannot work here)
                lot = self.env['stock.production.lot'].with_context(active_mo_id=self.production_id.id).create({
                    'name': barcode,
                    'product_id': self.component_id.id,
                    'company_id': self.company_id.id,
                })
            self.lot_id = lot
        elif self.production_id.product_id.tracking and self.production_id.product_id.tracking != 'none':
            if not lot:
                lot = self.env['stock.production.lot'].create({
                    'name': barcode,
                    'product_id': self.product_id.id,
                    'company_id': self.company_id.id,
                })
            self.finished_lot_id = lot

    def _update_component_quantity(self):
        if self.component_tracking == 'serial':
            self.qty_done = self.product_id.uom_id._compute_quantity(1, self.product_uom_id, rounding_method='HALF-UP')
            return
        move = self.move_id
        # Compute the new quantity for the current component
        rounding = move.product_uom.rounding
        new_qty = self._prepare_component_quantity(move, self.qty_producing)

        # In case the production uom is different than the workorder uom
        # it means the product is serial and production uom is not the reference
        new_qty = self.product_uom_id._compute_quantity(
            new_qty,
            self.production_id.product_uom_id,
            round=False
        )
        qty_todo = float_round(new_qty, precision_rounding=rounding)
        qty_todo = qty_todo - move.quantity_done
        if self.move_line_id and self.move_line_id.lot_id:
            qty_todo = min(self.move_line_id.product_uom_qty, qty_todo)
        self.qty_done = qty_todo

    def _action_confirm(self):
        res = super()._action_confirm()
        self.filtered(lambda wo: not wo.check_ids)._create_checks()
        return res

    def _update_qty_producing(self, quantity):
        if float_is_zero(quantity, precision_rounding=self.product_uom_id.rounding):
            self.check_ids.unlink()
        super()._update_qty_producing(quantity)
