# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import reduce

from odoo import api, fields, models, _

EMPLOYER_ONSS = 0.2714


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    niss = fields.Char(
        'NISS Number', compute="_compute_niss", store=True, readonly=False,
        groups="hr.group_hr_user", tracking=True)
    spouse_fiscal_status = fields.Selection([
        ('without_income', 'Without Income'),
        ('high_income', 'With High income'),
        ('low_income', 'With Low Income'),
        ('low_pension', 'With Low Pensions'),
        ('high_pension', 'With High Pensions')
    ], string='Tax status for spouse', groups="hr.group_hr_user", default='without_income', required=False)
    spouse_fiscal_status_explanation = fields.Char(compute='_compute_spouse_fiscal_status_explanation')
    disabled = fields.Boolean(string="Disabled", help="If the employee is declared disabled by law", groups="hr.group_hr_user")
    disabled_spouse_bool = fields.Boolean(string='Disabled Spouse', help='if recipient spouse is declared disabled by law', groups="hr.group_hr_user")
    disabled_children_bool = fields.Boolean(string='Disabled Children', help='if recipient children is/are declared disabled by law', groups="hr.group_hr_user")
    resident_bool = fields.Boolean(string='Nonresident', help='if recipient lives in a foreign country', groups="hr.group_hr_user")
    disabled_children_number = fields.Integer('Number of disabled children', groups="hr.group_hr_user")
    dependent_children = fields.Integer(compute='_compute_dependent_children', string='Considered number of dependent children', groups="hr.group_hr_user")
    l10n_be_dependent_children_attachment = fields.Integer(
        string="# dependent children for salary attachement", groups="hr.group_hr_user",
        help="""To benefit from this increase in the elusive or non-transferable quotas, the worker whose remuneration is subject to seizure or transfer, must declare it using a form, the model of which has been published in the Belgian Official Gazette. of 30 November 2006.

He must attach to this form the documents establishing the reality of the charge invoked.

Source: Opinion on the indexation of the amounts set in Article 1, paragraph 4, of the Royal Decree of 27 December 2004 implementing Articles 1409, § 1, paragraph 4, and 1409, § 1 bis, paragraph 4 , of the Judicial Code relating to the limitation of seizure when there are dependent children, MB, December 13, 2019.""")
    other_dependent_people = fields.Boolean(string="Other Dependent People", help="If other people are dependent on the employee", groups="hr.group_hr_user")
    other_senior_dependent = fields.Integer('# seniors (>=65)', help="Number of seniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user")
    other_disabled_senior_dependent = fields.Integer('# disabled seniors (>=65)', groups="hr.group_hr_user")
    other_juniors_dependent = fields.Integer('# people (<65)', help="Number of juniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user")
    other_disabled_juniors_dependent = fields.Integer('# disabled people (<65)', groups="hr.group_hr_user")
    dependent_seniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent seniors", groups="hr.group_hr_user")
    dependent_juniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent juniors", groups="hr.group_hr_user")

    start_notice_period = fields.Date("Start notice period", groups="hr.group_hr_user", copy=False, tracking=True)
    end_notice_period = fields.Date("End notice period", groups="hr.group_hr_user", copy=False, tracking=True)
    first_contract_in_company = fields.Date("First contract in company", groups="hr.group_hr_user", copy=False)

    has_bicycle = fields.Boolean(string="Bicycle to work", default=False, groups="hr.group_hr_user",
        help="Use a bicycle as a transport mode to go to work")
    certificate = fields.Selection(selection_add=[('civil_engineer', 'Master: Civil Engineering')])
    l10n_be_scale_seniority = fields.Integer(string="Seniority at Hiring", groups="hr.group_hr_user", tracking=True)

    double_pay_line_ids = fields.One2many(
        'l10n.be.double.pay.recovery.line', 'employee_id',
        string='Previous Occupations', groups="hr_payroll.group_hr_payroll_user")

    def _compute_spouse_fiscal_status_explanation(self):
        low_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_low_income_threshold')
        other_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_other_income_threshold')
        for employee in self:
            employee.spouse_fiscal_status_explanation = _("""- Without Income: The spouse of the income recipient has no professional income.\n
- High income: The spouse of the recipient of the income has professional income, other than pensions, annuities or similar income, which exceeds %s€ net per month.\n
- Low Income: The spouse of the recipient of the income has professional income, other than pensions, annuities or similar income, which does not exceed %s€ net per month.\n
- Low Pensions: The spouse of the beneficiary of the income has professional income which consists exclusively of pensions, annuities or similar income and which does not exceed %s€ net per month.\n
- High Pensions: The spouse of the beneficiary of the income has professional income which consists exclusively of pensions, annuities or similar income and which exceeds %s€ net per month.""", low_income_threshold, low_income_threshold, other_income_threshold, other_income_threshold)

    @api.depends('identification_id')
    def _compute_niss(self):
        characters = dict.fromkeys([',', '.', '-', ' '], '')
        for employee in self:
            if employee.identification_id and not employee.niss:
                employee.niss = reduce(lambda a, kv: a.replace(*kv), characters.items(), employee.identification_id)

    def _is_niss_valid(self):
        # The last 2 positions constitute the check digit. This check digit is
        # a sequence of 2 digits forming a number between 01 and 97. This number is equal to 97
        # minus the remainder of the division by 97 of the number formed:
        # - either by the first 9 digits of the national number for people born before the 1st
        # January 2000.
        # - either by the number 2 followed by the first 9 digits of the national number for people
        # born after December 31, 1999.
        # (https://fr.wikipedia.org/wiki/Num%C3%A9ro_de_registre_national)
        self.ensure_one()
        niss = self.niss
        if not niss or len(niss) != 11:
            return False
        try:
            test = niss[:-2]
            if test[0] in ['0', '1', '2', '3', '4', '5']:  # Should be good for several years
                test = '2%s' % test
            checksum = int(niss[-2:])
            return checksum == 97 - int(test) % 97
        except Exception:
            return False

    @api.onchange('disabled_children_bool')
    def _onchange_disabled_children_bool(self):
        self.disabled_children_number = 0

    @api.onchange('other_dependent_people')
    def _onchange_other_dependent_people(self):
        self.other_senior_dependent = 0.0
        self.other_disabled_senior_dependent = 0.0
        self.other_juniors_dependent = 0.0
        self.other_disabled_juniors_dependent = 0.0

    @api.depends('disabled_children_bool', 'disabled_children_number', 'children')
    def _compute_dependent_children(self):
        for employee in self:
            if employee.disabled_children_bool:
                employee.dependent_children = employee.children + employee.disabled_children_number
            else:
                employee.dependent_children = employee.children

    @api.depends('other_dependent_people', 'other_senior_dependent',
        'other_disabled_senior_dependent', 'other_juniors_dependent', 'other_disabled_juniors_dependent')
    def _compute_dependent_people(self):
        for employee in self:
            employee.dependent_seniors = employee.other_senior_dependent + employee.other_disabled_senior_dependent
            employee.dependent_juniors = employee.other_juniors_dependent + employee.other_disabled_juniors_dependent
