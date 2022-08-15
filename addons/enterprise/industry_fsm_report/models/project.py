# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Project(models.Model):
    _inherit = "project.project"

    allow_worksheets = fields.Boolean(
        "Worksheets", compute='_compute_allow_worksheets', store=True, readonly=False,
        help="Enables customizable worksheets on tasks.")
    worksheet_template_id = fields.Many2one(
        'worksheet.template', compute="_compute_worksheet_template_id", store=True, readonly=False,
        string="Default Worksheet",
        help="Choose a default worksheet template for this project (you can change it individually on each task).",
        domain="[('res_model', '=', 'project.task'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")

    @api.depends('is_fsm')
    def _compute_allow_worksheets(self):
        for project in self:
            if not project._origin:
                project.allow_worksheets = project.is_fsm

    @api.depends('allow_worksheets')
    def _compute_worksheet_template_id(self):
        default_worksheet = self.env.ref('industry_fsm_report.fsm_worksheet_template', False)
        for project in self:
            if not project.worksheet_template_id:
                if project.allow_worksheets and default_worksheet:
                    project.worksheet_template_id = default_worksheet.id
                else:
                    project.worksheet_template_id = False


class Task(models.Model):
    _inherit = "project.task"

    allow_worksheets = fields.Boolean(related='project_id.allow_worksheets')
    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        compute='_compute_worksheet_template_id', store=True, readonly=False,
        domain="[('res_model', '=', 'project.task'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")
    worksheet_count = fields.Integer(compute='_compute_worksheet_count')
    fsm_is_sent = fields.Boolean('Is Worksheet sent', readonly=True)
    worksheet_signature = fields.Binary('Signature', help='Signature received through the portal.', copy=False, attachment=True)
    worksheet_signed_by = fields.Char('Signed By', help='Name of the person that signed the task.', copy=False)
    worksheet_color = fields.Integer(related='worksheet_template_id.color')
    display_sign_report_primary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_sign_report_secondary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_send_report_primary = fields.Boolean(compute='_compute_display_send_report_buttons')
    display_send_report_secondary = fields.Boolean(compute='_compute_display_send_report_buttons')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {
            'allow_worksheets',
            'worksheet_count',
            'worksheet_signature',  # [XBO] TODO: remove me in master
            'worksheet_template_id',
        }

    @api.depends('allow_worksheets', 'worksheet_count')
    def _compute_display_conditions_count(self):
        super(Task, self)._compute_display_conditions_count()
        for task in self:
            enabled = task.display_enabled_conditions_count
            satisfied = task.display_satisfied_conditions_count
            enabled += 1 if task.allow_worksheets else 0
            satisfied += 1 if task.allow_worksheets and task.worksheet_count else 0
            task.update({
                'display_enabled_conditions_count': enabled,
                'display_satisfied_conditions_count': satisfied
            })

    @api.depends(
        'allow_worksheets', 'timer_start', 'worksheet_signature', 'worksheet_template_id',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count')
    def _compute_display_sign_report_buttons(self):
        for task in self:
            sign_p, sign_s = True, True
            if not task.allow_worksheets or task.timer_start or \
                    task.worksheet_signature or not task.worksheet_template_id or \
                    not task.display_satisfied_conditions_count:
                sign_p, sign_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    sign_s = False
                else:
                    sign_p = False
            task.update({
                'display_sign_report_primary': sign_p,
                'display_sign_report_secondary': sign_s,
            })

    @api.depends(
        'allow_worksheets', 'timer_start', 'worksheet_template_id',
        'display_satisfied_conditions_count', 'display_satisfied_conditions_count',
        'fsm_is_sent')
    def _compute_display_send_report_buttons(self):
        for task in self:
            send_p, send_s = True, True
            if not task.allow_worksheets or task.timer_start or \
                    not task.worksheet_template_id or \
                    not task.display_satisfied_conditions_count or task.fsm_is_sent:
                send_p, send_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    send_s = False
                else:
                    send_p = False
            task.update({
                'display_send_report_primary': send_p,
                'display_send_report_secondary': send_s,
            })

    @api.depends('project_id')
    def _compute_worksheet_template_id(self):
        # Change worksheet when the project changes, not project.allow_worksheet (YTI To confirm)
        for task in self:
            if task.project_id.allow_worksheets:
                task.worksheet_template_id = task.project_id.worksheet_template_id.id
            else:
                task.worksheet_template_id = False

    @api.depends('worksheet_template_id')
    def _compute_worksheet_count(self):
        is_portal_user = self.env.user.share
        for record in self:
            worksheet_count = 0
            if record.worksheet_template_id:
                Worksheet = self.env[record.worksheet_template_id.sudo().model_id.model]
                if is_portal_user:
                    Worksheet = Worksheet.sudo()
                worksheet_count = Worksheet.search_count([('x_project_task_id', '=', record.id)])
            record.worksheet_count = worksheet_count

    def has_to_be_signed(self):
        return self.allow_worksheets and not self.worksheet_signature

    def action_fsm_worksheet(self):
        action = self.worksheet_template_id.action_id.sudo().read()[0]
        worksheet = self.env[self.worksheet_template_id.sudo().model_id.model].search([('x_project_task_id', '=', self.id)])
        context = literal_eval(action.get('context', '{}'))
        action.update({
            'res_id': worksheet.id if worksheet else False,
            'views': [(False, 'form')],
            'context': {
                **context,
                'edit': True,
                'default_x_project_task_id': self.id,
                'form_view_initial_mode': 'edit',
            },
        })
        return action

    def action_preview_worksheet(self):
        self.ensure_one()
        if not self.worksheet_template_id:
            raise UserError(_("To send the report, you need to select a worksheet template."))

        source = 'fsm' if self.env.context.get('fsm_mode', False) else 'project'
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(suffix='/worksheet/%s' % source)
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Worksheet %s - %s' % (self.name, self.partner_id.name)

    def _is_fsm_report_available(self):
        self.ensure_one()
        return self.worksheet_count or self.timesheet_ids

    def action_send_report(self):
        tasks_with_report = self.filtered(lambda task: task._is_fsm_report_available())
        if not tasks_with_report:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("There are no reports to send."),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        template_id = self.env.ref('industry_fsm_report.mail_template_data_send_report').id
        return {
            'name': _("Send report"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass_mail' if len(tasks_with_report.ids) > 1 else 'comment',
                'default_model': 'project.task',
                'default_res_id': tasks_with_report.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'fsm_mark_as_sent': True,
                'active_ids': tasks_with_report.ids,
            },
        }

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _message_post_after_hook(self, message, *args, **kwargs):
        if self.env.context.get('fsm_mark_as_sent') and not self.fsm_is_sent:
            self.write({'fsm_is_sent': True})

class ProjectTaskRecurrence(models.Model):
    _inherit = 'project.task.recurrence'

    @api.model
    def _get_recurring_fields(self):
        return ['worksheet_template_id'] + super(ProjectTaskRecurrence, self)._get_recurring_fields()
