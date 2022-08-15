# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from pytz import utc, timezone
from dateutil.relativedelta import relativedelta

from odoo import models, fields


class Task(models.Model):
    _inherit = "project.task"

    def _get_calendars_and_resources_key(self):
        self.ensure_one()
        if len(self.user_ids) == 1 and self.user_ids.employee_id.resource_calendar_id:
            return self.user_ids.employee_id
        else:
            return super(Task, self)._get_calendars_and_resources_key()

    def _get_calendars_and_resources(self, date_start, date_end):
        """
        Gets the calendars and resources (for instance to later get the work intervals for the provided date_start
        and date_end).
        :param date_start:
        :param date_end:
        :return: a dict of:
                    key = unique key identifying the calendar usage history (should be retrieved through the use of _get_calendars_and_resources_key)
                    value = list of tuple (date_start, date_end, 'resource.calendar', 'resource.resource') containing
                            the interval validity, the the calendar and the resource. The tuples are sorted
                            chronologically.
        :rtype: dict(dict)
        """
        self.ensure_one()

        if len(self.user_ids) != 1 or not self.user_ids.employee_id.resource_calendar_id:
            return super(Task, self)._get_calendars_and_resources(date_start, date_end)

        key = self._get_calendars_and_resources_key()
        calendar_by_task_dict = defaultdict(list)
        employee = self.user_ids.employee_id
        creation_date = employee.create_date.replace(tzinfo=utc)
        employee_company_tz = employee.company_id.resource_calendar_id.tz
        # Use company's resource calendar prior to employee creation.
        dict_entry = super(Task, self)._get_calendars_and_resources(date_start, date_end)[key]
        dict_entry[-1].update({
            'date_end': creation_date,
        })
        calendar_by_task_dict[key] += dict_entry
        # Use employee's resource calendar from employee creation.
        dict_entry = super(Task, self)._get_calendars_and_resources(date_start, date_end)[key]
        dict_entry[-1].update({
            'date_start': creation_date,
            'calendar_id': employee.resource_calendar_id,
            'resource_id': employee.resource_id,
        })
        calendar_by_task_dict[key] += dict_entry
        # If employee has left, use its resource calendar only up to the date he left and use the company's calendar after that date.
        departure_date = employee.departure_date
        if departure_date:
            departure_date = fields.Datetime.to_datetime(employee.departure_date).replace(tzinfo=timezone(employee_company_tz)) + \
                             relativedelta(days=1, microseconds=-1)
            calendar_by_task_dict[key][-1].update({
                'date_end': departure_date,
            })
            dict_entry = super(Task, self)._get_calendars_and_resources(date_start, date_end)[key]
            dict_entry[-1].update({
                'date_start': departure_date,
            })
            calendar_by_task_dict[key] += dict_entry
        return calendar_by_task_dict
