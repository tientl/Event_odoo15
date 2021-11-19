# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    @property
    def filter_journals(self):
        if self.env.company.account_fiscal_country_id.code == 'IN':
            return True
        return super().filter_journals
