# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    payslip_state = fields.Selection([
        ('normal', 'To compute in next payslip'),
        ('done', 'Computed in current payslip'),
        ('blocked', 'To defer to next payslip')], string='Payslip State',
        copy=False, default='normal', required=True)

    def action_validate(self):
        # Get employees payslips
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('state', 'in', ['done', 'paid', 'verify']),
        ]).filtered(lambda p: p.is_regular)
        done_payslips = all_payslips.filtered(lambda p: p.state in ['done', 'paid'])
        waiting_payslips = all_payslips - done_payslips
        # Mark Leaves to Defer
        for leave in self:
            if any(
                payslip.employee_id == leave.employee_id \
                and (payslip.date_from <= leave.date_to.date() \
                and payslip.date_to >= leave.date_from.date()) for payslip in done_payslips) \
                    and not any(payslip.employee_id == leave.employee_id \
                and (payslip.date_from <= leave.date_to.date() \
                and payslip.date_to >= leave.date_from.date()) for payslip in waiting_payslips):
                leave.payslip_state = 'blocked'
        res = super().action_validate()
        self._recompute_payslips()
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self._recompute_payslips()
        return res

    def _recompute_payslips(self):
        # Recompute draft/waiting payslips
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('state', 'in', ['draft', 'verify']),
        ]).filtered(lambda p: p.is_regular)
        draft_payslips = self.env['hr.payslip']
        waiting_payslips = self.env['hr.payslip']
        for leave in self:
            for payslip in all_payslips:
                if payslip.employee_id == leave.employee_id and (payslip.date_from <= leave.date_to.date() and payslip.date_to >= leave.date_from.date()):
                    if payslip.state == 'draft':
                        draft_payslips |= payslip
                    elif payslip.state == 'verify':
                        waiting_payslips |= payslip
        if draft_payslips:
            draft_payslips._compute_worked_days_line_ids()
        if waiting_payslips:
            waiting_payslips.action_refresh_from_work_entries()


    def _cancel_work_entry_conflict(self):
        leaves_to_defer = self.filtered(lambda l: l.payslip_state == 'blocked')
        for leave in leaves_to_defer:
            leave.activity_schedule(
                'hr_payroll_holidays.mail_activity_data_hr_leave_to_defer',
                summary=_('Validated Time Off to Defer'),
                note=_('Please create manually the work entry for <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a>') % (
                    leave.employee_id._name, leave.employee_id.id, leave.employee_id.display_name),
                user_id=leave.employee_id.company_id.deferred_time_off_manager.id or self.env.ref('base.user_admin').id)
        return super(HrLeave, self - leaves_to_defer)._cancel_work_entry_conflict()

    def activity_feedback(self, act_type_xmlids, user_id=None, feedback=None):
        if 'hr_payroll_holidays.mail_activity_data_hr_leave_to_defer' in act_type_xmlids:
            self.write({'payslip_state': 'done'})
        return super().activity_feedback(act_type_xmlids, user_id=user_id, feedback=feedback)
