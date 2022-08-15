# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpProductionWorkcenterLine(models.Model):
    _inherit = "mrp.workorder"

    measure = fields.Float(related='current_quality_check_id.measure', readonly=False)
    measure_success = fields.Selection(related='current_quality_check_id.measure_success', readonly=False)
    norm_unit = fields.Char(related='current_quality_check_id.norm_unit', readonly=False)

    def do_pass(self):
        self.ensure_one()
        self.current_quality_check_id.do_pass()
        return self._next()

    def do_fail(self):
        self.ensure_one()
        self.current_quality_check_id.do_fail()
        return self._next()

    def do_measure(self):
        self.ensure_one()
        self.current_quality_check_id.do_measure()
        return self._next()

    def _next(self, continue_production=False):
        self.ensure_one()
        old_check_id = self.current_quality_check_id
        result = super(MrpProductionWorkcenterLine, self)._next(continue_production=continue_production)
        if old_check_id.quality_state == 'fail':
            return {
                'name': _('Quality Check Failed'),
                'type': 'ir.actions.act_window',
                'res_model': 'quality.check.wizard',
                'views': [(self.env.ref('quality_control.quality_check_wizard_form_failure').id, 'form')],
                'target': 'new',
                'context': {**self.env.context, **{
                    'default_check_ids': [old_check_id.id],
                    'default_current_check_id': old_check_id.id,
                    'default_test_type': old_check_id.test_type,
                    'default_failure_message': old_check_id.failure_message,
                    'default_warning_message': old_check_id.warning_message,
                }},
            }
        return result

    def button_quality_alert(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['target'] = 'new'
        action['views'] = [(False, 'form')]
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_workorder_id': self.id,
            'default_production_id': self.production_id.id,
            'default_workcenter_id': self.workcenter_id.id,
            'discard_on_footer_button': True,
        }
        return action

    def button_finish(self):
        """ When using the Done button of the simplified view, validate directly some types of quality checks
        """
        for check in self.check_ids:
            if check.quality_state in ['pass', 'fail']:
                continue
            if check.test_type in ['register_consumed_materials', 'register_byproducts', 'instructions']:
                check.quality_state = 'pass'
            else:
                raise UserError(_("You first need to complete the Quality Check using the Tablet View before marking the Operation as Done."))
        return super().button_finish()
