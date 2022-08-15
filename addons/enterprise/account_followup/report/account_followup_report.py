# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class AccountFollowUpReport(models.AbstractModel):
    _name = 'report.account_followup.report_followup_print_all'
    _description = 'Account Follow-up Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        partners = self.env['res.partner'].browse(docids)

        qr_code_urls = {}
        for partner in partners:
            for invoice in partner.unpaid_invoices:
                if invoice.display_qr_code:
                    new_code_url = invoice.generate_qr_code()
                    if new_code_url:
                        qr_code_urls[invoice.id] = new_code_url

        return {
            'docs': partners,
            'qr_code_urls': qr_code_urls,
        }
