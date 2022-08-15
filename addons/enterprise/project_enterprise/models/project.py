# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import utc
from collections import defaultdict
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.resource.models.resource import Intervals


DATE_AUTO_SHIFT_CONTEXT_KEY = 'date_auto_shift'
DATE_AUTO_SHIFT_DIRECTION_CONTEXT_KEY = 'date_auto_shift_direction'
DATE_AUTO_SHIFT_IDS_TO_EXCLUDE_KEY = 'date_auto_shift_ids_to_exclude'
DATE_AUTO_SHIFT_FORWARD = 'forward'
DATE_AUTO_SHIFT_BACKWARD = 'backward'
DATE_AUTO_SHIFT_BOTH_DIRECTIONS = 'both'

PROJECT_TASK_WRITABLE_FIELDS = {
    'planned_date_begin',
    'planned_date_end',
}

class Task(models.Model):
    _inherit = "project.task"

    planned_date_begin = fields.Datetime("Start date", tracking=True, task_dependency_tracking=True)
    planned_date_end = fields.Datetime("End date", tracking=True, task_dependency_tracking=True)
    partner_mobile = fields.Char(related='partner_id.mobile', readonly=False)
    partner_zip = fields.Char(related='partner_id.zip', readonly=False)
    partner_street = fields.Char(related='partner_id.street', readonly=False)
    project_color = fields.Integer('Project color', related='project_id.color')

    # Task Dependencies fields
    display_warning_dependency_in_gantt = fields.Boolean(compute="_compute_display_warning_dependency_in_gantt")
    planning_overlap = fields.Integer(compute='_compute_planning_overlap', search='_search_planning_overlap')

    # User names in popovers
    user_names = fields.Char(compute='_compute_user_names')

    _sql_constraints = [
        ('planned_dates_check', "CHECK ((planned_date_begin <= planned_date_end))", "The planned start date must be prior to the planned end date."),
    ]

    @property
    def SELF_WRITABLE_FIELDS(self):
        return super().SELF_WRITABLE_FIELDS | PROJECT_TASK_WRITABLE_FIELDS

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        planned_date_begin = result.get('planned_date_begin', False)
        planned_date_end = result.get('planned_date_end', False)
        if planned_date_begin and planned_date_end and not self.env.context.get('fsm_mode', False):
            user_id = result.get('user_id', None)
            planned_date_begin, planned_date_end = self._calculate_planned_dates(planned_date_begin, planned_date_end, user_id)
            result.update(planned_date_begin=planned_date_begin, planned_date_end=planned_date_end)
        return result

    @api.depends('stage_id')
    def _compute_display_warning_dependency_in_gantt(self):
        for task in self:
            task.display_warning_dependency_in_gantt = not (task.stage_id.is_closed or task.stage_id.fold)

    @api.depends('planned_date_begin', 'planned_date_end', 'user_ids')
    def _compute_planning_overlap(self):
        if self.ids:
            query = """
                SELECT
                    T1.id, COUNT(T2.id)
                FROM
                    (
                        SELECT
                            T.id as id,
                            T.project_id,
                            T.planned_date_begin as planned_date_begin,
                            T.planned_date_end as planned_date_end,
                            T.active as active
                        FROM project_task T
                        LEFT OUTER JOIN project_project P ON P.id = T.project_id
                        WHERE T.id IN %s
                            AND T.active = 't'
                            AND T.planned_date_begin IS NOT NULL
                            AND T.planned_date_end IS NOT NULL
                            AND T.project_id IS NOT NULL
                    ) T1
                INNER JOIN project_task_user_rel U1
                    ON T1.id = U1.task_id
                INNER JOIN project_task T2
                    ON T1.id != T2.id
                        AND T2.active = 't'
                        AND T2.planned_date_begin IS NOT NULL
                        AND T2.planned_date_end IS NOT NULL
                        AND T2.project_id IS NOT NULL
                        AND (T1.planned_date_begin::TIMESTAMP, T1.planned_date_end::TIMESTAMP)
                            OVERLAPS (T2.planned_date_begin::TIMESTAMP, T2.planned_date_end::TIMESTAMP)
                INNER JOIN project_task_user_rel U2
                    ON T2.id = U2.task_id
                    AND U2.user_id = U1.user_id
                GROUP BY T1.id
            """
            self.env.cr.execute(query, (tuple(self.ids),))
            raw_data = self.env.cr.dictfetchall()
            overlap_mapping = dict(map(lambda d: d.values(), raw_data))
            for task in self:
                task.planning_overlap = overlap_mapping.get(task.id, 0)
        else:
            self.planning_overlap = False

    @api.model
    def _search_planning_overlap(self, operator, value):
        if operator not in ['=', '>'] or not isinstance(value, int) or value != 0:
            raise NotImplementedError(_('Operation not supported, you should always compare planning_overlap to 0 value with = or > operator.'))

        query = """
            SELECT T1.id
            FROM project_task T1
            INNER JOIN project_task T2 ON T1.id <> T2.id
            INNER JOIN project_task_user_rel U1 ON T1.id = U1.task_id
            INNER JOIN project_task_user_rel U2 ON T2.id = U2.task_id
                AND U1.user_id = U2.user_id
            WHERE
                T1.planned_date_begin < T2.planned_date_end
                AND T1.planned_date_end > T2.planned_date_begin
                AND T1.planned_date_begin IS NOT NULL
                AND T1.planned_date_end IS NOT NULL
                AND T1.active = 't'
                AND T1.project_id IS NOT NULL
                AND T2.planned_date_begin IS NOT NULL
                AND T2.planned_date_end IS NOT NULL
                AND T2.project_id IS NOT NULL
                AND T2.active = 't'
        """
        operator_new = (operator == ">") and "inselect" or "not inselect"
        return [('id', operator_new, (query, ()))]

    def _compute_user_names(self):
        for task in self:
            task.user_names = ', '.join(task.user_ids.mapped('name'))

    @api.model
    def _calculate_planned_dates(self, date_start, date_stop, user_id=None, calendar=None):
        if not (date_start and date_stop):
            raise UserError('One parameter is missing to use this method. You should give a start and end dates.')
        start, stop = date_start, date_stop
        if isinstance(start, str):
            start = fields.Datetime.from_string(start)
        if isinstance(stop, str):
            stop = fields.Datetime.from_string(stop)

        if not calendar:
            user = self.env['res.users'].sudo().browse(user_id) if user_id and user_id != self.env.user.id else self.env.user
            calendar = user.resource_calendar_id or self.env.company.resource_calendar_id
            if not calendar:  # Then we stop and return the dates given in parameter.
                return date_start, date_stop

        if not start.tzinfo:
            start = start.replace(tzinfo=utc)
        if not stop.tzinfo:
            stop = stop.replace(tzinfo=utc)

        intervals = calendar._work_intervals_batch(start, stop)[False]
        if not intervals:  # Then we stop and return the dates given in parameter
            return date_start, date_stop
        list_intervals = [(start, stop) for start, stop, records in intervals]  # Convert intervals in interval list
        start = list_intervals[0][0].astimezone(utc).replace(tzinfo=None)  # We take the first date in the interval list
        stop = list_intervals[-1][1].astimezone(utc).replace(tzinfo=None)  # We take the last date in the interval list
        return start, stop

    def _is_auto_shift_candidate(self):
        """
        Informs whether a task is a candidate for the auto shift feature.
        :return: True if the task is a candidate for the auto shift feature.
        :rtype: bool
        """
        self.ensure_one()
        task_is_done = self.stage_id.fold or self.stage_id.is_closed
        return self.project_id and self.project_id.allow_task_dependencies and not task_is_done and \
               self.planned_date_begin and self.planned_date_end and self.planned_date_begin > datetime.now()

    def _get_tasks_by_resource_calendar_dict(self):
        """
            Returns a dict of:
                key = 'resource.calendar'
                value = recordset of 'project.task'
        """
        default_calendar = self.env.company.resource_calendar_id

        calendar_by_user_dict = {  # key: user_id, value: resource.calendar instance
            user.id:
                user.resource_calendar_id or default_calendar
            for user in self.mapped('user_ids')
        }

        tasks_by_resource_calendar_dict = defaultdict(
            lambda: self.env[self._name])  # key = resource_calendar instance, value = tasks
        for task in self:
            if len(task.user_ids) == 1:
                tasks_by_resource_calendar_dict[calendar_by_user_dict[task.user_ids.id]] |= task
            else:
                tasks_by_resource_calendar_dict[default_calendar] |= task

        return tasks_by_resource_calendar_dict

    def _get_calendars_and_resources_key(self):
        self.ensure_one()
        return self.company_id.resource_calendar_id or self.project_id.company_id.resource_calendar_id

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
        calendar_by_task_dict = {
            self._get_calendars_and_resources_key(): [
                {
                    'date_start': datetime(1, 1, 1, tzinfo=utc),
                    'date_end': datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=utc),
                    'calendar_id': self.company_id.resource_calendar_id or self.project_id.company_id.resource_calendar_id,
                    'resource_id': False,
                }
            ]
        }
        return calendar_by_task_dict

    def write(self, vals):
        compute_default_planned_dates = None
        if not self.env.context.get('fsm_mode', False) and 'planned_date_begin' in vals and 'planned_date_end' in vals:  # if fsm_mode=True then the processing in industry_fsm module is done for these dates.
            compute_default_planned_dates = self.filtered(lambda task: not task.planned_date_begin and not task.planned_date_end)

        res = super().write(vals)

        if compute_default_planned_dates:
            # Take the default planned dates
            planned_date_begin = vals.get('planned_date_begin', False)
            planned_date_end = vals.get('planned_date_end', False)

            # Then sort the tasks by resource_calendar and finally compute the planned dates
            tasks_by_resource_calendar_dict = compute_default_planned_dates._get_tasks_by_resource_calendar_dict()
            for (calendar, tasks) in tasks_by_resource_calendar_dict.items():
                date_start, date_stop = self._calculate_planned_dates(planned_date_begin, planned_date_end, calendar=calendar)
                tasks.write({
                    'planned_date_begin': date_start,
                    'planned_date_end': date_stop,
                })

        date_auto_shift = self.env.context.get(DATE_AUTO_SHIFT_CONTEXT_KEY, False)
        write_planned_date_fields = any(field for field in ['planned_date_begin', 'planned_date_end'] if field in vals)
        if date_auto_shift and write_planned_date_fields:
            self._action_auto_shift()

        return res

    def _write_planned_dates_if_in_future(self, new_planned_date_begin, new_planned_date_end):
        self.ensure_one()
        if new_planned_date_begin and new_planned_date_end and new_planned_date_begin >= datetime.now(tz=utc):
            context_update = {
                DATE_AUTO_SHIFT_IDS_TO_EXCLUDE_KEY: self.env.context.get(DATE_AUTO_SHIFT_IDS_TO_EXCLUDE_KEY, set()) | {self.id}
            }
            self.with_context(**context_update).write({
                'planned_date_begin': new_planned_date_begin.astimezone(utc).replace(tzinfo=None),
                'planned_date_end': new_planned_date_end.astimezone(utc).replace(tzinfo=None),
            })
            return True

        return False

    @api.model
    def _get_cache_info(self, key, task_calendars, intervals_cache, date_time, search_forward):
        match_index = 0
        for index, item in enumerate(task_calendars[key] if search_forward else reversed(task_calendars[key]), 1):
            if item['date_start'] <= date_time and date_time <= item['date_end']:
                match_index = index
                break

        cache_key = task_calendars[key][match_index - 1]['calendar_id'], task_calendars[key][match_index - 1]['resource_id']
        intervals_cache_entry = intervals_cache[cache_key]
        in_memory_start = intervals_cache_entry._items[0][0].astimezone(utc) if len(intervals_cache_entry) > 0 else \
                          datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=utc)
        in_memory_end = intervals_cache_entry._items[-1][1].astimezone(utc) if len(intervals_cache_entry) > 0 else \
                        datetime(1, 1, 1, tzinfo=utc)

        return intervals_cache_entry, in_memory_start, in_memory_end

    def _get_first_work_interval(self, intervals_cache, date_time, task_calendars, search_forward=True):
        """
        Finds and returns the first work interval for the provided calendar and resource that matches the date_time
        and search_forward criteria. A first search is made in the intervals_cache and if none is found, additional
        search are made in the database until a match is found.
        :param date_time: The date the work interval is searched for. If no exact match can be done, the closest is
                          returned.
        :param calendar: The calendar the work intervals are to be retrieved from.
        :param resource: The resource the work intervals are to be retrieved for.
        :param intervals_cache: The cached data that can be used prior to fetch data from the database.
                                A defaultdict (lambda: Intervals()) with keys of tuple(`resource.calendar`,
                                `resource.resource`).
        :param search_forward: The search direction.
                               Having search_forward truthy causes the search to be made chronologically, looking for
                               an interval that matches interval_start <= date_time < interval_end.
                               Having search_forward falsy causes the search to be made reverse chronologically, looking
                               for an interval that matches interval_start < date_time <= interval_end.
        :return: tuple (interval, intervals_cache). The closest interval that matches the search criteria and the
                 intervals_cache updated with the data fetched from the database if any.
        """
        self.ensure_one()

        key = self._get_calendars_and_resources_key()
        if key not in task_calendars:
            task_calendars = self._get_calendars_and_resources(date_time - relativedelta(months=1),
                                                               date_time + relativedelta(months=1))

        intervals_cache_entry, in_memory_start, in_memory_end = self._get_cache_info(key, task_calendars, intervals_cache, date_time, search_forward)

        assert date_time.tzinfo

        interval = Intervals()
        if (search_forward and in_memory_start <= date_time < in_memory_end) or \
                (not search_forward and in_memory_start < date_time <= in_memory_end):
            interval = self._get_interval(date_time, intervals_cache_entry, search_forward)
        else:
            search_extender = search_forward and 1 or -1
            if len(intervals_cache_entry) == 0:
                in_memory_start = in_memory_end = date_time
            else:
                if search_forward and date_time < in_memory_start:
                    search_extender = -1
                elif not search_forward and date_time > in_memory_end:
                    search_extender = 1

            while not interval:
                intervals = Intervals()
                interval_pool = Intervals()
                date_to_search = date_time + timedelta(weeks=search_extender)
                if date_to_search <= in_memory_start:
                    if (date_to_search < task_calendars[key][0]['date_start']):
                        new_task_calendars = self._get_calendars_and_resources(date_to_search,
                                                                               task_calendars[key][0]['date_start'])
                        task_calendars[key][0:0] = new_task_calendars[key]

                        intervals_cache_entry, in_memory_start, in_memory_end = self._get_cache_info(key, task_calendars,
                                                                                           intervals_cache, date_time,
                                                                                           search_forward)

                    for entry in filter(lambda calendar_interval: calendar_interval['date_start'] <= in_memory_start and calendar_interval['date_end'] >= date_to_search,
                                        task_calendars[key] if search_forward else reversed(task_calendars[key])):
                        new_interval = entry['calendar_id']._work_intervals_batch(max(date_to_search, entry['date_start']), min(in_memory_start, entry['date_end']), entry['resource_id'])[entry['resource_id'] and entry['resource_id'].id]
                        intervals |= new_interval
                        intervals_cache[entry['calendar_id'], entry['resource_id']] |= new_interval
                        interval_pool |= intervals_cache[entry['calendar_id'], entry['resource_id']]

                else:
                    if (date_to_search > task_calendars[key][-1]['date_end']):
                        new_task_calendars = self._get_calendars_and_resources(task_calendars[key][-1]['date_end'],
                                                                               date_to_search)
                        task_calendars[key].append(new_task_calendars[key])

                        intervals_cache_entry, in_memory_start, in_memory_end = self._get_cache_info(key, task_calendars,
                                                                                           intervals_cache, date_time,
                                                                                           search_forward)

                    for entry in filter(lambda calendar_interval: calendar_interval['date_start'] <= date_to_search and calendar_interval['date_end'] >= in_memory_end,
                                        task_calendars[key] if search_forward else reversed(task_calendars[key])):
                        new_interval = entry['calendar_id']._work_intervals_batch(max(in_memory_end, entry['date_start']), min(date_to_search, entry['date_end']), entry['resource_id'])[entry['resource_id'] and entry['resource_id'].id]
                        intervals |= new_interval
                        intervals_cache[entry['calendar_id'], entry['resource_id']] |= new_interval
                        interval_pool |= intervals_cache[entry['calendar_id'], entry['resource_id']]

                interval = self._get_interval(date_time, interval_pool, search_forward)
                search_extender += search_extender

        return interval, intervals_cache, task_calendars

    @api.model
    def _get_interval(self, date_time, intervals, search_forward):
        """
        Finds and returns the first work interval for the provided date_time and search_forward criteria.
        :param date_time: The date the work interval is searched for. If no exact match can be done, the closest is
                          returned.
        :param intervals:
        :param search_forward: The search direction.
                               Having search_forward truthy causes the search to be made chronologically, looking for
                               an interval that matches interval_end > date_time. Having search_forward falsy causes
                               the search to be made reverse chronologically, looking for an interval that matches
                               interval_start < date_time.
        :return: tuple ``(start, stop, records)`` where ``records`` is a recordset.
        """
        if not search_forward:
            intervals = reversed(intervals)
        for interval in intervals:
            if (search_forward and interval[1] > date_time) or (not search_forward and interval[0] < date_time):
                return interval
        return ()

    @api.model
    def _get_date_for_planned_hours(self, intervals, planned_hours_target, planned_hours, searched_date,
                                    search_forward=True):
        """
        Browse the intervals in order to find the date that meets the planned_hours_target constraint and returns
        the planned_hours and the search_date corresponding to it. If not possible, returns the planned_hours the closest
        to the planned_hours_target as well as the corresponding search_date.
        :param intervals: The intervals to browse.
        :param planned_hours_target: The planned_hours target.
        :param planned_hours: The current value of planned_hours.
        :param searched_date: The current value of the search_date.
        :param search_forward: The search direction. Having search_forward truthy causes the search to be made chronologically.
                               Having search_forward falsy causes the search to be made reverse chronologically.
        :return: tuple ``(planned_hours, searched_date)``.
        """
        enumeration = search_forward and intervals or reversed(intervals)
        for interval in enumeration:
            delta = 0.0
            if search_forward:
                if interval[1] > searched_date:
                    target_date = max(searched_date, interval[0])
                    delta = min(planned_hours_target - planned_hours, interval[1] - target_date)
                    searched_date = target_date + delta
            else:
                if interval[0] < searched_date:
                    target_date = min(searched_date, interval[1])
                    delta = min(planned_hours_target - planned_hours, target_date - interval[0])
                    searched_date = target_date - delta

            if delta:
                planned_hours += delta

            if planned_hours >= planned_hours_target:
                break
        return planned_hours, searched_date

    def _action_auto_shift(self):
        # Recordset of all the tasks that are 'linked' to the current task and that would require an update in
        # their planned_date fields.
        tasks_to_auto_shift, mapped_depend_on, mapped_dependent = self._action_auto_shift_get_candidates()
        if not tasks_to_auto_shift:
            return

        # # We will perform the search per calendar in order to increase performance in case multiple records
        # # share the same calendar.
        # tasks_by_resource_calendar_dict = tasks_to_auto_shift._get_tasks_by_resource_calendar_dict()

        # The calendar intervals that will be kept during the process of all the tasks that
        # share the calendar in order to limit DB queries.
        intervals_cache = defaultdict(Intervals)

        for task in tasks_to_auto_shift:
            new_planned_date_begin, new_planned_date_end = False, False
            if task.planned_hours:
                new_planned_date_begin, new_planned_date_end, intervals_cache = task.sudo()._action_auto_shift_with_planned_hours(
                    mapped_dependent, mapped_depend_on, intervals_cache)
            else:
                new_planned_date_begin, new_planned_date_end, intervals_cache = task.sudo()._action_auto_shift_without_planned_hours(
                    mapped_dependent, mapped_depend_on, intervals_cache)

            task._write_planned_dates_if_in_future(new_planned_date_begin, new_planned_date_end)

    def _action_auto_shift_get_candidates(self):
        """
        Gets the tasks that are candidates for the auto shift feature, together with the two dictionaries
        mapped_depend_on and mapped_dependent that provide access to the task that trigger the auto shift.
        The priority is put on depend_on task, meaning that if a task is a candidate for the auto shift feature from
        both a task it depends on and a dependent task, the only move considered will be the one due to its dependent
        overlapping task (meaning that the task will be planned earlier, which tends to reduce the critical path).
        :return: tuple ``(tasks_to_auto_shift, mapped_depend_on, mapped_dependent)``.
        """
        # Mapping of tasks with the related tasks that are depending on it
        mapped_depend_on = defaultdict(lambda: self.env['project.task'])
        # Mapping of tasks with the related tasks dependent tasks
        mapped_dependent = defaultdict(lambda: self.env['project.task'])
        tasks_to_auto_shift = self.env['project.task']

        auto_shift_direction = self.env.context.get(DATE_AUTO_SHIFT_DIRECTION_CONTEXT_KEY, 'none')
        auto_shift_forward = auto_shift_direction in (DATE_AUTO_SHIFT_FORWARD, DATE_AUTO_SHIFT_BOTH_DIRECTIONS)
        auto_shift_backward = auto_shift_direction in (DATE_AUTO_SHIFT_BACKWARD, DATE_AUTO_SHIFT_BOTH_DIRECTIONS)

        auto_shift_candidate_ids = set(self.ids)
        auto_shift_candidate_ids.update(self.depend_on_ids.ids)
        auto_shift_candidate_ids.update(self.dependent_ids.ids)
        # The goal is to automatically exclude ids from the depend_on_ids and dependent_ids but not the self.ids.
        # But the call on _is_auto_shift_candidate will still ensure that the self.ids are candidates
        date_auto_shift_ids_to_exclude = self.env.context.get(DATE_AUTO_SHIFT_IDS_TO_EXCLUDE_KEY, set()) - set(self.ids)
        auto_shift_candidates = self.env['project.task'].browse(auto_shift_candidate_ids - date_auto_shift_ids_to_exclude)
        auto_shift_candidate_set = {auto_shift_candidate.id for auto_shift_candidate in auto_shift_candidates if auto_shift_candidate._is_auto_shift_candidate()}

        for task in self:
            # We provide priority to depend_on over dependent as we try to shorten the critical path
            if task.id in auto_shift_candidate_set:
                for depend_on_task in task.depend_on_ids:
                    if depend_on_task.id in auto_shift_candidate_set and depend_on_task.project_id == task.project_id \
                            and (depend_on_task.planned_date_end > task.planned_date_begin or auto_shift_forward):
                        if not mapped_depend_on[depend_on_task] or \
                                mapped_depend_on[depend_on_task].planned_date_begin > task.planned_date_begin:
                            if mapped_dependent[depend_on_task]:
                                del mapped_dependent[depend_on_task]
                            mapped_depend_on[depend_on_task] = task
                            tasks_to_auto_shift |= depend_on_task
                for dependent_task in task.dependent_ids:
                    if dependent_task.id in auto_shift_candidate_set and dependent_task.project_id == task.project_id \
                            and (dependent_task.planned_date_begin < task.planned_date_end or auto_shift_backward):
                        if (not mapped_depend_on[dependent_task] and not mapped_dependent[dependent_task]) or \
                                mapped_dependent[dependent_task].planned_date_end < task.planned_date_end:
                            mapped_dependent[dependent_task] = task
                            tasks_to_auto_shift |= dependent_task
        return tasks_to_auto_shift, mapped_depend_on, mapped_dependent

    def _action_auto_shift_with_planned_hours(self, mapped_dependent, mapped_depend_on, intervals_cache):

        # If planned_hours are used, we will modify the planned_date fields values in order to
        # preserve the planned_hours, taking into account the work intervals either of the user
        # if available or the one of the company if not
        self.ensure_one()
        task = self
        key = self._get_calendars_and_resources_key()

        new_planned_date_begin, new_planned_date_end = False, False

        planned_hours = timedelta(hours=task.planned_hours)

        task_calendars = {}

        if mapped_dependent[task]:
            # Case 1: Move forward
            # Here task is a task that the depends on the written task so we need to schedule it after
            # to this task planned_date_end

            search_forward = True
            date_candidate = mapped_dependent[task].planned_date_end.replace(tzinfo=utc)
            # We arbitrary get the calendars info for the period from a month before the date and a month after.
            task_calendars = self._get_calendars_and_resources(date_candidate - relativedelta(months=1),
                                                               date_candidate + relativedelta(months=1))
            planned_date_begin_interval, intervals_cache, task_calendars = self._get_first_work_interval(intervals_cache,
                                                                                                         date_candidate,
                                                                                                         task_calendars)
            searched_date = new_planned_date_begin = max(date_candidate, planned_date_begin_interval[0])
        else:
            # Case 2: Move backward
            # Here task is a task that the written task depends on so we need to schedule it prior to
            # this task planned_date_begin

            search_forward = False
            date_candidate = mapped_depend_on[task].planned_date_begin.replace(tzinfo=utc)
            # We arbitrary get the calendars info for the period from a month before the date and a month after.
            task_calendars = self._get_calendars_and_resources(date_candidate - relativedelta(months=1),
                                                               date_candidate + relativedelta(months=1))
            planned_date_end_interval, intervals_cache, task_calendars = self._get_first_work_interval(intervals_cache,
                                                                                                       date_candidate,
                                                                                                       task_calendars,
                                                                                                       search_forward=False)
            searched_date = new_planned_date_end = min(date_candidate, planned_date_end_interval[1])

        # Keeps track of the hours that have already been covered.
        new_task_hours = timedelta(hours=0.0)
        min_numb_of_weeks = 1
        first = defaultdict(lambda: True)
        iteration_counter = 0
        # If we can't reschedule the task within a year, we can consider that there is an issue.
        MAX_ITERATIONS = 52
        while new_task_hours < planned_hours:
            iteration_counter += 1

            if iteration_counter > MAX_ITERATIONS:
                # This should of course never happen. But if it does we will return False which will cause the
                # process to stop for this task dependency node (this one and its dependencies)
                new_planned_date_begin, new_planned_date_end = False, False
                break

            # Look for the missing intervals with min search of 1 week
            calendar_intervals_to_search = max(planned_hours - new_task_hours, timedelta(weeks=min_numb_of_weeks))

            if mapped_dependent[task]:
                # task is a task that the written task depends on so we need to schedule it prior to this task planned_date_begin
                start = searched_date
                stop = start + calendar_intervals_to_search
            else:
                # task is a task that the depends on the written task so we need to schedule it after to this task planned_date_end
                stop = searched_date
                start = stop - calendar_intervals_to_search

            # find every calendars between start and stop
            for calendar in (task_calendars[key] if search_forward else reversed(task_calendars[key])):
                if calendar['date_start'] <= stop and calendar['date_end'] >= start:
                    intervals_cache_entry = intervals_cache[calendar['calendar_id'], calendar['resource_id']]
                    calendar_intervals_start = intervals_cache_entry._items[0][0].astimezone(
                        utc) if len(intervals_cache_entry) > 0 else datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=utc)
                    calendar_intervals_end = intervals_cache_entry._items[-1][1].astimezone(
                        utc) if len(intervals_cache_entry) > 0 else datetime(1, 1, 1, tzinfo=utc)
                    calendar_interval = Intervals([(
                        calendar_intervals_start,
                        calendar_intervals_end,
                        self.env['resource.calendar.attendance'])])

                    task_interval = Intervals([
                        (max(min(start, calendar_intervals_end), calendar['date_start']),
                         min(max(stop, calendar_intervals_start), calendar['date_end']),
                         self.env['resource.calendar.attendance'])
                    ])

                    search_intervals = task_interval - calendar_interval

                    if not search_intervals or first[intervals_cache_entry]:
                        first[intervals_cache_entry] = False
                        # Look into the calendar intervals that have already been retrieved
                        new_task_hours, searched_date = self._get_date_for_planned_hours(intervals_cache_entry, planned_hours,
                                                                                         new_task_hours, searched_date,
                                                                                         search_forward)

                    else:
                        for search_interval in search_intervals:
                            intervals = calendar['calendar_id']._work_intervals_batch(search_interval[0], search_interval[1], calendar['resource_id'])[calendar['resource_id'] and calendar['resource_id'].id]
                            if not intervals:
                                min_numb_of_weeks += 1
                                break
                            else:
                                min_numb_of_weeks = 1

                            new_task_hours, searched_date = self._get_date_for_planned_hours(intervals, planned_hours,
                                                                                             new_task_hours,
                                                                                             searched_date,
                                                                                             search_forward)

                            intervals_cache_entry |= intervals

                if new_task_hours == planned_hours:
                    break

        if mapped_dependent[task]:
            new_planned_date_end = searched_date
        else:
            new_planned_date_begin = searched_date

        return new_planned_date_begin, new_planned_date_end, intervals_cache

    def _action_auto_shift_without_planned_hours(self, mapped_dependent, mapped_depend_on, intervals_cache):
        # Checks planned_hours is covered otherwise add
        self.ensure_one()
        task = self

        if mapped_dependent[task]:
            # Case 1: Move forward
            # Here task is a task that the depends on the written task so we need to schedule it after
            # to this task planned_date_end

            date_candidate = mapped_dependent[task].planned_date_end.replace(tzinfo=utc)
            # We arbitrary get the calendars info for the period from a month before the date and a month after.
            task_calendars = self._get_calendars_and_resources(date_candidate - relativedelta(months=1),
                                                               date_candidate + relativedelta(months=1))
            planned_date_begin_interval, intervals_cache, task_calendars = self._get_first_work_interval(intervals_cache,
                                                                                                         date_candidate,
                                                                                                         task_calendars)
            new_planned_date_begin = max(date_candidate, planned_date_begin_interval[0])
            new_planned_date_end = new_planned_date_begin + (
                    task.planned_date_end - task.planned_date_begin)
        else:
            # Case 2: Move backward
            # Here task is a task that the written task depends on so we need to schedule it prior to
            # this task planned_date_begin

            date_candidate = mapped_depend_on[task].planned_date_begin.replace(tzinfo=utc)
            # We arbitrary get the calendars info for the period from a month before the date and a month after.
            task_calendars = self._get_calendars_and_resources(date_candidate - relativedelta(months=1),
                                                               date_candidate + relativedelta(months=1))
            planned_date_end_interval, intervals_cache, task_calendars = self._get_first_work_interval(intervals_cache,
                                                                                                       date_candidate,
                                                                                                       task_calendars,
                                                                                                       search_forward=False)
            new_planned_date_end = min(date_candidate, planned_date_end_interval[1])
            new_planned_date_begin = new_planned_date_end - (
                task.planned_date_end - task.planned_date_begin)

        return new_planned_date_begin, new_planned_date_end, intervals_cache

    def _get_task_overlap_domain(self):
        domain_mapping = {}
        for task in self:
            domain_mapping[task.id] = [
                '&',
                    '&',
                        ('user_ids', 'in', task.user_ids.ids),
                        '&',
                            ('planned_date_begin', '<', task.planned_date_end),
                            ('planned_date_end', '>', task.planned_date_begin),
                    ('project_id', '!=', False)
            ]
        return domain_mapping

    def action_fsm_view_overlapping_tasks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_view_all_task')
        domain = self._get_task_overlap_domain()[self.id]
        if 'views' in action:
            gantt_view = self.env.ref("project_enterprise.project_task_dependency_view_gantt")
            map_view = self.env.ref('project_enterprise.project_task_map_view_no_title')
            action['views'] = [(gantt_view.id, 'gantt'), (map_view.id, 'map')] + [(state, view) for state, view in action['views'] if view not in ['gantt', 'map']]
        action.update({
            'name': _('Overlapping Tasks'),
            'domain': domain,
            'context': {
                'fsm_mode': False,
                'task_nameget_with_hours': False,
                'initialDate': self.planned_date_begin,
            }
        })
        return action

    # ----------------------------------------------------
    # Gantt view
    # ----------------------------------------------------

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        user_ids = set()

        # function to "mark" top level rows concerning users
        # the propagation of that user_id to subrows is taken care of in the traverse function below
        def tag_user_rows(rows):
            for row in rows:
                group_bys = row.get('groupedBy')
                res_id = row.get('resId')
                if group_bys:
                    # if user_ids is the first grouping attribute
                    if group_bys[0] == 'user_ids' and res_id:
                        user_id = res_id
                        user_ids.add(user_id)
                        row['user_id'] = user_id
                    # else we recursively traverse the rows
                    elif 'user_ids' in group_bys:
                        tag_user_rows(row.get('rows'))

        tag_user_rows(rows)
        resources = self.env['res.users'].browse(user_ids).mapped('resource_ids').filtered(lambda r: r.company_id.id == self.env.company.id)
        # we reverse sort the resources by date to keep the first one created in the dictionary
        # to anticipate the case of a resource added later for the same employee and company
        user_resource_mapping = {resource.user_id.id: resource.id for resource in resources.sorted('create_date', True)}
        leaves_mapping = resources._get_unavailable_intervals(start_datetime, end_datetime)
        company_leaves = self.env.company.resource_calendar_id._unavailable_intervals(start_datetime.replace(tzinfo=utc), end_datetime.replace(tzinfo=utc))

        # function to recursively replace subrows with the ones returned by func
        def traverse(func, row):
            new_row = dict(row)
            if new_row.get('user_id'):
                for sub_row in new_row.get('rows'):
                    sub_row['user_id'] = new_row['user_id']
            new_row['rows'] = [traverse(func, row) for row in new_row.get('rows')]
            return func(new_row)

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unavailability(row):
            new_row = dict(row)
            user_id = row.get('user_id')
            calendar = company_leaves
            if user_id:
                resource_id = user_resource_mapping.get(user_id)
                if resource_id:
                    calendar = leaves_mapping[resource_id]

            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, calendar)
            new_row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return new_row

        return [traverse(inject_unavailability, row) for row in rows]

    @api.model
    def action_reschedule(self, direction, master_task_id, slave_task_id):
        # Mapping of tasks with the related tasks that are depending on it
        mapped_depend_on = defaultdict(lambda: self.env['project.task'])
        # Mapping of tasks with the related tasks dependent tasks
        mapped_dependent = defaultdict(lambda: self.env['project.task'])
        master_task, slave_task = self.env['project.task'].browse([master_task_id, slave_task_id])
        is_dependency_constraint_met = master_task.planned_date_end <= slave_task.planned_date_begin

        auto_shift_task_write_context = {
            DATE_AUTO_SHIFT_CONTEXT_KEY: True,
            DATE_AUTO_SHIFT_DIRECTION_CONTEXT_KEY: DATE_AUTO_SHIFT_BOTH_DIRECTIONS,
        }

        if direction == 'forward':
            auto_shift_task_write_context[DATE_AUTO_SHIFT_DIRECTION_CONTEXT_KEY] = DATE_AUTO_SHIFT_FORWARD
            if (is_dependency_constraint_met):
                trigger_task = master_task
                mapped_depend_on[trigger_task] = slave_task
            else:
                trigger_task = slave_task
                mapped_dependent[trigger_task] = master_task
        elif direction == 'backward':
            auto_shift_task_write_context[DATE_AUTO_SHIFT_DIRECTION_CONTEXT_KEY] = DATE_AUTO_SHIFT_BACKWARD
            if (is_dependency_constraint_met):
                trigger_task = slave_task
                mapped_dependent[trigger_task] = master_task
            else:
                trigger_task = master_task
                mapped_depend_on[trigger_task] = slave_task
        else:
            return False

        trigger_task = trigger_task.with_context(**auto_shift_task_write_context)
        intervals_cache = defaultdict(Intervals)

        if trigger_task.planned_hours:
            new_planned_date_begin, new_planned_date_end, intervals_cache = trigger_task.sudo()._action_auto_shift_with_planned_hours(
                mapped_dependent, mapped_depend_on, intervals_cache)
        else:
            new_planned_date_begin, new_planned_date_end, intervals_cache = trigger_task.sudo()._action_auto_shift_without_planned_hours(
                mapped_dependent, mapped_depend_on, intervals_cache)

        if not trigger_task._write_planned_dates_if_in_future(new_planned_date_begin, new_planned_date_end):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('You cannot reschedule tasks in the past. Please, change their dates manually instead.'),
                }
            }

        return True

    def _get_recurrence_start_date(self):
        self.ensure_one()
        return self.planned_date_begin or fields.Date.today()

    @api.depends('planned_date_begin')
    def _compute_recurrence_message(self):
        return super(Task, self)._compute_recurrence_message()

    def action_dependent_tasks(self):
        action = super().action_dependent_tasks()
        action['view_mode'] = 'tree,form,kanban,calendar,pivot,graph,gantt,activity,map'
        return action

    def action_recurring_tasks(self):
        action = super().action_recurring_tasks()
        action['view_mode'] = 'tree,form,kanban,calendar,pivot,graph,gantt,activity,map'
        return action
