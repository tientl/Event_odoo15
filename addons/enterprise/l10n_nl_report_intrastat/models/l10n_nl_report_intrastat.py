# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportL10nNLIntrastat(models.AbstractModel):
    _inherit = 'l10n.nl.report.intrastat'

    def _get_lines_query_params(self, options):
        # Note that if you made a change in this method, you probably will need to make a change also
        # in l10n_nl_report/l10n_nl_report_intrastat.py

        query = """
            SELECT l.partner_id, p.name, p.vat, country.code,
                   ROUND(SUM(CASE WHEN product_t.type != 'service' THEN l.credit - l.debit ELSE 0 END)) as amount_product,
                   ROUND(SUM(CASE WHEN product_t.type = 'service' THEN l.credit - l.debit ELSE 0 END)) as amount_service
            FROM account_move_line l
            LEFT JOIN res_partner p ON l.partner_id = p.id
            LEFT JOIN res_company company ON l.company_id = company.id
            LEFT JOIN res_partner comp_partner ON company.partner_id = comp_partner.id
            LEFT JOIN account_move move ON l.move_id = move.id
            LEFT JOIN res_country country ON move.intrastat_country_id = country.id
            LEFT JOIN res_country company_country ON comp_partner.country_id = company_country.id
            LEFT JOIN account_account_tag_account_move_line_rel line_tag on line_tag.account_move_line_id = l.id
            LEFT JOIN product_product product on product.id = l.product_id
            LEFT JOIN product_template product_t on product.product_tmpl_id = product_t.id
            WHERE line_tag.account_account_tag_id IN %(product_service_tags)s
            AND l.parent_state = 'posted'
            AND company_country.id != country.id
            AND country.intrastat = TRUE AND (country.code != 'GB' OR l.date < '2021-01-01')
            AND l.date >= %(date_from)s
            AND l.date <= %(date_to)s
            AND l.company_id IN %(company_ids)s
            GROUP BY l.partner_id, p.name, p.vat, country.code
            HAVING ROUND(SUM(CASE WHEN product_t.type != 'service' THEN l.credit - l.debit ELSE 0 END)) != 0
            OR ROUND(SUM(CASE WHEN product_t.type = 'service' THEN l.credit - l.debit ELSE 0 END)) != 0
            ORDER BY p.name
        """

        params = {
            'product_service_tags': tuple(self.env.ref('l10n_nl.tax_report_rub_3b').tag_ids.ids),
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'company_ids': tuple(self.env.companies.ids),
        }

        return {'query': query,
                'params': params,
                }
