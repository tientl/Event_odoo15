# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, _
from odoo.fields import Date
from odoo.exceptions import ValidationError

from werkzeug.urls import url_encode


class GenerateSimulationLink(models.TransientModel):
    _name = 'generate.simulation.link'
    _description = 'Generate Simulation Link'

    @api.model
    def default_get(self, fields):
        result = super(GenerateSimulationLink, self).default_get(fields)
        if not set(fields) & set(['contract_id', 'employee_id', 'employee_contract_id', 'applicant_id']):
            return result
        model = self.env.context.get('active_model')
        if model == 'hr.contract':
            contract_id = self.env.context.get('active_id')
            contract = self.env['hr.contract'].sudo().browse(contract_id)
            if not contract.employee_id:
                result['contract_id'] = contract_id
            else:
                result['employee_id'] = contract.employee_id.id
                result['employee_contract_id'] = contract.id
                result['contract_id'] = contract.id
        elif model == 'hr.applicant':
            applicant_id = self.env.context.get('active_id')
            applicant = self.env['hr.applicant'].sudo().browse(applicant_id)
            if not applicant.access_token or applicant.access_token_end_date < Date.today():
                applicant.access_token = uuid.uuid4().hex
                applicant.access_token_end_date = self.env['hr.applicant']._get_access_token_end_date()
            result['applicant_id'] = applicant_id
            contract = applicant.job_id.default_contract_id
            result['contract_id'] = applicant.job_id.default_contract_id.id
            if applicant.job_id:
                result['job_title'] = applicant.job_id.name
        if not result.get('applicant_id') and not contract.contract_update_template_id or result.get('applicant_id') and not contract.sign_template_id:
            raise ValidationError(_('No signature template defined on the contract.'))
        if not contract.hr_responsible_id:
            raise ValidationError(_('No HR responsible defined on the contract.'))
        return result

    def get_contract_domain(self):
        return [
            '|',
            ('employee_id', '=', False),
            ('employee_id', '=', self.employee_contract_id.employee_id.id)]

    contract_id = fields.Many2one(
        'hr.contract', string="Offer Template", required=True, store=True,
        domain="['|', ('employee_id', '=', False), ('employee_id', '=', employee_contract_employee_id)]")
    employee_contract_id = fields.Many2one('hr.contract')
    employee_contract_employee_id = fields.Many2one(related='employee_contract_id.employee_id', string="contract employee")
    employee_id = fields.Many2one('hr.employee')
    final_yearly_costs = fields.Monetary(
        string="Yearly Cost", required=True,
        compute='_compute_from_contract_id', readonly=False, store=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    applicant_id = fields.Many2one('hr.applicant')
    job_title = fields.Char("Job Title", compute='_compute_from_contract_id', store=True, readonly=False)
    contract_start_date = fields.Date("Contract Start Date", default=fields.Date.context_today)

    email_to = fields.Char('Email To', compute='_compute_email_to', store=True, readonly=False)
    url = fields.Char('Offer link', compute='_compute_url')

    @api.depends('employee_id.address_home_id.email', 'applicant_id.email_from')
    def _compute_email_to(self):
        for wizard in self:
            if wizard.employee_id:
                wizard.email_to = wizard.employee_id.address_home_id.email
            elif wizard.applicant_id:
                wizard.email_to = wizard.applicant_id.email_from

    def _get_url_triggers(self):
        return ['applicant_id', 'final_yearly_costs', 'employee_contract_id', 'job_title', 'contract_start_date']

    @api.depends(lambda self: [key for key in self._fields.keys()])
    def _compute_url(self):
        for wizard in self:
            url = wizard.contract_id.get_base_url() + '/salary_package/simulation/contract/%s?' % (wizard.contract_id.id)
            params = {}
            for trigger in self._get_url_triggers():
                if wizard[trigger]:
                    params[trigger] = wizard[trigger].id if isinstance(wizard[trigger], models.BaseModel) else wizard[trigger]
            if wizard.applicant_id:
                params['token'] = wizard.applicant_id.access_token
            if wizard.contract_start_date:
                params['contract_start_date'] = wizard.contract_start_date
            if params:
                url = url + url_encode(params)
            wizard.url = url

    @api.depends('contract_id', 'applicant_id')
    def _compute_from_contract_id(self):
        for wizard in self:
            wizard.final_yearly_costs = wizard.contract_id.final_yearly_costs
            if not wizard.job_title or (wizard.applicant_id and wizard.applicant_id.job_id and wizard.job_title != wizard.applicant_id.job_id.name):
                wizard.job_title = wizard.contract_id.employee_id.job_title or wizard.contract_id.job_id.name

    def name_get(self):
        return [(w.id, w.employee_id.name or w.applicant_id.partner_name) for w in self]

    def send_offer(self):
        try:
            template_id = self.env.ref('hr_contract_salary.mail_template_send_offer').id
        except ValueError:
            template_id = False
        try:
            template_applicant_id = self.env.ref('hr_contract_salary.mail_template_send_offer_applicant').id
        except ValueError:
            template_applicant_id = False
        partner_to = False
        if self.employee_id:
            partner_to = self.employee_id.address_home_id
            if not partner_to:
                raise ValidationError(_("No private address defined on the employee!"))
        elif self.applicant_id:
            partner_to = self.applicant_id.partner_id
            if not partner_to:
                partner_to = self.env['res.partner'].create({
                    'is_company': False,
                    'name': self.applicant_id.partner_name,
                    'email': self.applicant_id.email_from,
                    'phone': self.applicant_id.partner_phone,
                    'mobile': self.applicant_id.partner_mobile
                })
                self.applicant_id.partner_id = partner_to

        if self.applicant_id:
            default_model = 'hr.applicant'
            default_res_id = self.applicant_id.id
            default_use_template = bool(template_applicant_id)
            default_template_id = template_applicant_id
        elif self.employee_contract_id:
            default_model = 'hr.contract'
            default_res_id = self.employee_contract_id.id
            default_use_template = bool(template_id)
            default_template_id = template_id
        else:
            default_model = 'hr.contract'
            default_res_id = self.contract_id.id
            default_use_template = bool(template_id)
            default_template_id = template_id

        ctx = {
            'default_model': default_model,
            'default_res_id': default_res_id,
            'default_use_template': default_use_template,
            'default_template_id': default_template_id,
            'default_composition_mode': 'comment',
            'salary_package_url': self.url,
            'custom_layout': "mail.mail_notification_light",
            'partner_to': partner_to and partner_to.id or False,
            'mail_post_autofollow': False,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [[False, 'form']],
            'target': 'new',
            'context': ctx,
        }
