# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrContractSignDocumentWizard(models.TransientModel):
    _name = 'hr.contract.sign.document.wizard'
    _description = 'Sign document in contract'

    def _group_hr_contract_domain(self):
        group = self.env.ref('hr_contract.group_hr_contract_manager', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []

    def _get_sign_template_ids(self):
        list_template = []
        for template in self.env['sign.template'].search([]):
            distinct_responsible_count = len(template.sign_item_ids.mapped('responsible_id'))
            if distinct_responsible_count == 2 or distinct_responsible_count == 1:
                list_template.append(template.id)
        return list_template

    def _sign_template_domain(self):
        return [('id', 'in', self._get_sign_template_ids())]

    def _default_get_template_warning(self):
        return not bool(self._get_sign_template_ids()) and _('No appropriate template could be found, please make sure you configured them properly.')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'responsible_id' in fields_list and not defaults.get('responsible_id') and defaults.get('contract_id'):
            contract = self.env['hr.contract'].browse(defaults.get('contract_id'))
            defaults['responsible_id'] = contract.hr_responsible_id
        return defaults

    contract_id = fields.Many2one('hr.contract', string='Contract',
        default=lambda self: self.env.context.get('active_id'))
    employee_id = fields.Many2one('hr.employee', string='Employee', compute='_compute_employee')
    responsible_id = fields.Many2one('res.users', string='Responsible', domain=_group_hr_contract_domain)
    employee_role_id = fields.Many2one("sign.item.role", string="Employee Role", required=True, domain="[('id', 'in', sign_template_responsible_ids)]",
        compute='_compute_employee_role_id', store=True, readonly=False,
        help="Employee's role on the templates to sign. The same role must be present in all the templates")
    sign_template_responsible_ids = fields.Many2many('sign.item.role', compute='_compute_responsible_ids')

    sign_template_ids = fields.Many2many('sign.template', string='Documents to sign',
        domain=_sign_template_domain, help="""Documents to sign. Only documents with 1 or 2 different responsible are selectable.
        Documents with 1 responsible will only have to be signed by the employee while documents with 2 different responsible will have to be signed by both the employee and the responsible.
        """, required=True)
    has_both_template = fields.Boolean(compute='_compute_has_both_template')
    template_warning = fields.Char(default=_default_get_template_warning, store=False)

    subject = fields.Char(string="Subject", required=True, default='Signature Request')
    message = fields.Html("Message")
    follower_ids = fields.Many2many('res.partner', string="Copy to")

    @api.depends('sign_template_responsible_ids')
    def _compute_employee_role_id(self):
        for wizard in self:
            if len(wizard.sign_template_responsible_ids) == 1:
                wizard.employee_role_id = wizard.sign_template_responsible_ids

    @api.depends('sign_template_ids.sign_item_ids.responsible_id')
    def _compute_responsible_ids(self):
        for r in self:
            responsible_ids = self.env['sign.item.role']
            for sign_template_id in r.sign_template_ids:
                if responsible_ids:
                    responsible_ids &= sign_template_id.sign_item_ids.responsible_id
                else:
                    responsible_ids |= sign_template_id.sign_item_ids.responsible_id
            r.sign_template_responsible_ids = responsible_ids

    @api.depends('contract_id')
    def _compute_employee(self):
        for contract in self:
            contract.employee_id = contract.contract_id.employee_id

    @api.depends('sign_template_ids')
    def _compute_has_both_template(self):
        for wizard in self:
            wizard.has_both_template = bool(wizard.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 2))

    def validate_signature(self):
        self.ensure_one()
        if not self.employee_id.user_id and not self.employee_id.user_id.partner_id:
            raise ValidationError(_('Employee must be linked to a user and a partner.'))

        sign_request = self.env['sign.request']
        if not self.check_access_rights('create', raise_exception=False):
            sign_request = sign_request.sudo()

        sign_values = []
        sign_templates_employee_ids = self.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 1)
        sign_templates_both_ids = self.sign_template_ids - sign_templates_employee_ids
        for sign_template_id in sign_templates_employee_ids:
            sign_values.append((
                sign_template_id,
                [{'role': self.employee_role_id.id,
                  'partner_id': self.employee_id.user_id.partner_id.id}]
            ))
        for sign_template_id in sign_templates_both_ids:
            second_role = set(sign_template_id.sign_item_ids.mapped('responsible_id').ids)
            second_role.remove(self.employee_role_id.id)
            second_role = second_role.pop()
            sign_values.append((
                sign_template_id,
                [{'role': self.employee_role_id.id,
                  'partner_id': self.employee_id.user_id.partner_id.id},
                 {'role': second_role,
                  'partner_id': self.responsible_id.partner_id.id}]
            ))

        res_ids = []
        for sign_request_values in sign_values:
            res = sign_request.initialize_new(
                template_id=sign_request_values[0].id,
                signers=sign_request_values[1],
                followers=self.follower_ids.ids + [self.responsible_id.partner_id.id],
                reference=_('Signature Request - %s', self.contract_id.name),
                subject=self.subject,
                message=self.message
            )
            res_ids.append(res['id'])

        sign_requests = self.env['sign.request'].browse(res_ids)
        if not self.check_access_rights('write', raise_exception=False):
            sign_requests = sign_requests.sudo()

        for sign_request in sign_requests:
            sign_request.toggle_favorited()
        sign_requests.action_sent()
        sign_requests.write({'state': 'sent'})
        sign_requests.request_item_ids.write({'state': 'sent'})

        self.contract_id.sign_request_ids += sign_requests

        if self.responsible_id and sign_templates_both_ids:
            signatories_text = _('%s and %s are the signatories.') % (self.employee_id.display_name, self.responsible_id.display_name)
        else:
            signatories_text = _('Only %s has to sign.') % self.employee_id.display_name
        self.contract_id.message_post(body=_('%s requested a new signature on the following documents:<br/><ul>%s</ul>%s') %
            (self.env.user.display_name, '\n'.join('<li>%s</li>' % name for name in self.sign_template_ids.mapped('name')),
            signatories_text))

        if len(sign_requests) == 1 and self.env.user.id == self.responsible_id.id:
            return sign_requests.go_to_document()
