# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.osv import expression

class AccountDisallowedExpensesCategory(models.Model):
    _name = 'account.disallowed.expenses.category'
    _description = "Disallowed Expenses Category"

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the category without removing it.")
    rate_ids = fields.One2many('account.disallowed.expenses.rate', 'category_id', string='Rate')
    company_id = fields.Many2one('res.company')
    account_ids = fields.One2many('account.account', 'disallowed_expenses_category_id')

    _sql_constraints = [
        (
            'unique_code_in_country', 'UNIQUE(code, company_id)',
            'Disallowed expenses category code should be unique in each company.')
    ]

    def name_get(self):
        if not self.ids:
            return []
        sql = """
            SELECT category.id, rate.rate
            FROM account_disallowed_expenses_category category
            LEFT JOIN account_disallowed_expenses_rate rate ON rate.id = (
                SELECT rate.id
                FROM account_disallowed_expenses_rate rate
                WHERE rate.category_id = category.id
                ORDER BY date_from DESC
                LIMIT 1
            )
            WHERE category.id in %(ids)s
        """
        self.env.cr.execute(sql, {'ids': tuple(self.ids)})
        rates = dict(self.env.cr.fetchall())
        result = []
        for record in self:
            rate = rates.get(record.id) and ('%g%%' % rates[record.id]) or _('No Rate')
            name = '%s - %s (%s)' % (record.code, record.name, rate)
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def action_account_select(self):
        self.ensure_one()
        return {
            'name': _('Accounts'),
            'view_ids': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'res_model': 'account.account',
            'type': 'ir.actions.act_window',
            'context': {'search_default_disallowed_expenses_category_id': self.id},
        }


class AccountDisallowedExpensesRate(models.Model):
    _name = 'account.disallowed.expenses.rate'
    _description = "Disallowed Expenses Rate"
    _order = 'date_from desc'

    rate = fields.Float(string='Disallowed %', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    category_id = fields.Many2one('account.disallowed.expenses.category', string='Category', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
