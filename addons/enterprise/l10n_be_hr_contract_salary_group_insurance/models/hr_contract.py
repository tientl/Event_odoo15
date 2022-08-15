# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    wage_with_holidays = fields.Monetary(
        string="Wage With Sacrifices",
        help="Adapted salary, according to the sacrifices defined on the contract (Example: Extra-legal time off, a percentage of the salary invested in a group insurance, etc...)")
    # Group Insurance
    l10n_be_group_insurance_rate = fields.Float(
        string="Group Insurance Sacrifice Rate", tracking=True,
        help="Should be between 0 and 100 %")
    l10n_be_group_insurance_amount = fields.Monetary(
        compute='_compute_l10n_be_group_insurance_amount', store=True)
    l10n_be_group_insurance_cost = fields.Monetary(
        compute='_compute_l10n_be_group_insurance_amount', store=True)
    # Ambulatory Insurance
    l10n_be_has_ambulatory_insurance = fields.Boolean(
        string="Has Ambulatory Insurance",
        groups="hr_contract.group_hr_contract_manager", tracking=True)
    l10n_be_ambulatory_insured_children = fields.Integer(
        string="Ambulatory: # Insured Children < 19",
        groups="hr_contract.group_hr_contract_manager", tracking=True)
    l10n_be_ambulatory_insured_adults = fields.Integer(
        string="Ambulatory: # Insured Children >= 19",
        groups="hr_contract.group_hr_contract_manager", tracking=True)
    l10n_be_ambulatory_insured_spouse = fields.Boolean(
        string="Ambulatory: Insured Spouse",
        groups="hr_contract.group_hr_contract_manager", tracking=True)
    l10n_be_ambulatory_amount_per_child = fields.Float(
        string="Ambulatory: Amount per Child", groups="hr_contract.group_hr_contract_manager",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_child', default=7.2)))
    l10n_be_ambulatory_amount_per_adult = fields.Float(
        string="Ambulatory: Amount per Adult", groups="hr_contract.group_hr_contract_manager",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_adult', default=20.5)))
    l10n_be_ambulatory_insurance_amount = fields.Float(
        compute='_compute_ambulatory_insurance_amount', string="Ambulatory: Insurance Amount",
        groups="hr_contract.group_hr_contract_manager", tracking=True)
    l10n_be_ambulatory_insured_adults_total = fields.Integer(
        compute='_compute_ambulatory_insured_adults_total',
        groups="hr_contract.group_hr_contract_manager")

    _sql_constraints = [
        ('check_percentage_group_insurance_rate', 'CHECK(l10n_be_group_insurance_rate >= 0 AND l10n_be_group_insurance_rate <= 100)', 'The group insurance salary sacrifice rate on wage should be between 0 and 100.'),
    ]

    @api.depends('holidays', 'wage', 'final_yearly_costs', 'l10n_be_group_insurance_rate')
    def _compute_wage_with_holidays(self):
        super()._compute_wage_with_holidays()

    @api.depends('wage', 'l10n_be_group_insurance_rate')
    def _compute_l10n_be_group_insurance_amount(self):
        for contract in self:
            rate = contract.l10n_be_group_insurance_rate
            insurance_amount = contract.wage * rate / 100.0
            contract.l10n_be_group_insurance_amount = insurance_amount
            # Example
            # 5 % salary configurator
            # 4.4 % insurance cost
            # 8.86 % ONSS
            # =-----------------------
            # 13.26 % over the 5%
            contract.l10n_be_group_insurance_cost = insurance_amount * (1 + 13.26 / 100.0)

    def _is_salary_sacrifice(self):
        self.ensure_one()
        return super()._is_salary_sacrifice() or self.l10n_be_group_insurance_rate

    def _get_yearly_cost_sacrifice_fixed(self):
        return super()._get_yearly_cost_sacrifice_fixed() + self._get_salary_costs_factor() * self.wage * self.l10n_be_group_insurance_rate / 100

    def _get_salary_costs_factor(self):
        self.ensure_one()
        res = super()._get_salary_costs_factor()
        if self.l10n_be_group_insurance_rate:
            return res * (1.0 - self.l10n_be_group_insurance_rate / 100)
        return res

    @api.depends(
        'l10n_be_has_ambulatory_insurance',
        'l10n_be_ambulatory_insured_adults',
        'l10n_be_ambulatory_insured_spouse')
    def _compute_ambulatory_insured_adults_total(self):
        for contract in self:
            contract.l10n_be_ambulatory_insured_adults_total = (
                int(contract.l10n_be_has_ambulatory_insurance)
                + contract.l10n_be_ambulatory_insured_adults
                + int(contract.l10n_be_ambulatory_insured_spouse))

    @api.model
    def _get_ambulatory_insurance_amount(self, child_amount, child_count, adult_amount, adult_count):
        return child_amount * child_count + adult_amount * adult_count

    @api.depends(
        'l10n_be_ambulatory_insured_children', 'l10n_be_ambulatory_insured_adults_total',
        'l10n_be_ambulatory_amount_per_child', 'l10n_be_ambulatory_amount_per_adult')
    def _compute_ambulatory_insurance_amount(self):
        for contract in self:
            contract.l10n_be_ambulatory_insurance_amount = contract._get_ambulatory_insurance_amount(
                contract.l10n_be_ambulatory_amount_per_child,
                contract.l10n_be_ambulatory_insured_children,
                contract.l10n_be_ambulatory_amount_per_adult,
                contract.l10n_be_ambulatory_insured_adults_total)

    def _get_contract_insurance_amount(self, name):
        self.ensure_one()
        if name == 'ambulatory':
            return self.l10n_be_ambulatory_insurance_amount
        if name == 'group':
            return self.l10n_be_group_insurance_amount * (1 + 4.4 / 100.0)
        return super()._get_contract_insurance_amount(name)

    def _get_advantage_values_l10n_be_ambulatory_insured_spouse(self, contract, advantages):
        return {'l10n_be_ambulatory_insured_spouse': advantages['fold_l10n_be_ambulatory_insured_spouse']}
