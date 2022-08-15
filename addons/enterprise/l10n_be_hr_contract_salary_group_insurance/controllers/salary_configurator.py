# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_contract_salary.controllers import main
from odoo.http import route, request


class HrContractSalary(main.HrContractSalary):

    @route(['/salary_package/onchange_advantage'], type='json', auth='public')
    def onchange_advantage(self, advantage_field, new_value, contract_id, advantages):
        res = super().onchange_advantage(advantage_field, new_value, contract_id, advantages)
        insurance_fields = [
            'l10n_be_ambulatory_insured_children', 'l10n_be_ambulatory_insured_adults',
            'fold_l10n_be_ambulatory_insured_spouse', 'l10n_be_has_ambulatory_insurance']
        if advantage_field in insurance_fields:
            child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_child', default=7.2))
            adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_adult', default=20.5))
            adv = advantages['contract']
            child_count = int(adv['l10n_be_ambulatory_insured_children_manual'] or False)
            l10n_be_has_ambulatory_insurance = float(adv['l10n_be_has_ambulatory_insurance_radio']) == 1.0 if 'l10n_be_has_ambulatory_insurance_radio' in adv else False
            adult_count = int(adv['l10n_be_ambulatory_insured_adults_manual'] or False) \
                        + int(adv['fold_l10n_be_ambulatory_insured_spouse']) \
                        + int(l10n_be_has_ambulatory_insurance)
            insurance_amount = request.env['hr.contract']._get_insurance_amount(
                child_amount, child_count,
                adult_amount, adult_count)
            res['extra_values'] = [('l10n_be_has_ambulatory_insurance', insurance_amount)]
        return res

    def _get_advantages_values(self, contract):
        mapped_advantages, advantage_types, dropdown_options, dropdown_group_otions, initial_values = super()._get_advantages_values(contract)
        initial_values['l10n_be_has_ambulatory_insurance'] = contract.l10n_be_ambulatory_insurance_amount
        return mapped_advantages, advantage_types, dropdown_options, dropdown_group_otions, initial_values

    def _get_new_contract_values(self, contract, employee, advantages):
        res = super()._get_new_contract_values(contract, employee, advantages)
        res['l10n_be_has_ambulatory_insurance'] = float(advantages['l10n_be_has_ambulatory_insurance_radio']) == 1.0 if 'l10n_be_has_ambulatory_insurance_radio' in advantages else False
        return res
