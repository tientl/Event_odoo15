# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger"

    def _get_query_amls_select_clause(self):
        # OVERRIDE to fetch currency name
        select = '''
            cur.name                     AS currency_name,
            account_move_line.move_id    AS move_id,
        '''
        select += super()._get_query_amls_select_clause()
        return select

    def _get_query_amls_from_clause(self):
        # OVERRIDE to fetch currency name
        from_clause = super()._get_query_amls_from_clause()
        from_clause += '''
            LEFT JOIN res_currency cur ON cur.id = account_move_line.currency_id
        '''
        return from_clause
