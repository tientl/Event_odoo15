from odoo import fields, models, api,  _


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    def _get_field_service_project_values(self):
        project_name = _("Field Service")
        type_ids = [
            (4, self.env.ref('industry_fsm.planning_project_stage_0').id),
            (4, self.env.ref('industry_fsm.planning_project_stage_1').id)]
        return [{
            'name': project_name,
            'is_fsm': True,
            'allow_timesheets': True,
            'type_ids': type_ids,
            'company_id': company.id
        } for company in self]

    @api.model
    def create(self, vals):
        new_company = super(ResCompany, self).create(vals)
        self.env['project.project'].sudo().create(new_company._get_field_service_project_values())
        return new_company
