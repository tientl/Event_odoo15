# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime
import pytz

from odoo import fields, models
from odoo.addons.resource.models.resource import Intervals

class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        assert start.tzinfo and end.tzinfo
        if not self:
            return super()._get_calendars_validity_within_period(start, end, default_company=default_company)
        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        resource_without_contract = self.filtered(lambda r: not r.employee_id or r.employee_id.employee_type not in ['employee', 'student'])
        resource_with_contract = self - resource_without_contract
        if resource_with_contract:
            date_start = fields.Date.to_date(start)
            date_end = fields.Date.to_date(end)
            contracts = resource_with_contract.employee_id._get_contracts(
                date_start, date_end, states=['open', 'draft']
            ).filtered(lambda c: c.state == 'open' or c.kanban_state == 'done')
            for contract in contracts:
                calendars_within_period_per_resource[contract.employee_id.resource_id.id][contract.resource_calendar_id] |= Intervals([(
                    pytz.utc.localize(datetime.combine(contract.date_start, datetime.min.time())) if contract.date_start > date_start else start,
                    pytz.utc.localize(datetime.combine(contract.date_end, datetime.max.time())) if contract.date_end and contract.date_end < date_end else end,
                    self.env['resource.calendar.attendance']
                )])
        calendars_within_period_per_resource.update(
            super(ResourceResource, resource_without_contract)._get_calendars_validity_within_period(start, end, default_company=default_company)
        )
        return calendars_within_period_per_resource
