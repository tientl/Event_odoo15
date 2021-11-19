#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        res.update({
            'compute_holiday_pay_recovery_n': compute_holiday_pay_recovery_n,
            'compute_holiday_pay_recovery_n1': compute_holiday_pay_recovery_n1,
        })
        return res

def compute_holiday_pay_recovery_n(payslip, categories, worked_days, inputs):
    """
        See: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/intermediates#intermediate_row_196b32c7-9d98-4233-805d-ca9bf123ff48

        When an employee changes employer, he receives the termination pay and a vacation certificate
        stating his vacation rights. When he subsequently takes vacation with his new employer, the latter
        must, when paying the simple vacation pay, take into account the termination pay that the former
        employer has already paid.

        From an exchange of letters with the SPF ETCS and the Inspectorate responsible for the control of
        social laws, it turned out that when calculating the simple vacation pay, the new employer must
        deduct the exit pay based on the number of vacation days taken. The rule in the ONSS instructions
        according to which the new employer must take into account the exit vacation pay only once when the
        employee takes his main vacation is abolished.

        When the salary of an employee with his new employer is higher than the salary he had with his
        previous employer, his new employer will have, each time he takes vacation days, to make a
        calculation to supplement the nest egg. exit from these days up to the amount of the simple vacation
        pay to which the worker is entitled.

        Concretely:

        2020 vacation certificate (full year):
        - simple allowance 1,917.50 EUR
            - this amounts to 1917.50 / 20 EUR = 95.875 EUR per day of vacation
            - holidays 2021, for example when taking 5 days in April 2021
        - monthly salary with the new employer: 3000.00 EUR / month
            - simple nest egg:
                 - remuneration code 12: 5/20 x 1917.50 = 479.38 EUR
                 - remuneration code 1: (5/22 x 3000.00) - 479.38 = 202.44 EUR
            - ordinary days for the month of April:
                - remuneration code 1: 17/22 x 3000.00 = 2318.18 EUR
                - The examples included in the ONSS instructions will be adapted in the next publication.
    """

    employee = payslip.dict.employee_id
    number_of_days = employee.l10n_be_holiday_pay_number_of_days_n
    hourly_amount_to_recover = employee.l10n_be_holiday_pay_to_recover_n / (number_of_days * 7.6)
    if not worked_days.LEAVE120 or not worked_days.LEAVE120.amount:
        return 0
    holiday_amount = min(worked_days.LEAVE120.amount, hourly_amount_to_recover * worked_days.LEAVE120.number_of_hours)
    recovered_amount = employee.l10n_be_holiday_pay_recovered_n
    remaining_amount = employee.l10n_be_holiday_pay_to_recover_n - recovered_amount
    return - min(remaining_amount, holiday_amount)

def compute_holiday_pay_recovery_n1(payslip, categories, worked_days, inputs):
    employee = payslip.dict.employee_id
    number_of_days = employee.l10n_be_holiday_pay_number_of_days_n1
    hourly_amount_to_recover = employee.l10n_be_holiday_pay_to_recover_n1 / (number_of_days * 7.6)
    if not worked_days.LEAVE120 or not worked_days.LEAVE120.amount:
        return 0
    holiday_amount = min(worked_days.LEAVE120.amount, hourly_amount_to_recover * worked_days.LEAVE120.number_of_hours)
    recovered_amount = employee.l10n_be_holiday_pay_recovered_n1
    remaining_amount = employee.l10n_be_holiday_pay_to_recover_n1 - recovered_amount
    return - min(remaining_amount, holiday_amount)
