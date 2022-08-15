# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _order = 'sequence, id'
    _description = 'Salary Rule'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True,
        help="The code of salary rules can be used as reference in computation of other rules. "
             "In that case, it is case sensitive.")
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure", required=True)
    sequence = fields.Integer(required=True, index=True, default=5,
        help='Use to arrange calculation sequence')
    quantity = fields.Char(default='1.0',
        help="It is used in computation for percentage and fixed amount. "
             "E.g. a rule for Meal Voucher having fixed amount of "
             u"1€ per worked day can have its quantity defined in expression "
             "like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    active = fields.Boolean(default=True,
        help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(string='Appears on Payslip', default=True,
        help="Used to display the salary rule on payslip.")
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True)
    condition_range = fields.Char(string='Range Based on', default='contract.wage',
        help='This will be used to compute the % fields values; in general it is on basic, '
             'but you can also use categories code fields in lowercase as a variable names '
             '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True,
        default='''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = rules.NET > categories.NET * 0.10''',
        help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range', help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float(string='Maximum Range', help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix', help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fixed Amount', digits='Payroll')
    amount_percentage = fields.Float(string='Percentage (%)', digits='Payroll Rate',
        help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text(string='Python Code',
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days.
                    # inputs: object containing the computed inputs.

                    # Note: returned value have to be set in the variable 'result'

                    result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable')
    partner_id = fields.Many2one('res.partner', string='Partner',
        help="Eventual third party involved in the salary payment of the employees.")
    note = fields.Html(string='Description')

    def _raise_error(self, localdict, error_type, e):
        raise UserError(_("""%s:
- Employee: %s
- Contract: %s
- Payslip: %s
- Salary rule: %s (%s)
- Error: %s""") % (
            error_type,
            localdict['employee'].name,
            localdict['contract'].name,
            localdict['payslip'].dict.name,
            self.name,
            self.code,
            e))

    def _compute_rule(self, localdict):

        """
        :param localdict: dictionary containing the current computation environment
        :return: returns a tuple (amount, qty, rate)
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix or 0.0, float(safe_eval(self.quantity, localdict)), 100.0
            except Exception as e:
                self._raise_error(localdict, _("Wrong quantity defined for:"), e)
        if self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage or 0.0)
            except Exception as e:
                self._raise_error(localdict, _("Wrong percentage base or quantity defined for:"), e)
        else:  # python code
            try:
                safe_eval(self.amount_python_compute or 0.0, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), localdict.get('result_qty', 1.0), localdict.get('result_rate', 100.0)
            except Exception as e:
                self._raise_error(localdict, _("Wrong python code defined for:"), e)

    def _satisfy_condition(self, localdict):
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        if self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except Exception as e:
                self._raise_error(localdict, _("Wrong range condition defined for:"), e)
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception as e:
                self._raise_error(localdict, _("Wrong python condition defined for:"), e)
