# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _get_query_reconciliation_widget_miscellaneous_matching_lines(self, statement_line, domain=[]):
        # OVERRIDE
        account_ids = []
        for account_property in [
            'property_stock_account_input',
            'property_stock_account_output',
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
        ]:
            account = self.env['ir.property']._get(account_property, "product.category")
            if account:
                account_ids.append(account.id)

        if account_ids:
            domain.append(('account_id', 'not in', tuple(account_ids)))
        return super()._get_query_reconciliation_widget_miscellaneous_matching_lines(statement_line, domain=domain)
