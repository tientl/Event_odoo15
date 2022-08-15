# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from collections import defaultdict
from odoo import api, _, fields, models
from odoo.tools import date_utils
from odoo.osv import expression


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    schedule_pay = fields.Selection(related='structure_type_id.default_struct_id.schedule_pay', depends=())
    resource_calendar_id = fields.Many2one(required=True, default=lambda self: self.env.company.resource_calendar_id,
        help="Employee's working schedule.")
    hours_per_week = fields.Float(related='resource_calendar_id.hours_per_week')
    full_time_required_hours = fields.Float(related='resource_calendar_id.full_time_required_hours')
    is_fulltime = fields.Boolean(related='resource_calendar_id.is_fulltime')
    wage_type = fields.Selection(related='structure_type_id.wage_type')
    hourly_wage = fields.Monetary('Hourly Wage', default=0, required=True, tracking=True, help="Employee's hourly gross wage.")
    payslips_count = fields.Integer("# Payslips", compute='_compute_payslips_count', groups="hr_payroll.group_hr_payroll_user")
    calendar_changed = fields.Boolean(help="Whether the previous or next contract has a different schedule or not")

    def _compute_payslips_count(self):
        count_data = self.env['hr.payslip'].read_group(
            [('contract_id', 'in', self.ids)],
            ['contract_id'],
            ['contract_id'])
        mapped_counts = {cd['contract_id'][0]: cd['contract_id_count'] for cd in count_data}
        for contract in self:
            contract.payslips_count = mapped_counts.get(contract.id, 0)

    def _is_same_occupation(self, contract):
        self.ensure_one()
        contract_type = self.contract_type_id
        work_time_rate = self.resource_calendar_id.work_time_rate
        return contract_type == contract.contract_type_id and work_time_rate == contract.resource_calendar_id.work_time_rate

    def _get_occupation_dates(self, include_future_contracts=False):
        # Takes several contracts and returns all the contracts under the same occupation (i.e. the same
        #  work rate + the date_from and date_to)
        # include_futur_contracts will use draft contracts if the start_date is posterior compared to current date
        #  NOTE: this does not take kanban_state in account
        result = []
        done_contracts = self.env['hr.contract']
        date_today = fields.Date.today()

        for contract in self:
            if contract in done_contracts:
                continue
            contracts = contract  # hr.contract(38,)
            date_from = contract.date_start
            date_to = contract.date_end
            history = self.env['hr.contract.history'].search([('employee_id', '=', contract.employee_id.id)], limit=1)
            all_contracts = history.contract_ids.filtered(
                lambda c: (
                    c.active and c != contract and
                    (c.state in ['open', 'close'] or (include_future_contracts and c.state == 'draft' and c.date_start >= date_today))
                )
            ) # hr.contract(29, 37, 38, 39, 41) -> hr.contract(29, 37, 39, 41)
            before_contracts = all_contracts.filtered(lambda c: c.date_start < contract.date_start) # hr.contract(39, 41)
            after_contracts = all_contracts.filtered(lambda c: c.date_start > contract.date_start).sorted(key='date_start') # hr.contract(37, 29)

            for before_contract in before_contracts:
                if contract._is_same_occupation(before_contract):
                    date_from = before_contract.date_start
                    contracts |= before_contract
                else:
                    break

            for after_contract in after_contracts:
                if contract._is_same_occupation(after_contract):
                    date_to = after_contract.date_end
                    contracts |= after_contract
                else:
                    break
            result.append((contracts, date_from, date_to))
            done_contracts |= contracts
        return result

    def _compute_calendar_changed(self):
        date_today = fields.Date.today()
        contract_resets = self.filtered(
            lambda c: (
                not c.date_start or not c.employee_id or not c.resource_calendar_id or not c.active or
                not (c.state in ('open', 'close') or (c.state == 'draft' and c.date_start >= date_today)) # make sure to include futur contracts
            )
        )
        contract_resets.filtered(lambda c: c.calendar_changed).write({'calendar_changed': False})
        self -= contract_resets
        occupation_dates = self._get_occupation_dates(include_future_contracts=True)
        occupation_by_employee = defaultdict(list)
        for row in occupation_dates:
            occupation_by_employee[row[0][0].employee_id.id].append(row)
        contract_changed = self.env['hr.contract']
        for occupations in occupation_by_employee.values():
            if len(occupations) == 1:
                continue
            for i in range(len(occupations) - 1):
                current_row = occupations[i]
                next_row = occupations[i + 1]
                contract_changed |= current_row[0][-1]
                contract_changed |= next_row[0][0]
        contract_changed.filtered(lambda c: not c.calendar_changed).write({'calendar_changed': True})
        (self - contract_changed).filtered(lambda c: c.calendar_changed).write({'calendar_changed': False})

    @api.model
    def _recompute_calendar_changed(self, employee_ids):
        contract_ids = self.search([('employee_id', 'in', employee_ids.ids)], order='date_start asc')
        if not contract_ids:
            return
        contract_ids._compute_calendar_changed()

    def action_open_payslips(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_view_hr_payslip_month_form")
        action.update({'domain': [('contract_id', '=', self.id)]})
        return action

    def _index_contracts(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_hr_payroll_index")
        action['context'] = repr(self.env.context)
        return action

    def _get_work_hours_domain(self, date_from, date_to, domain=None, inside=True):
        if domain is None:
            domain = []
        domain = expression.AND([domain, [
            ('state', 'in', ['validated', 'draft']),
            ('contract_id', 'in', self.ids),
        ]])
        if inside:
            domain = expression.AND([domain, [
                ('date_start', '>=', date_from),
                ('date_stop', '<=', date_to)]])
        else:
            domain = expression.AND([domain, [
                '|', '|',
                '&', '&',
                    ('date_start', '>=', date_from),
                    ('date_start', '<', date_to),
                    ('date_stop', '>', date_to),
                '&', '&',
                    ('date_start', '<', date_from),
                    ('date_stop', '<=', date_to),
                    ('date_stop', '>', date_from),
                '&',
                    ('date_start', '<', date_from),
                    ('date_stop', '>', date_to)]])
        return domain

    def _get_work_hours(self, date_from, date_to, domain=None):
        """
        Returns the amount (expressed in hours) of work
        for a contract between two dates.
        If called on multiple contracts, sum work amounts of each contract.
        :param date_from: The start date
        :param date_to: The end date
        :returns: a dictionary {work_entry_id: hours_1, work_entry_2: hours_2}
        """

        date_from = datetime.combine(date_from, datetime.min.time())
        date_to = datetime.combine(date_to, datetime.max.time())
        work_data = defaultdict(int)

        # First, found work entry that didn't exceed interval.
        work_entries = self.env['hr.work.entry'].read_group(
            self._get_work_hours_domain(date_from, date_to, domain=domain, inside=True),
            ['hours:sum(duration)'],
            ['work_entry_type_id']
        )
        work_data.update({data['work_entry_type_id'][0] if data['work_entry_type_id'] else False: data['hours'] for data in work_entries})

        # Second, find work entry that exceeds interval and compute right duration.
        work_entries = self.env['hr.work.entry'].search(self._get_work_hours_domain(date_from, date_to, domain=domain, inside=False))

        for work_entry in work_entries:
            date_start = max(date_from, work_entry.date_start)
            date_stop = min(date_to, work_entry.date_stop)
            if work_entry.work_entry_type_id.is_leave:
                contract = work_entry.contract_id
                calendar = contract.resource_calendar_id
                employee = contract.employee_id
                contract_data = employee._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar
                )[employee.id]

                work_data[work_entry.work_entry_type_id.id] += contract_data.get('hours', 0)
            else:
                dt = date_stop - date_start
                work_data[work_entry.work_entry_type_id.id] += dt.days * 24 + dt.seconds / 3600  # Number of hours
        return work_data

    def _get_default_work_entry_type(self):
        return self.structure_type_id.default_work_entry_type_id or super(HrContract, self)._get_default_work_entry_type()

    def _get_fields_that_recompute_payslip(self):
        # Returns the fields that should recompute the payslip
        return [self._get_contract_wage]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._recompute_calendar_changed(res.mapped('employee_id'))
        return res

    def unlink(self):
        employee_ids = self.mapped('employee_id')
        res = super().unlink()
        self._recompute_calendar_changed(employee_ids)
        return res

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'cancel':
            self.env['hr.payslip'].search([
                ('contract_id', 'in', self.filtered(lambda c: c.state != 'cancel').ids),
                ('state', 'in', ['draft', 'verify']),
            ]).action_payslip_cancel()
        res = super().write(vals)
        dependendant_fields = self._get_fields_that_recompute_payslip()
        if any(key in dependendant_fields for key in vals.keys()):
            for contract in self:
                contract._recompute_payslips(self.date_start, self.date_end or date.max)
        if any(key in vals for key in ('state', 'date_start', 'resource_calendar_id', 'employee_id')):
            self._recompute_calendar_changed(self.mapped('employee_id'))
        return res

    def _recompute_work_entries(self, date_from, date_to):
        self.ensure_one()
        super()._recompute_work_entries(date_from, date_to)
        self._recompute_payslips(date_from, date_to)

    def _recompute_payslips(self, date_from, date_to):
        self.ensure_one()
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('contract_id', '=', self.id),
            ('state', 'in', ['draft', 'verify']),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('company_id', '=', self.env.company.id),
        ]).filtered(lambda p: p.is_regular)
        if all_payslips:
            all_payslips.action_refresh_from_work_entries()

    def action_new_salary_attachment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Salary Attachment'),
            'res_model': 'hr.salary.attachment',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.employee_id.id}
        }
