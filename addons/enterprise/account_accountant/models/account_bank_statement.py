from odoo import models

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def action_bank_reconcile_bank_statements(self):
        self.ensure_one()
        limit = int(self.env["ir.config_parameter"].sudo().get_param("account.reconcile.batch", 1000))
        bank_stmt_lines = self.env['account.bank.statement.line'].search([
            ('statement_id', 'in', self.ids),
            ('is_reconciled', '=', False),
        ], limit=limit)
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': {'statement_line_ids': bank_stmt_lines.ids, 'company_ids': self.mapped('company_id').ids},
        }
