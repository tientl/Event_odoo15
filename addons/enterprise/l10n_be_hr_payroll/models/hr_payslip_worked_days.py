# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    is_credit_time = fields.Boolean(string='Credit Time')

    @api.depends('is_paid', 'is_credit_time', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        monthly_self = self.filtered(lambda wd: not wd.payslip_id.edited and wd.payslip_id.wage_type == "monthly")

        credit_time_days = monthly_self.filtered(lambda worked_day: worked_day.is_credit_time)
        credit_time_days.update({'amount': 0})

        # For the average of the variable remuneration:
        # Taking into account the full number of months with the employer
        # Variable monthly average remuneration to be divided by 25 and increased by 20% (in 5-day regime).
        # Example: if over 7 months, the variable average monthly remuneration is € 1,212.
        # You add, to the JF, the following amount: 1212/25 = 48.48 + 20% = € 58.17.
        variable_salary_wd = self.filtered(lambda wd: wd.code == 'LEAVE1731')
        for wd in variable_salary_wd:
            amount = wd.payslip_id._get_last_year_average_variable_revenues()
            amount = amount / 25.0
            if not float_compare(wd.payslip_id.contract_id.resource_calendar_id.work_time_rate, 100, precision_digits=2):
                amount *= 1.2
            wd.amount = amount

        paid_be_wds = (monthly_self - credit_time_days - variable_salary_wd).filtered(
            lambda wd: wd.payslip_id.struct_id.country_id.code == "BE" and wd.is_paid)

        if paid_be_wds:
            for be_wd in paid_be_wds:
                payslip = be_wd.payslip_id
                contract = payslip.contract_id
                calendar = payslip.contract_id.resource_calendar_id or payslip.employee_id.resource_calendar_id
                tz = pytz.timezone(calendar.tz)
                hours_per_week = calendar.hours_per_week
                wage = payslip._get_contract_wage() if payslip.contract_id else 0

                # We usually deduct the unpaid hours using the hourly formula. This is the fairest
                # way to deduct 1 day, because we will deduct the same amount in a short month (February)
                # than in a long month (March)
                # But in the case of the long month with not enough paid hours, this could lead
                # to a basic salary = 0, which is in that case unfair. Switch to another method in which
                # we compute the amount from the paid hours using the hourly formula
                paid_hours = sum(be_wd.payslip_id.worked_days_line_ids.filtered(
                    lambda wd: wd.is_paid and wd.work_entry_type_id.code not in ['OUT', 'LEAVE300', 'LEAVE301']
                ).mapped('number_of_hours'))
                if paid_hours < hours_per_week and be_wd.work_entry_type_id.code not in ['OUT', 'LEAVE300', 'LEAVE301']:
                    be_wd.amount = wage * 3 / (13 * hours_per_week) * be_wd.number_of_hours
                    continue

                # If out of contract, we use the hourly formula to deduct the real wage
                out_be_wd = be_wd.payslip_id.worked_days_line_ids.filtered(lambda wd: wd.code == 'OUT')
                if out_be_wd:
                    out_hours = sum([wd.number_of_hours for wd in out_be_wd])
                    # Don't count out of contract time that actually was a credit time 
                    if payslip.contract_id.time_credit:
                        if contract.date_start > payslip.date_from:
                            start = payslip.date_from
                            end = contract.date_start
                            start_dt = tz.localize(fields.Datetime.to_datetime(start))
                            end_dt = tz.localize(fields.Datetime.to_datetime(end) + timedelta(days=1, seconds=-1))
                            credit_time_attendances = payslip.contract_id.resource_calendar_id._attendance_intervals_batch(start_dt, end_dt)[False]
                            standard_attendances = payslip.contract_id.standard_calendar_id._attendance_intervals_batch(start_dt, end_dt)[False]
                            out_hours -= sum([(stop - start).total_seconds() / 3600 for start, stop, dummy in standard_attendances - credit_time_attendances])
                        if contract.date_end and contract.date_end < payslip.date_to:
                            start = contract.date_end
                            end = payslip.date_to
                            start_dt = tz.localize(fields.Datetime.to_datetime(start))
                            end_dt = tz.localize(fields.Datetime.to_datetime(end) + timedelta(days=1, seconds=-1))
                            credit_time_attendances = payslip.contract_id.resource_calendar_id._attendance_intervals_batch(start_dt, end_dt)[False]
                            standard_attendances = payslip.contract_id.standard_calendar_id._attendance_intervals_batch(start_dt, end_dt)[False]
                            out_hours -= sum([(stop - start).total_seconds() / 3600 for start, stop, dummy in standard_attendances - credit_time_attendances])

                    out_ratio = 1 - 3 / (13 * hours_per_week) * out_hours if hours_per_week else 1
                else:
                    out_ratio = 1

                # For training time off: The maximum reimbursement is fixed by a threshold that you can
                # find at https://www.leforem.be/entreprises/aides-financieres-conge-education-paye.html
                # In that case we have to adapt the wage.
                wage_to_deduct = 0
                max_hours_per_week = contract.standard_calendar_id.hours_per_week or contract.resource_calendar_id.hours_per_week
                training_ratio = 3 / (13 * max_hours_per_week) if max_hours_per_week else 0
                training_wds = paid_be_wds.filtered(lambda wd: wd.work_entry_type_id.code == "LEAVE260")
                if training_wds:
                    training_hours = sum(training_wds.mapped('number_of_hours'))
                    training_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                        'training_time_off_threshold', payslip.date_to, raise_if_not_found=False)
                    if wage > training_threshold:
                        hourly_wage_to_deduct = (wage - training_threshold) * training_ratio
                        wage_to_deduct = training_hours * hourly_wage_to_deduct

                ####################################################################################
                #  Example:
                #  Note: 3/13/38) * wage : hourly wage, if 13th months and 38 hours/week calendar
                #
                #  CODE     :   number_of_hours    :    Amount
                #  WORK100  :      130 hours       : (1 - 3/13/38 * (15 + 30)) * wage
                #  PAID     :      30 hours        : 3/13/38 * (15 + 30)) * wage
                #  UNPAID   :      15 hours        : 0
                #
                #  TOTAL PAID : WORK100 + PAID + UNPAID = (1 - 3/13/38 * 15 ) * wage
                ####################################################################################
                main_worked_day = "WORK100"
                if main_worked_day not in be_wd.payslip_id.worked_days_line_ids.mapped('code'):
                    main_worked_day = be_wd.payslip_id.worked_days_line_ids.filtered(
                        lambda wd: wd.is_paid and wd.code not in ['LEAVE300', 'LEAVE301'])
                    main_worked_day = main_worked_day[0].code if main_worked_day else False

                if be_wd.code == 'OUT':
                    worked_day_amount = 0
                elif wage_to_deduct and be_wd.code == 'LEAVE260':
                    worked_day_amount = min(wage, training_threshold) * training_ratio * training_hours
                elif be_wd.code == main_worked_day:  # WORK100 (Generally)
                    # Case with half days mixed with full days
                    work100_wds = be_wd.payslip_id.worked_days_line_ids.filtered(lambda wd: wd.code == "WORK100")
                    number_of_hours = sum([
                        wd.number_of_hours
                        for wd in be_wd.payslip_id.worked_days_line_ids
                        if wd.code not in [main_worked_day, 'OUT'] and not wd.is_credit_time])
                    if len(work100_wds) > 1:
                        # In this case, we cannot use the hourly formula since the monthly
                        # salary must always be the same, without having an identical number of
                        # working days

                        # If only presence -> Compute the full days from the hourly formula
                        if len(list(set(be_wd.payslip_id.worked_days_line_ids.mapped('code')))) == 1:
                            ratio = (out_ratio - 3 / (13 * hours_per_week) * number_of_hours) if hours_per_week else 0
                            worked_day_amount = wage * ratio
                            if float_compare(be_wd.number_of_hours, max(work100_wds.mapped('number_of_hours')), 2): # lowest lines
                                # Don't remove this strange hack. Here is the use case:
                                # Set an employee on the payslip, it calls _onchange_employee to:
                                # 1/ Set a contract
                                # 2/ Set a structure
                                # 3/ Compute the worked days
                                # The actions 1/ and 2/ implies to call the _onchange_method again
                                # So we will create all the worked days (let's say n records) 3 times
                                # (and the 2 first batches will be dropped).
                                # The 2 first batches won't be part of the cache of the record, so
                                # be_wd.payslip_id.worked_days_line_ids will return only n records
                                # But in an indeterministic way, the records could still be marked
                                # as to recompute, for the stored / computed amount field.
                                # So self will contain 3 * n records in that case.
                                # This could lead to a situation in which work100_wds contains the
                                # 2 valid attendance worked days, and be_wd is an invalid other worked
                                # day, leading to a singleton error when trying to read the number_of_hours
                                # field.
                                if be_wd not in work100_wds:
                                    ratio = 0
                                else:
                                    ratio = 3 / (13 * hours_per_week) * (work100_wds - be_wd).number_of_hours if hours_per_week else 0
                                worked_day_amount = worked_day_amount * (1 - ratio)
                            else:  # biggest line
                                ratio = 3 / (13 * hours_per_week) * be_wd.number_of_hours if hours_per_week else 0
                                worked_day_amount = worked_day_amount * ratio
                        # Mix of presence/absences - Compute the half days from the hourly formula
                        else:
                            if float_compare(be_wd.number_of_hours, max(work100_wds.mapped('number_of_hours')), 2): # lowest lines
                                ratio = 3 / (13 * hours_per_week) * be_wd.number_of_hours if hours_per_week else 0
                                worked_day_amount = wage * ratio
                                # ratio = 3 / (13 * hours_per_week) * (work100_wds - be_wd).number_of_hours if hours_per_week else 0
                                # worked_day_amount = worked_day_amount * (1 - ratio)
                            else:  # biggest line
                                total_wage = (out_ratio - 3 / (13 * hours_per_week) * number_of_hours) * wage if hours_per_week else 0
                                # Don't remove this strange hack -> See explanation above
                                if be_wd not in work100_wds:
                                    ratio = 0
                                else:
                                    ratio = 3 / (13 * hours_per_week) * (work100_wds - be_wd).number_of_hours if hours_per_week else 0
                                worked_day_amount = total_wage - wage * ratio
                                # ratio = 3 / (13 * hours_per_week) * be_wd.number_of_hours if hours_per_week else 0
                                # worked_day_amount = worked_day_amount * ratio
                    else:
                        # Classic case : Only 1 WORK100 line
                        ratio = (out_ratio - 3 / (13 * hours_per_week) * number_of_hours) if hours_per_week else 0
                        worked_day_amount = max(wage * ratio, 0)
                else:
                    number_of_hours = be_wd.number_of_hours
                    ratio = 3 / (13 * hours_per_week) * number_of_hours if hours_per_week else 0
                    worked_day_amount = wage * ratio
                    if worked_day_amount > wage:
                        worked_day_amount = wage
                be_wd.amount = worked_day_amount

        super(HrPayslipWorkedDays, self - credit_time_days - paid_be_wds - variable_salary_wd)._compute_amount()
