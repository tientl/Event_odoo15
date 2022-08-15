# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models, _
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips, ResultRules
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils, convert_file, html2plaintext
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _order = 'date_to desc'

    struct_id = fields.Many2one(
        'hr.payroll.structure', string='Structure',
        compute='_compute_struct_id', store=True, readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]},
        help='Defines the rules that have to be applied to this payslip, according '
             'to the contract chosen. If the contract is empty, this field isn\'t '
             'mandatory anymore and all the valid rules of the structures '
             'of the employee\'s contracts will be applied.')
    struct_type_id = fields.Many2one('hr.payroll.structure.type', related='struct_id.type_id')
    wage_type = fields.Selection(related='struct_type_id.wage_type')
    name = fields.Char(
        string='Payslip Name', required=True,
        compute='_compute_name', store=True, readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})
    number = fields.Char(
        string='Reference', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, readonly=True,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), '|', ('active', '=', True), ('active', '=', False)]")
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id', readonly=True, store=True)
    date_from = fields.Date(
        string='From', readonly=True, required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)), states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    date_to = fields.Date(
        string='To', readonly=True, required=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()),
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected')],
        string='Status', index=True, readonly=True, copy=False,
        default='draft', tracking=True,
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', string='Payslip Lines',
        compute='_compute_line_ids', store=True, readonly=True, copy=True,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    company_id = fields.Many2one(
        'res.company', string='Company', copy=False, required=True,
        compute='_compute_company_id', store=True, readonly=False,
        default=lambda self: self.env.company,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    country_id = fields.Many2one(
        'res.country', string='Country',
        related='company_id.country_id', readonly=True
    )
    country_code = fields.Char(related='country_id.code', readonly=True)
    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked_days', 'payslip_id', string='Payslip Worked Days', copy=True,
        compute='_compute_worked_days_line_ids', store=True, readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})
    input_line_ids = fields.One2many(
        'hr.payslip.input', 'payslip_id', string='Payslip Inputs',
        compute='_compute_input_line_ids', store=True,
        readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})
    paid = fields.Boolean(
        string='Made Payment Order ? ', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    note = fields.Text(string='Internal Note', readonly=True, states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    contract_id = fields.Many2one(
        'hr.contract', string='Contract', domain="[('company_id', '=', company_id)]",
        compute='_compute_contract_id', store=True, readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})
    credit_note = fields.Boolean(
        string='Credit Note', readonly=True,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]},
        help="Indicates this payslip has a refund of another")
    has_refund_slip = fields.Boolean(compute='_compute_has_refund_slip')
    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Batch Name', readonly=True,
        copy=False, states={'draft': [('readonly', False)], 'verify': [('readonly', False)]}, ondelete='cascade',
        domain="[('company_id', '=', company_id)]")
    sum_worked_hours = fields.Float(compute='_compute_worked_hours', store=True, help='Total hours of attendance and time off (paid or not)')
    # YTI TODO: normal_wage to be removed
    normal_wage = fields.Integer(compute='_compute_normal_wage', store=True)
    compute_date = fields.Date('Computed On')
    basic_wage = fields.Monetary(compute='_compute_basic_net')
    net_wage = fields.Monetary(compute='_compute_basic_net')
    currency_id = fields.Many2one(related='contract_id.currency_id')
    warning_message = fields.Char(compute='_compute_warning_message', store=True, readonly=False)
    is_regular = fields.Boolean(compute='_compute_is_regular')
    has_negative_net_to_report = fields.Boolean()
    negative_net_to_report_display = fields.Boolean(compute='_compute_negative_net_to_report_display')
    negative_net_to_report_message = fields.Char(compute='_compute_negative_net_to_report_display')
    negative_net_to_report_amount = fields.Float(compute='_compute_negative_net_to_report_display')
    is_superuser = fields.Boolean(compute="_compute_is_superuser")
    edited = fields.Boolean()
    queued_for_pdf = fields.Boolean(default=False)

    salary_attachment_ids = fields.Many2many(
        'hr.salary.attachment',
        relation='hr_payslip_hr_salary_attachment_rel',
        string='Salary Attachments',
        compute='_compute_salary_attachment_ids',
        store=True,
        readonly=False,
    )
    salary_attachment_count = fields.Integer('Salary Attachment count', compute='_compute_salary_attachment_count')

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'struct_id')
    def _compute_input_line_ids(self):
        attachment_types = self._get_attachment_types()
        attachment_type_ids = [f.id for f in attachment_types.values()]
        for slip in self:
            if not slip.employee_id or not slip.employee_id.salary_attachment_ids or not slip.struct_id:
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id.id in attachment_type_ids)
                slip.update({'input_line_ids': [Command.unlink(line.id) for line in lines_to_remove]})
            if slip.employee_id.salary_attachment_ids:
                lines_to_keep = slip.input_line_ids.filtered(lambda x: x.input_type_id.id not in attachment_type_ids)
                input_line_vals = [Command.clear()] + [Command.link(line.id) for line in lines_to_keep]

                valid_attachments = slip.employee_id.salary_attachment_ids.filtered(
                    lambda a: a.state == 'open' and a.date_start <= slip.date_to
                )

                # Only take deduction types present in structure
                deduction_types = list(set(valid_attachments.mapped('deduction_type')))
                struct_deduction_lines = list(set(slip.struct_id.rule_ids.mapped('code')))
                included_deduction_types = [f for f in deduction_types if attachment_types[f].code in struct_deduction_lines]
                for deduction_type in included_deduction_types:
                    if not slip.struct_id.rule_ids.filtered(lambda r: r.active and r.code == attachment_types[deduction_type].code):
                        continue
                    attachments = valid_attachments.filtered(lambda a: a.deduction_type == deduction_type)
                    amount = sum(attachments.mapped('active_amount'))
                    name = ', '.join(attachments.mapped('description'))
                    input_type_id = attachment_types[deduction_type].id
                    input_line_vals.append(Command.create({
                        'name': name,
                        'amount': amount,
                        'input_type_id': input_type_id,
                    }))
                slip.update({'input_line_ids': input_line_vals})

    @api.depends('input_line_ids.input_type_id', 'input_line_ids')
    def _compute_salary_attachment_ids(self):
        attachment_types = self._get_attachment_types()
        for slip in self:
            if not slip.input_line_ids and not slip.salary_attachment_ids:
                continue
            attachments = self.env['hr.salary.attachment']
            if slip.employee_id and slip.input_line_ids:
                input_line_type_ids = slip.input_line_ids.mapped('input_type_id.id')
                deduction_types = [f for f in attachment_types if attachment_types[f].id in input_line_type_ids]
                attachments = slip.employee_id.salary_attachment_ids.filtered(
                    lambda a: (
                        a.state == 'open'
                        and a.deduction_type in deduction_types
                        and a.date_start <= slip.date_to
                    )
                )
            slip.salary_attachment_ids = attachments

    @api.depends('salary_attachment_ids')
    def _compute_salary_attachment_count(self):
        for slip in self:
            slip.salary_attachment_count = len(slip.salary_attachment_ids)


    @api.depends('employee_id', 'state')
    def _compute_negative_net_to_report_display(self):
        activity_type = self.env.ref('hr_payroll.mail_activity_data_hr_payslip_negative_net')
        for payslip in self:
            if payslip.state in ['draft', 'verify']:
                payslips_to_report = self.env['hr.payslip'].search([
                    ('has_negative_net_to_report', '=', True),
                    ('employee_id', '=', payslip.employee_id.id),
                    ('credit_note', '=', False),
                ])
                payslip.negative_net_to_report_display = payslips_to_report
                payslip.negative_net_to_report_amount = payslips_to_report._get_line_values(['NET'], compute_sum=True)['NET']['sum']['total']
                payslip.negative_net_to_report_message = _(
                    'Note: There are previous payslips with a negative amount for a total of %s to report.',
                    round(payslip.negative_net_to_report_amount, 2))
                if payslips_to_report and payslip.state == 'verify' and payslip.contract_id and not payslip.activity_ids.filtered(lambda a: a.activity_type_id == activity_type):
                    payslip.activity_schedule(
                        'hr_payroll.mail_activity_data_hr_payslip_negative_net',
                        summary=_('Previous Negative Payslip to Report'),
                        note=_('At least one previous negative net could be reported on this payslip for <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a>') % (
                            payslip.employee_id._name, payslip.employee_id.id, payslip.employee_id.display_name),
                        user_id=payslip.contract_id.hr_responsible_id.id or self.env.ref('base.user_admin').id)
            else:
                payslip.negative_net_to_report_display = False
                payslip.negative_net_to_report_amount = False
                payslip.negative_net_to_report_message = False

    def _get_negative_net_input_type(self):
        self.ensure_one()
        return self.env.ref('hr_payroll.input_deduction')

    def action_report_negative_amount(self):
        self.ensure_one()
        deduction_input_type = self._get_negative_net_input_type()
        deduction_input_line = self.input_line_ids.filtered(lambda l: l.input_type_id == deduction_input_type)
        if deduction_input_line:
            deduction_input_line.amount += abs(self.negative_net_to_report_amount)
        else:
            self.write({'input_line_ids': [(0, 0, {
                'input_type_id': deduction_input_type.id,
                'amount': abs(self.negative_net_to_report_amount),
            })]})
            self.compute_sheet()
        self.env['hr.payslip'].search([
            ('has_negative_net_to_report', '=', True),
            ('employee_id', '=', self.employee_id.id),
            ('credit_note', '=', False),
        ]).write({'has_negative_net_to_report': False})
        self.activity_feedback(['hr_payroll.mail_activity_data_hr_payslip_negative_net'])

    def _compute_is_regular(self):
        for payslip in self:
            payslip.is_regular = payslip.struct_id.type_id.default_struct_id == payslip.struct_id

    def _is_invalid(self):
        self.ensure_one()
        if self.state not in ['done', 'paid']:
            return _("This payslip is not validated. This is not a legal document.")
        return False

    @api.depends('worked_days_line_ids', 'input_line_ids')
    def _compute_line_ids(self):
        if not self.env.context.get("payslip_no_recompute"):
            return
        for payslip in self.filtered(lambda p: p.line_ids and p.state in ['draft', 'verify']):
            payslip.line_ids = [(5, 0, 0)] + [(0, 0, line_vals) for line_vals in payslip._get_payslip_lines()]

    def _compute_basic_net(self):
        line_values = (self._origin)._get_line_values(['BASIC', 'NET'])
        for payslip in self:
            payslip.basic_wage = line_values['BASIC'][payslip._origin.id]['total']
            payslip.net_wage = line_values['NET'][payslip._origin.id]['total']

    @api.depends('worked_days_line_ids.number_of_hours', 'worked_days_line_ids.is_paid')
    def _compute_worked_hours(self):
        for payslip in self:
            payslip.sum_worked_hours = sum([line.number_of_hours for line in payslip.worked_days_line_ids])

    @api.depends('contract_id')
    def _compute_normal_wage(self):
        with_contract = self.filtered('contract_id')
        (self - with_contract).normal_wage = 0
        for payslip in with_contract:
            payslip.normal_wage = payslip._get_contract_wage()

    def _compute_is_superuser(self):
        self.update({'is_superuser': self.env.user._is_superuser() and self.user_has_groups("base.group_no_one")})

    def _compute_has_refund_slip(self):
        #This field is only used to know whether we need a confirm on refund or not
        #It doesn't have to work in batch and we try not to search if not necessary
        for payslip in self:
            if not payslip.credit_note and payslip.state in ('done', 'paid') and self.search_count([
                ('employee_id', '=', payslip.employee_id.id),
                ('date_from', '=', payslip.date_from),
                ('date_to', '=', payslip.date_to),
                ('contract_id', '=', payslip.contract_id.id),
                ('struct_id', '=', payslip.struct_id.id),
                ('credit_note', '=', True),
                ('state', '!=', 'cancel'),
                ]):
                payslip.has_refund_slip = True
            else:
                payslip.has_refund_slip = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(payslip.date_from > payslip.date_to for payslip in self):
            raise ValidationError(_("Payslip 'Date From' must be earlier 'Date To'."))

    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals and vals['state'] == 'paid':
            # Register payment in Salary Attachments
            # NOTE: Since we combine multiple attachments on one input line, it's not possible to compute
            #  how much per attachment needs to be taken record_payment will consume monthly payments (child_support) before other attachments
            attachment_types = self._get_attachment_types()
            for slip in self.filtered(lambda r: r.salary_attachment_ids):
                for deduction_type, input_type_id in attachment_types.items():
                    attachments = slip.salary_attachment_ids.filtered(lambda r: r.deduction_type == deduction_type)
                    input_lines = slip.input_line_ids.filtered(lambda r: r.input_type_id.id == input_type_id.id)
                    # Use the amount from the computed value in the payslip lines not the input
                    salary_lines = slip.line_ids.filtered(lambda r: r.code in input_lines.mapped('code'))
                    if not attachments or not salary_lines:
                        continue
                    attachments.record_payment(abs(salary_lines.total))
        return res

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def _get_pdf_reports(self):
        classic_report = self.env.ref('hr_payroll.action_report_payslip')
        result = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                result[classic_report] |= payslip
            else:
                result[payslip.struct_id.report_id] |= payslip
        return result

    def _generate_pdf(self):
        mapped_reports = self._get_pdf_reports()
        attachments_vals_list = []
        generic_name = _("Payslip")
        template = self.env.ref('hr_payroll.mail_template_new_payslip', raise_if_not_found=False)
        for report, payslips in mapped_reports.items():
            for payslip in payslips:
                pdf_content, dummy = report.sudo()._render_qweb_pdf(payslip.id)
                if report.print_report_name:
                    pdf_name = safe_eval(report.print_report_name, {'object': payslip})
                else:
                    pdf_name = generic_name
                attachments_vals_list.append({
                    'name': pdf_name,
                    'type': 'binary',
                    'raw': pdf_content,
                    'res_model': payslip._name,
                    'res_id': payslip.id
                })
                # Send email to employees
                if template:
                    template.send_mail(payslip.id, notif_layout='mail.mail_notification_light')
        self.env['ir.attachment'].sudo().create(attachments_vals_list)

    def action_payslip_done(self):
        invalid_payslips = self.filtered(lambda p: p.contract_id and (p.contract_id.date_start > p.date_to or (p.contract_id.date_end and p.contract_id.date_end < p.date_from)))
        if invalid_payslips:
            raise ValidationError(_('The following employees have a contract outside of the payslip period:\n%s', '\n'.join(invalid_payslips.mapped('employee_id.name'))))
        if any(slip.contract_id.state == 'cancel' for slip in self):
            raise ValidationError(_('You cannot valide a payslip on which the contract is cancelled'))
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled payslip."))
        self.write({'state' : 'done'})

        line_values = self._get_line_values(['NET'])

        self.filtered(lambda p: not p.credit_note and line_values['NET'][p.id]['total'] < 0).write({'has_negative_net_to_report': True})
        self.mapped('payslip_run_id').action_close()
        # Validate work entries for regular payslips (exclude end of year bonus, ...)
        regular_payslips = self.filtered(lambda p: p.struct_id.type_id.default_struct_id == p.struct_id)
        work_entries = self.env['hr.work.entry']
        for regular_payslip in regular_payslips:
            work_entries |= self.env['hr.work.entry'].search([
                ('date_start', '<=', regular_payslip.date_to),
                ('date_stop', '>=', regular_payslip.date_from),
                ('employee_id', '=', regular_payslip.employee_id.id),
            ])
        if work_entries:
            work_entries.action_validate()

        if self.env.context.get('payslip_generate_pdf'):
            if self.env.context.get('payslip_generate_pdf_direct'):
                self._generate_pdf()
            else:
                self.write({'queued_for_pdf': True})
                payslip_cron = self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs', raise_if_not_found=False)
                if payslip_cron:
                    payslip_cron._trigger()

    def action_payslip_cancel(self):
        if not self.env.user._is_system() and self.filtered(lambda slip: slip.state == 'done'):
            raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        self.mapped('payslip_run_id').action_close()

    def action_payslip_paid(self):
        if any(slip.state != 'done' for slip in self):
            raise UserError(_('Cannot mark payslip as paid if not confirmed.'))
        self.write({'state': 'paid'})

    def action_open_work_entries(self):
        self.ensure_one()
        return self.employee_id.action_open_work_entries()

    def action_open_salary_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Salary Attachments'),
            'res_model': 'hr.salary.attachment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.salary_attachment_ids.ids)],
        }

    def refund_sheet(self):
        copied_payslips = self.env['hr.payslip']
        for payslip in self:
            copied_payslip = payslip.copy({
                'credit_note': True,
                'name': _('Refund: %(payslip)s', payslip=payslip.name),
                'edited': True,
                'state': 'verify',
            })
            for wd in copied_payslip.worked_days_line_ids:
                wd.number_of_hours = -wd.number_of_hours
                wd.number_of_days = -wd.number_of_days
                wd.amount = -wd.amount
            for line in copied_payslip.line_ids:
                line.amount = -line.amount
            copied_payslips |= copied_payslip
        formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', copied_payslips.ids)],
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(payslip.state not in ('draft', 'cancel') for payslip in self):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))

    def compute_sheet(self):
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'])
        # delete old payslip lines
        payslips.line_ids.unlink()
        for payslip in payslips:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            lines = [(0, 0, line) for line in payslip._get_payslip_lines()]
            payslip.write({'line_ids': lines, 'number': number, 'state': 'verify', 'compute_date': fields.Date.today()})
        return True

    def action_refresh_from_work_entries(self):
        # Refresh the whole payslip in case the HR has modified some work entries
        # after the payslip generation
        if any(p.state not in ['draft', 'verify'] for p in self):
            raise UserError(_('The payslips should be in Draft or Waiting state.'))
        self.mapped('worked_days_line_ids').unlink()
        self.mapped('line_ids').unlink()
        self._compute_worked_days_line_ids()
        self.compute_sheet()

    def _round_days(self, work_entry_type, days):
        if work_entry_type.round_days != 'NO':
            precision_rounding = 0.5 if work_entry_type.round_days == "HALF" else 1
            day_rounded = float_round(days, precision_rounding=precision_rounding, rounding_method=work_entry_type.round_days_type)
            return day_rounded
        return days

    @api.model
    def _get_attachment_types(self):
        return {
            'attachment': self.env.ref('hr_payroll.input_attachment_salary'),
            'assignment': self.env.ref('hr_payroll.input_assignment_salary'),
            'child_support': self.env.ref('hr_payroll.input_child_support'),
        }

    def _get_worked_day_lines_hours_per_day(self):
        self.ensure_one()
        return self.contract_id.resource_calendar_id.hours_per_day

    def _get_out_of_contract_calendar(self):
        self.ensure_one()
        return self.contract_id.resource_calendar_id

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        hours_per_day = self._get_worked_day_lines_hours_per_day()
        work_hours = self.contract_id._get_work_hours(self.date_from, self.date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_days_rounding = 0
        for work_entry_type_id, hours in work_hours_ordered:
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
            }
            res.append(attendance_line)
        return res

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        if contract.resource_calendar_id:
            res = self._get_worked_day_lines_values(domain=domain)
            if not check_out_of_contract:
                return res

            # If the contract doesn't cover the whole month, create
            # worked_days lines to adapt the wage accordingly
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']

            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                res.append({
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': out_days,
                    'number_of_hours': out_hours,
                })
        return res

    def _get_base_local_dict(self):
        return {
            'float_round': float_round,
            'float_compare': float_compare,
        }

    def _get_localdict(self):
        self.ensure_one()
        worked_days_dict = {line.code: line for line in self.worked_days_line_ids if line.code}
        inputs_dict = {line.code: line for line in self.input_line_ids if line.code}

        employee = self.employee_id
        contract = self.contract_id

        localdict = {
            **self._get_base_local_dict(),
            **{
                'categories': BrowsableObject(employee.id, {}, self.env),
                'rules': BrowsableObject(employee.id, {}, self.env),
                'payslip': Payslips(employee.id, self, self.env),
                'worked_days': WorkedDays(employee.id, worked_days_dict, self.env),
                'inputs': InputLine(employee.id, inputs_dict, self.env),
                'employee': employee,
                'contract': contract,
                'result_rules': ResultRules(employee.id, {}, self.env)
            }
        }
        return localdict

    def _get_payslip_lines(self):
        self.ensure_one()

        localdict = self.env.context.get('force_payslip_localdict', None)
        if localdict is None:
            localdict = self._get_localdict()

        rules_dict = localdict['rules'].dict
        result_rules_dict = localdict['result_rules'].dict

        blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

        result = {}

        for rule in sorted(self.struct_id.rule_ids, key=lambda x: x.sequence):
            if rule.id in blacklisted_rule_ids:
                continue
            localdict.update({
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100,
                'result_name': False
            })
            if rule._satisfy_condition(localdict):
                amount, qty, rate = rule._compute_rule(localdict)
                #check if there is already a rule computed with that code
                previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                #set/overwrite the amount computed for this rule in the localdict
                tot_rule = amount * qty * rate / 100.0
                localdict[rule.code] = tot_rule
                result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty}
                rules_dict[rule.code] = rule
                # sum the amount for its salary category
                localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
                # Retrieve the line name in the employee's lang
                employee_lang = self.employee_id.sudo().address_home_id.lang
                # This actually has an impact, don't remove this line
                context = {'lang': employee_lang}
                if localdict['result_name']:
                    rule_name = localdict['result_name']
                elif rule.code in ['BASIC', 'GROSS', 'NET', 'DEDUCTION', 'REIMBURSEMENT']:  # Generated by default_get (no xmlid)
                    if rule.code == 'BASIC':  # Note: Crappy way to code this, but _(foo) is forbidden. Make a method in master to be overridden, using the structure code
                        if rule.name == "Double Holiday Pay":
                            rule_name = _("Double Holiday Pay")
                        if rule.struct_id.name == "CP200: Employees 13th Month":
                            rule_name = _("Prorated end-of-year bonus")
                        else:
                            rule_name = _('Basic Salary')
                    elif rule.code == "GROSS":
                        rule_name = _('Gross')
                    elif rule.code == "DEDUCTION":
                        rule_name = _('Deduction')
                    elif rule.code == "REIMBURSEMENT":
                        rule_name = _('Reimbursement')
                    elif rule.code == 'NET':
                        rule_name = _('Net Salary')
                else:
                    rule_name = rule.with_context(lang=employee_lang).name
                # create/overwrite the rule in the temporary results
                result[rule.code] = {
                    'sequence': rule.sequence,
                    'code': rule.code,
                    'name': rule_name,
                    'note': html2plaintext(rule.note),
                    'salary_rule_id': rule.id,
                    'contract_id': localdict['contract'].id,
                    'employee_id': localdict['employee'].id,
                    'amount': amount,
                    'quantity': qty,
                    'rate': rate,
                    'slip_id': self.id,
                }
        return result.values()

    @api.depends('employee_id')
    def _compute_company_id(self):
        for slip in self.filtered(lambda p: p.employee_id):
            slip.company_id = slip.employee_id.company_id

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_contract_id(self):
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                slip.contract_id = False
                continue
            # Add a default contract if not already defined or invalid
            if slip.contract_id and slip.employee_id == slip.contract_id.employee_id:
                continue
            contracts = slip.employee_id._get_contracts(slip.date_from, slip.date_to)
            slip.contract_id = contracts[0] if contracts else False

    @api.depends('contract_id')
    def _compute_struct_id(self):
        for slip in self.filtered(lambda p: not p.struct_id):
            slip.struct_id = slip.contract_id.structure_type_id.default_struct_id

    @api.depends('employee_id', 'struct_id', 'date_from')
    def _compute_name(self):
        for slip in self.filtered(lambda p: p.employee_id and p.date_from):
            lang = slip.employee_id.sudo().address_home_id.lang or self.env.user.lang
            context = {'lang': lang}
            payslip_name = slip.struct_id.payslip_name or _('Salary Slip')
            del context

            slip.name = '%(payslip_name)s - %(employee_name)s - %(dates)s' % {
                'payslip_name': payslip_name,
                'employee_name': slip.employee_id.name,
                'dates': format_date(self.env, slip.date_from, date_format="MMMM y", lang_code=lang)
            }

    @api.depends('date_to')
    def _compute_warning_message(self):
        for slip in self.filtered(lambda p: p.date_to):
            if slip.date_to > date_utils.end_of(fields.Date.today(), 'month'):
                slip.warning_message = _(
                    "This payslip can be erroneous! Work entries may not be generated for the period from %(start)s to %(end)s.",
                    start=date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1),
                    end=slip.date_to,
                )
            else:
                slip.warning_message = False

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_worked_days_line_ids(self):
        if self.env.context.get('salary_simulation'):
            return
        valid_slips = self.filtered(lambda p: p.employee_id and p.date_from and p.date_to and p.contract_id and p.struct_id)
        # Make sure to reset invalid payslip's worked days line
        invalid_slips = self - valid_slips
        invalid_slips.worked_days_line_ids = [(5, False, False)]
        # Ensure work entries are generated for all contracts
        generate_from = min(p.date_from for p in self)
        current_month_end = date_utils.end_of(fields.Date.today(), 'month')
        generate_to = max(min(fields.Date.to_date(p.date_to), current_month_end) for p in self)
        self.mapped('contract_id')._generate_work_entries(generate_from, generate_to)

        for slip in valid_slips:
            slip.write({'worked_days_line_ids': slip._get_new_worked_days_lines()})

    def _get_new_worked_days_lines(self):
        if self.struct_id.use_worked_day_lines:
            return [(5, 0, 0)] + [(0, 0, vals) for vals in self._get_worked_day_lines()]
        return [(5, False, False)]

    def _get_salary_line_total(self, code):
        _logger.warning('The method _get_salary_line_total is deprecated in favor of _get_line_values')
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum([line.total for line in lines])

    def _get_salary_line_quantity(self, code):
        _logger.warning('The method _get_salary_line_quantity is deprecated in favor of _get_line_values')
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum([line.quantity for line in lines])

    def _get_line_values(self, code_list, vals_list=None, compute_sum=False):
        if vals_list is None:
            vals_list = ['total']
        valid_values = {'quantity', 'amount', 'total'}
        if set(vals_list) - valid_values:
            raise UserError(_('The following values are not valid:\n%s', '\n'.join(list(set(vals_list) - valid_values))))
        result = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(vals_list, 0)))
        if not self:
            return result
        self.flush()
        selected_fields = ','.join('SUM(%s) AS %s' % (vals, vals) for vals in vals_list)
        self.env.cr.execute("""
            SELECT
                p.id,
                pl.code,
                %s
            FROM hr_payslip_line pl
            JOIN hr_payslip p
            ON p.id IN %s
            AND pl.slip_id = p.id
            AND pl.code IN %s
            GROUP BY p.id, pl.code
        """ % (selected_fields, '%s', '%s'), (tuple(self.ids), tuple(code_list)))
        # self = hr.payslip(1, 2)
        # request_rows = [
        #     {'id': 1, 'code': 'IP', 'total': 100, 'quantity': 1},
        #     {'id': 1, 'code': 'IP.DED', 'total': 200, 'quantity': 1},
        #     {'id': 2, 'code': 'IP', 'total': -2, 'quantity': 1},
        #     {'id': 2, 'code': 'IP.DED', 'total': -3, 'quantity': 1}
        # ]
        request_rows = self.env.cr.dictfetchall()
        # result = {
        #     'IP': {
        #         'sum': {'quantity': 2, 'total': 300},
        #         1: {'quantity': 1, 'total': 100},
        #         2: {'quantity': 1, 'total': 200},
        #     },
        #     'IP.DED': {
        #         'sum': {'quantity': 2, 'total': -5},
        #         1: {'quantity': 1, 'total': -2},
        #         2: {'quantity': 1, 'total': -3},
        #     },
        # }
        for row in request_rows:
            code = row['code']
            payslip_id = row['id']
            for vals in vals_list:
                if compute_sum:
                    result[code]['sum'][vals] += row[vals]
                result[code][payslip_id][vals] += row[vals]
        return result

    def _get_worked_days_line_amount(self, code):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code == code)
        return sum([wd.amount for wd in wds])

    def _get_worked_days_line_number_of_hours(self, code):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code == code)
        return sum([wd.number_of_hours for wd in wds])

    def _get_worked_days_line_number_of_days(self, code):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code == code)
        return sum([wd.number_of_days for wd in wds])

    def _get_input_line_amount(self, code):
        lines = self.input_line_ids.filtered(lambda line: line.code == code)
        return sum([line.amount for line in lines])

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id, view_type, toolbar, submenu)
        if toolbar and 'print' in res['toolbar']:
            res['toolbar'].pop('print')
        return res

    def action_print_payslip(self):
        return {
            'name': 'Payslip',
            'type': 'ir.actions.act_url',
            'url': '/print/payslips?list_ids=%(list_ids)s' % {'list_ids': ','.join(str(x) for x in self.ids)},
        }

    def action_export_payslip(self):
        self.ensure_one()
        return {
            "name": "Debug Payslip",
            "type": "ir.actions.act_url",
            "url": "/debug/payslip/%s" % self.id,
        }

    def _get_contract_wage(self):
        self.ensure_one()
        return self.contract_id._get_contract_wage()

    def _get_paid_amount(self):
        self.ensure_one()
        if not self.worked_days_line_ids:
            return self._get_contract_wage()
        total_amount = 0
        for line in self.worked_days_line_ids:
            total_amount += line.amount
        return total_amount

    def _get_unpaid_amount(self):
        self.ensure_one()
        return self._get_contract_wage() - self._get_paid_amount()

    def _is_outside_contract_dates(self):
        self.ensure_one()
        payslip = self
        contract = self.contract_id
        return contract.date_start > payslip.date_to or (contract.date_end and contract.date_end < payslip.date_from)

    def _get_data_files_to_update(self):
        # Note: Use lists as modules/files order should be maintained
        return []

    def _update_payroll_data(self):
        data_to_update = self._get_data_files_to_update()
        _logger.info("Update payroll static data")
        idref = {}
        for module_name, files_to_update in data_to_update:
            for file_to_update in files_to_update:
                convert_file(self.env.cr, module_name, file_to_update, idref)

    def action_edit_payslip_lines(self):
        self.ensure_one()
        if not self.user_has_groups('hr_payroll.group_hr_payroll_manager'):
            raise UserError(_('This action is restricted to payroll managers only.'))
        if self.state == 'done':
            raise UserError(_('This action is forbidden on validated payslips.'))
        wizard = self.env['hr.payroll.edit.payslip.lines.wizard'].create({
            'payslip_id': self.id,
            'line_ids': [(0, 0, {
                'sequence': line.sequence,
                'code': line.code,
                'name': line.name,
                'note': line.note,
                'salary_rule_id': line.salary_rule_id.id,
                'contract_id': line.contract_id.id,
                'employee_id': line.employee_id.id,
                'amount': line.amount,
                'quantity': line.quantity,
                'rate': line.rate,
                'slip_id': self.id}) for line in self.line_ids],
            'worked_days_line_ids': [(0, 0, {
                'name': line.name,
                'sequence': line.sequence,
                'code': line.code,
                'work_entry_type_id': line.work_entry_type_id.id,
                'number_of_days': line.number_of_days,
                'number_of_hours': line.number_of_hours,
                'amount': line.amount,
                'slip_id': self.id}) for line in self.worked_days_line_ids]
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Payslip Lines'),
            'res_model': 'hr.payroll.edit.payslip.lines.wizard',
            'view_mode': 'form',
            'target': 'new',
            'binding_model_id': self.env['ir.model.data']._xmlid_to_res_id('hr_payroll.model_hr_payslip'),
            'binding_view_types': 'form',
            'res_id': wizard.id
        }

    @api.model
    def _cron_generate_pdf(self):
        payslips = self.search([
            ('state', 'in', ['done', 'paid']),
            ('queued_for_pdf', '=', True),
        ])
        if not payslips:
            return
        BATCH_SIZE = 50
        payslips_batch = payslips[:BATCH_SIZE]
        payslips_batch._generate_pdf()
        payslips_batch.write({'queued_for_pdf': False})
        # if necessary, retrigger the cron to generate more pdfs
        if len(payslips) > BATCH_SIZE:
            self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()

