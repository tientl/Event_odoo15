# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

class AccountFinancialReportLine(models.Model):
    _inherit = 'account.financial.html.report.line'

    @api.constrains('domain')
    def _validate_domain(self):
        # OVERRIDE from account_reports:
        # l10n_mx.trial.report uses some financial report lines to store
        # domains for account.account objects; so we need to change the
        # model these domains are validated against
        # TODO CLEAN ME: this is hacky and not at all the intended use of financial report lines
        regular_lines = self.env['account.financial.html.report.line']
        for record in self:
            if record.code and record.code.startswith('MX_COA_'):
                if not record.domain:
                    continue

                try:
                    domain = safe_eval(record.domain)
                    expression.expression(domain, self.env['account.account'])
                except Exception as e:
                    raise ValidationError(_("Error while validating the domain of line %s:\n%s") % (record.name, e))
            else:
                regular_lines += record

        super(AccountFinancialReportLine, regular_lines)._validate_domain()
