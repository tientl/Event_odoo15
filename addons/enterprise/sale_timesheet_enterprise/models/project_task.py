# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.sale_timesheet_enterprise.models.sale import DEFAULT_INVOICED_TIMESHEET


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def read(self, fields=None, load='_classic_read'):
        """ Override read method to filter timesheets in the task(s) is the user is portal user
            and the sale.invoiced_timesheet configuration is set to 'approved'
            Then we need to give the id of timesheets which is validated.
        """
        result = super().read(fields=fields, load=load)
        if fields and 'timesheet_ids' in fields and self.env.user.has_group('base.group_portal'):
            # We need to check if configuration
            param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
            if param_invoiced_timesheet == 'approved':
                timesheets_read_group = self.env['account.analytic.line'].read_group(
                    [('task_id', 'in', self.ids), ('validated', '=', True)],
                    ['ids:array_agg(id)', 'task_id'],
                    ['task_id'],
                )
                timesheets_dict = {res['task_id'][0]: res['ids'] for res in timesheets_read_group}
                for record_read in result:
                    record_read['timesheet_ids'] = timesheets_dict.get(record_read['id'], [])
        return result
