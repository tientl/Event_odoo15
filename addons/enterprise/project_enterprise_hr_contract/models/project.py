# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from pytz import timezone, utc
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields


class Task(models.Model):
    _inherit = "project.task"

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

        calendar_by_task_dict = defaultdict(list)
        contracts = self.env['hr.contract']
        if len(self.user_ids) == 1 and self.user_ids.employee_id:
            employee = self.user_ids.employee_id
            contracts = employee._get_contracts(date_start, date_end, ['open', 'close'])

        if not contracts:
            return super(Task, self)._get_calendars_and_resources(date_start, date_end)

        employee_company_tz = employee.company_id.resource_calendar_id.tz
        first_contract_datetime = fields.Datetime.to_datetime(contracts[0].date_start).replace(tzinfo=timezone(employee_company_tz))
        key = self._get_calendars_and_resources_key()

        # If some of the interval is not covered, fallback to super() behavior.
        if date_start < first_contract_datetime:
            fallback = super(Task, self)._get_calendars_and_resources(date_start, first_contract_datetime)[key]
            for entry in fallback:
                if entry['date_start'] < date_start:
                    if entry['date_end'] <= date_start:
                        continue
                    entry['date_start'] = date_start
                if entry['date_end'] > first_contract_datetime:
                    if entry['date_start'] >= first_contract_datetime:
                        continue
                    entry['date_end'] = first_contract_datetime
                calendar_by_task_dict[key].append(entry)

        last_contract_end_date = datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=utc)
        for contract in contracts:
            if contract.date_end:
                date_end = fields.Datetime.to_datetime(contract.date_end).replace(tzinfo=timezone(employee_company_tz)) + \
                           relativedelta(days=1, microseconds=-1)
            else:
                date_end = datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=utc)
            contract_dict_entry = {
                'date_start': fields.Datetime.to_datetime(contract.date_start).replace(tzinfo=timezone(employee_company_tz)),
                'date_end': date_end,
                'calendar_id': contract.resource_calendar_id,
                'resource_id': contract.employee_id.resource_id,
            }
            calendar_by_task_dict[key].append(contract_dict_entry)
            last_contract_end_date = date_end

        # If some of the interval is not covered, fallback to super() behavior.
        if last_contract_end_date < date_end:
            fallback = super(Task, self)._get_calendars_and_resources(last_contract_end_date, date_end)[key]
            for entry in fallback:
                if entry['date_start'] < last_contract_end_date:
                    if entry['date_end'] <= last_contract_end_date:
                        continue
                    entry['date_start'] = last_contract_end_date
                if entry['date_end'] > date_end:
                    if entry['date_start'] >= date_end:
                        continue
                    entry['date_end'] = date_end
                calendar_by_task_dict[key].append(entry)

        return calendar_by_task_dict
