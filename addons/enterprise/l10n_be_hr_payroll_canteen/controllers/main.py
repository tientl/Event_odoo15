# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_contract_salary.controllers import main


class HrContractSalary(main.HrContractSalary):
    def _get_new_contract_values(self, contract, employee, advantages):
        res = super()._get_new_contract_values(contract, employee, advantages)
        res['l10n_be_canteen_cost'] = advantages['l10n_be_canteen_cost']
        return res

    def _apply_url_value(self, contract, field_name, value):
        if field_name == 'l10n_be_canteen_cost':
            return {'l10n_be_canteen_cost': value}
        return super()._apply_url_value(contract, field_name, value)

    def _get_default_template_values(self, contract):
        values = super()._get_default_template_values(contract)
        values['l10n_be_canteen_cost'] = False
        return values
