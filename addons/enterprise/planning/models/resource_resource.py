# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime
from random import randint
import pytz

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.resource.models.resource import Intervals

class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _default_color(self):
        return randint(1, 11)

    color = fields.Integer(default=_default_color)
    employee_id = fields.One2many('hr.employee', 'resource_id', domain="[('company_id', '=', company_id)]")
    avatar_128 = fields.Image(compute='_compute_avatar_128')

    @api.depends('employee_id')
    def _compute_avatar_128(self):
        for resource in self:
            employees = resource.with_context(active_test=False).employee_id
            resource.avatar_128 = employees[0].avatar_128 if employees else False

    def get_formview_id(self, access_uid=None):
        if self.env.context.get('from_planning'):
            return self.env.ref('planning.resource_resource_with_employee_form_view_inherit', raise_if_not_found=False).id
        return super().get_formview_id(access_uid)

    @api.model_create_multi
    def create(self, vals_list):
        resources = super().create(vals_list)
        if self.env.context.get('from_planning'):
            create_vals = []
            for resource in resources.filtered(lambda r: r.resource_type == 'user'):
                create_vals.append({
                    'name': resource.name,
                    'resource_id': resource.id,
                })
            self.env['hr.employee'].sudo().with_context(from_planning=False).create(create_vals)
        return resources

    def name_get(self):
        result = []
        if self.env.context.get('planning_gantt_view'):
            for resource in self:
                employee = resource.employee_id
                if employee.job_title:
                    result.append((resource.id, "%s (%s)" % (employee.name, employee.job_title)))
                else:
                    result.append((resource.id, resource.name))
        else:
            result = super().name_get()
        return result

    # -----------------------------------------
    # Business Methods
    # -----------------------------------------

    def get_planning_hours_info(self, date_start_str, date_stop_str):
        date_start = datetime.strptime(date_start_str, DEFAULT_SERVER_DATETIME_FORMAT)
        date_stop = datetime.strptime(date_stop_str, DEFAULT_SERVER_DATETIME_FORMAT)
        planning_slots = self.env['planning.slot'].search([
            ('resource_id', 'in', self.ids),
            ('start_datetime', '<=', date_stop),
            ('end_datetime', '>=', date_start),
        ])
        planned_hours_mapped = defaultdict(float)
        start_utc = pytz.utc.localize(date_start)
        stop_utc = pytz.utc.localize(date_stop)
        work_intervals_batch = self.sudo()._get_work_intervals_batch(start_utc, stop_utc)
        for slot in planning_slots:
            if slot.start_datetime >= date_start and slot.end_datetime <= date_stop:
                planned_hours_mapped[slot.resource_id.id] += slot.allocated_hours
            else:
                # if the slot goes over the gantt period, compute the duration only within
                # the gantt period
                ratio = slot.allocated_percentage / 100.0 or 1
                start = max(start_utc, pytz.utc.localize(slot.start_datetime))
                end = min(stop_utc, pytz.utc.localize(slot.end_datetime))
                if slot.allocation_type == 'planning':
                    planned_hours_mapped[slot.resource_id.id] += (end - start).total_seconds() / 3600
                else:
                    # for forecast slots, use the conjonction between work intervals and slot.
                    interval = Intervals([(
                        start, end, self.env['resource.calendar.attendance']
                    )])
                    work_intervals = interval & work_intervals_batch[slot.resource_id.id]
                    planned_hours_mapped[slot.resource_id.id] += sum(
                        (stop - start).total_seconds() / 3600
                        for start, stop, _resource in work_intervals
                    ) * ratio
        # Compute employee work hours based on its work intervals.
        work_hours = {
            resource_id: sum(
                (stop - start).total_seconds() / 3600
                for start, stop, _resource in work_intervals
            )
            for resource_id, work_intervals in work_intervals_batch.items()
        }
        return {
            resource.id: {
                'planned_hours': planned_hours_mapped[resource.id],
                'work_hours': work_hours.get(resource.id, 0.0),
                'employee_id': resource.with_context(active_test=False).employee_id.id,
            }
            for resource in self
        }

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        """
            Returns a dict of dict with resource's id as first key and resource's calendar as secondary key
            The value is the validity interval of the calendar for the given resource.

            Here the validity interval for each calendar is the whole interval but it's meant to be overriden in further modules
            handling resource's employee contracts.
        """
        assert start.tzinfo and end.tzinfo
        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        default_calendar = default_company and default_company.resource_calendar_id or self.env.company.resource_calendar_id
        if not self:
            # if no resource, add the company resource calendar.
            calendars_within_period_per_resource[False][default_calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        for resource in self:
            calendar = resource.calendar_id or resource.company_id.resource_calendar_id or default_calendar
            calendars_within_period_per_resource[resource.id][calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        return calendars_within_period_per_resource

    def _get_work_intervals_batch(self, start, end):
        """
            Returns the work intervals of the resource following their calendars between ``start`` and ``end``

            This methods handle the eventuality of an resource having multiple resource calendars, see _get_calendars_validity_within_period method
            for further explanation.
        """
        assert start.tzinfo and end.tzinfo
        resource_calendar_validity_intervals = {}
        resource_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        work_intervals_per_resource = defaultdict(Intervals)

        resource_calendar_validity_intervals = self._get_calendars_validity_within_period(start, end)
        for resource_id in self:
            # For each resource, retrieve its calendar and their validity intervals
            for calendar in resource_calendar_validity_intervals[resource_id.id].keys():
                resource_per_calendar[calendar] |= resource_id
        for calendar in resource_per_calendar.keys():
            # For each calendar used by the resources, retrieve the work intervals for every resources using it
            work_intervals_batch = calendar._work_intervals_batch(start, end, resources=resource_per_calendar[calendar])
            for resource_id in resource_per_calendar[calendar]:
                # Make the conjonction between work intervals and calendar validity
                work_intervals_per_resource[resource_id.id] |= work_intervals_batch[resource_id.id] & resource_calendar_validity_intervals[resource_id.id][calendar]

        return work_intervals_per_resource
