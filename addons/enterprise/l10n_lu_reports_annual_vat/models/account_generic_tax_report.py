# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, tools
from odoo.exceptions import UserError

class AccountGenericTaxReport(models.AbstractModel):
    _inherit = "account.generic.tax.report"

    def _get_lu_electronic_report_values(self, options):
        lu_template_values = super()._get_lu_electronic_report_values(options)
        # The following values are set to 0 as they are not necessarily used in the report
        # But users should be able to see them in the xml file of the report
        values = {
	            code: {'value': 0, 'field_type': field_type}
	            for code, field_type in [('042', 'float'), ('418', 'number'), ('416', 'float'), ('417', 'float'), ('453', 'number'), ('451', 'float'), ('452', 'float')]
	        }

        lu_template_values['forms'][0]['field_values'].update(
            {**lu_template_values['forms'][0]['field_values'], **values}
        )

        return lu_template_values
