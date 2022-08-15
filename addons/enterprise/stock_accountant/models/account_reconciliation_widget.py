# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _get_query_reconciliation_widget_miscellaneous_matching_lines(self, statement_line, domain=[]):
        # OVERRIDE
        account_stock_properties_names = [
            'property_stock_account_input',
            'property_stock_account_output',
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
        ]
        properties = self.env['ir.property'].sudo().search([
            ('name', 'in', account_stock_properties_names),
            ('company_id', '=', self.env.company.id),
            ('value_reference', '!=', False),
        ])

        if properties:
            accounts = properties.mapped(lambda p: p.get_by_record())
            domain.append(('account_id', 'not in', tuple(accounts.ids)))
        return super()._get_query_reconciliation_widget_miscellaneous_matching_lines(statement_line, domain=domain)
