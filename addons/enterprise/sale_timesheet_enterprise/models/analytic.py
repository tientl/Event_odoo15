# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression
from odoo.addons.sale_timesheet_enterprise.models.sale import DEFAULT_INVOICED_TIMESHEET


class AnalyticLine(models.Model):

    _inherit = 'account.analytic.line'

    def _get_adjust_grid_domain(self, column_value):
        """ Don't adjust already invoiced timesheet """
        domain = super(AnalyticLine, self)._get_adjust_grid_domain(column_value)
        return expression.AND([domain, [('timesheet_invoice_id', '=', False)]])

    def _get_last_timesheet_domain(self):
        """ Do not update the timesheet which are already linked with invoice """
        domain = super()._get_last_timesheet_domain()
        return expression.AND([domain, [
            '|', ('timesheet_invoice_id', '=', False),
            ('timesheet_invoice_id.state', '=', 'cancel')
        ]])

    def _timesheet_get_portal_domain(self):
        domain = super(AnalyticLine, self)._timesheet_get_portal_domain()
        param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        if param_invoiced_timesheet == 'approved':
            domain = expression.AND([domain, [('validated', '=', True)]])
        return domain

    def _compute_can_validate(self):
        # Prevent `user_can_validate` from being true if the line is validated and the SO aswell
        billed_lines = self.filtered(lambda l: l.validated and not l._is_not_billed())
        for line in billed_lines:
            line.user_can_validate = False
        self -= billed_lines
        return super()._compute_can_validate()

    def action_invalidate_timesheet(self):
        invoice_validated_timesheets = self.filtered(lambda l: not l._is_not_billed())
        self -= invoice_validated_timesheets
        # Errors are handled in the parent if there are no lines left
        return super(AnalyticLine, self).action_invalidate_timesheet()
