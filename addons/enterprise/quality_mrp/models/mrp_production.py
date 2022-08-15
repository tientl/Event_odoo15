# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    check_ids = fields.One2many('quality.check', 'production_id', string="Checks")
    quality_check_todo = fields.Boolean(compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', "production_id", string="Alerts")
    quality_alert_count = fields.Integer(compute='_compute_quality_alert_count')

    def _compute_quality_alert_count(self):
        for production in self:
            production.quality_alert_count = len(production.quality_alert_ids)

    def _compute_check(self):
        for production in self:
            todo = False
            fail = False
            for check in production.check_ids:
                if check.quality_state == 'none':
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            production.quality_check_fail = fail
            production.quality_check_todo = todo

    # Crap but we should remove it after freeze due to brutal modification it will bring
    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        for production in self:
            if production.state in ['confirmed', 'to_close', 'progress'] and ('lot_producing_id' in vals or 'qty_producing' in vals):
                finished_product_move = production.move_finished_ids.filtered(
                    lambda move: move.product_id == production.product_id)
                if not finished_product_move.move_line_ids:
                    move_line_vals = finished_product_move._prepare_move_line_vals()
                    move_line_vals.update({
                        'lot_id': vals.get('lot_producing_id'),
                        'production_id': production.id,
                    })
                    self.env['stock.move.line'].create(move_line_vals)
                elif 'lot_producing_id' in vals:
                    finished_product_move.move_line_ids.write(
                        {'lot_id': vals.get('lot_producing_id')})
        return res

    def button_quality_alert(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['views'] = [(False, 'form')]
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_production_id': self.id,
        }
        return action

    def button_mark_done(self):
        for order in self:
            if any(x.quality_state == 'none' for x in order.check_ids):
                raise UserError(_('You still need to do the quality checks!'))
        return super(MrpProduction, self).button_mark_done()

    def open_quality_alert_mo(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_production_id': self.id,
            }
        action['domain'] = [('id', 'in', self.quality_alert_ids.ids)]
        action['views'] = [(False, 'tree'),(False,'form')]
        if self.quality_alert_count == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.quality_alert_ids.id
        return action

    def check_quality(self):
        self.ensure_one()
        checks = self.check_ids.filtered(lambda x: x.quality_state == 'none')
        if checks:
            return checks.action_open_quality_check_wizard()

    def action_cancel(self):
        res = super(MrpProduction, self).action_cancel()
        self.sudo().mapped('check_ids').filtered(lambda x: x.quality_state == 'none').unlink()
        return res
