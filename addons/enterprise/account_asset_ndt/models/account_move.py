# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _auto_create_asset(self):
        assets = super()._auto_create_asset()
        for asset in assets:
            asset._post_non_deductible_tax_value()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    non_deductible_tax_value = fields.Monetary(compute='_compute_non_deductible_tax_value', currency_field='company_currency_id')

    @api.depends('tax_ids.invoice_repartition_line_ids')
    def _compute_non_deductible_tax_value(self):
        """ Handle the specific case of non deductible taxes,
        such as "50% Non Déductible - Frais de voiture (Prix Excl.)" in Belgium.
        """
        non_deductible_tax_ids = self.tax_ids.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == 'tax' and not line.use_in_tax_closing
        ).tax_id

        res = {}
        if non_deductible_tax_ids:
            domain = [('move_id', 'in', self.move_id.ids)]
            tax_details_query, tax_details_params = self._get_query_tax_details_from_domain(domain)

            self.flush(self._fields)
            self._cr.execute(f'''
                SELECT
                    tdq.base_line_id,
                    SUM(tdq.tax_amount_currency)
                FROM ({tax_details_query}) AS tdq
                JOIN account_move_line aml ON aml.id = tdq.tax_line_id
                JOIN account_tax_repartition_line trl ON trl.id = tdq.tax_repartition_line_id
                WHERE tdq.base_line_id IN %s
                AND trl.use_in_tax_closing IS FALSE
                GROUP BY tdq.base_line_id
            ''', tax_details_params + [tuple(self.ids)])

            res = {row['base_line_id']: row['sum'] for row in self._cr.dictfetchall()}

        for record in self:
            record.non_deductible_tax_value = res.get(record._origin.id, 0.0)
