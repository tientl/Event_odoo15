# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class WorksheetTemplate(models.Model):
    _inherit = 'worksheet.template'

    @api.model
    def _default_quality_check_template_fields(self):
        return [
            (0, 0, {
                'name': 'x_passed',
                'ttype': 'boolean',
                'field_description': 'Passed',
            })
        ]

    @api.model
    def _default_quality_check_worksheet_form_arch(self):
        return """
            <form create="false" js_class="worksheet_validation">
                <sheet>
                    <h1 invisible="context.get('studio') or context.get('default_x_quality_check_id')">
                        <field name="x_quality_check_id" domain="[('test_type', '=', 'worksheet')]"/>
                    </h1>
                    <group>
                        <group>
                            <field name="x_comments"/>
                            <field name="x_passed"/>
                        </group>
                        <group>
                        </group>
                    </group>
                </sheet>
            </form>
        """

    @api.model
    def _get_quality_check_user_group(self):
        return self.env.ref('quality.group_quality_user')

    @api.model
    def _get_quality_check_manager_group(self):
        return self.env.ref('quality.group_quality_manager')

    @api.model
    def _get_quality_check_access_all_groups(self):
        return self.env.ref('quality.group_quality_manager')

    @api.model
    def _get_quality_check_module_name(self):
        return 'quality_control_worksheet'

    @api.model
    def _get_models_to_check_dict(self):
        res = super()._get_models_to_check_dict()
        res['quality.check'] = [('quality.check', 'Quality Check'), ('quality.point', 'Quality Point')]
        return res
