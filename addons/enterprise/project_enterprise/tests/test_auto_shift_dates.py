# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests.common import tagged
from .auto_shift_dates_common import AutoShiftDatesCommon, fake_now
from odoo.fields import Command


@freeze_time(fake_now)
@tagged('-at_install', 'post_install', 'auto_shift_dates')
class TestTaskDependencies(AutoShiftDatesCommon):

    def test_auto_shift_date_not_active(self):
        """
        This test purpose is to ensure that auto shift date feature is not active when it shouldn't:
        * When the context key date_auto_shift is not set to True (This context key being only used in the connector
          component integration in the Gantt Chart).
        * When the task has no project (either the moved task or the linked one (depend_on_ids or dependent_ids).
        * When the intervals defined by the planned_date_*(begin | end) fields of the tasks are not overlapping.
        * When the calculated planned_start_date is prior to now
        """

        def test_task_3_dates_unchanged(task_1_new_planned_dates, failed_message, domain_force=False, **context):
            task_1 = self.task_1.with_context(context) if domain_force else self.task_1.with_context(**context)
            task_1.write(task_1_new_planned_dates)
            self.assertEqual(self.task_3_planned_date_begin, self.task_3.planned_date_begin, failed_message)
            self.assertEqual(self.task_3_planned_date_end, self.task_3.planned_date_end)
            task_1.write({
                'planned_date_begin': self.task_1_planned_date_begin,
                'planned_date_end': self.task_1_planned_date_end,
            })

        self.task_4.depend_on_ids = [Command.clear()]

        # Checks that no date shift is made when the context key date_auto_shift is not True
        failed_message = "The auto shift date feature should not be enabled when the date_auto_shift context key is not present."
        test_task_3_dates_unchanged(self.task_1_date_auto_shift_trigger, failed_message, True, mail_create_nolog=True)

        # Checks that no date shift is made when the context key date_auto_shift is not True
        failed_message = "The auto shift date feature should not be enabled when the date_auto_shift context key is False."
        test_task_3_dates_unchanged(self.task_1_date_auto_shift_trigger, failed_message, date_auto_shift=False)

        # Checks that no date shift is made when the moved task has no project_id
        failed_message = "The auto shift date feature should not be triggered after having moved a task that does not have a project_id."
        project_id = self.task_1.project_id
        self.task_1.write({
            'project_id': False
        })
        test_task_3_dates_unchanged(self.task_1_date_auto_shift_trigger, failed_message)
        self.task_1.write({
            'project_id': project_id.id
        })

        # Checks that no date shift is made when the linked task has no project_id
        failed_message = "The auto shift date feature should not be triggered on tasks (depend_on_ids/dependent_ids) that do have a project_id."
        project_id = self.task_3.project_id
        self.task_3.write({
            'project_id': False
        })
        test_task_3_dates_unchanged(self.task_1_date_auto_shift_trigger, failed_message)
        self.task_3.write({
            'project_id': project_id.id
        })

        # Checks that no date shift is made when the new planned_date is prior to the current datetime.
        with freeze_time(self.task_1_no_date_auto_shift_trigger['planned_date_begin'] + relativedelta(weeks=1)):
            failed_message = "The auto shift date feature should not trigger any changes when the new planned_date is prior to the current datetime."
            test_task_3_dates_unchanged(self.task_1_date_auto_shift_trigger, failed_message)

    def test_auto_shift_dependent_task(self):
        """
        This test purpose is to ensure that a task B that depends on a task A is shifted forward, up to after
        A planned_date_end field value.
        """
        self.task_1.write(self.task_1_date_auto_shift_trigger)
        failed_message = "The auto shift date feature should move forward a dependent tasks."
        self.assertTrue(self.task_1.planned_date_end <= self.task_3.planned_date_begin, failed_message)

    def test_auto_shift_depend_on_task(self):
        """
        This test purpose is to ensure that a task A that depends on a task B is shifted backward, up to before
        B planned_date_start field value.
        """
        self.task_3.write(self.task_3_date_auto_shift_trigger)
        failed_message = "The auto shift date feature should move backward a task the moved task depends on."
        self.assertTrue(self.task_3.planned_date_begin >= self.task_1.planned_date_end, failed_message)

    def test_auto_shift_on_dependent_task_with_planned_hours(self):
        """
        This test purpose is to ensure that the task planned_date_fields (begin/end) are calculated accordingly to
        the planned_hours if any. So if a dependent task has to be move forward up to before an unavailable period of time
        and that its planned_hours is such that the planned_date_end would fall into that unavailable period, then the
        planned_date_end will be push forward after the unavailable period so that the planned_hours constraint is met.
        """
        self.task_1.write({
            'planned_date_begin': self.task_3_planned_date_begin,
            'planned_date_end': self.task_3_planned_date_begin + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the planned_hours into account and update the" \
                         "planned_date_end accordingly when moving a task forward."
        self.assertEqual(self.task_3.planned_date_end, self.task_3_planned_date_end + relativedelta(days=1, hour=9), failed_message)

    def test_auto_shift_on_task_depending_on_with_planned_hours(self):
        """
        This test purpose is to ensure that the task planned_date_fields (begin/end) are calculated accordingly to
        the planned_hours if any. So if a task, that the current task depends on, has to be move backward up to after
        an unavailable period of time and that its planned_hours is such that the planned_date_end would fall into that
        unavailable period, then the planned_date_begin will be push backward before the unavailable period so that
        the planned_hours constraint is met.
        """
        new_task_3_begin_date = self.task_1_planned_date_end - timedelta(hours=2)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the planned_hours into account and update the" \
                         "planned_date_begin accordingly when moving a task backward."
        self.assertEqual(self.task_1.planned_date_begin,
                         self.task_1_planned_date_begin + relativedelta(days=-1, hour=16), failed_message)

    def test_auto_shift_on_dependent_task_without_planned_hours(self):
        """
        This test purpose is to ensure that the interval made by the task planned_date_fields (begin/end) is
        preserved when no planned_hours is set.
        """
        self.task_3.write({
            'planned_hours': 0,
        })
        self.task_1.write({
            'planned_date_begin': self.task_3_planned_date_begin,
            'planned_date_end': self.task_3_planned_date_begin + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        failed_message = "When planned_hours=0, the auto shift date feature should preserve the time interval between" \
                         "planned_date_begin and planned_date_end when moving a task forward."
        self.assertEqual(self.task_3.planned_date_end - self.task_3.planned_date_begin,
                         self.task_3_planned_date_end - self.task_3_planned_date_begin, failed_message)

    def test_auto_shift_on_task_depending_on_without_planned_hours(self):
        """
        This test purpose is to ensure that the interval made by the task planned_date_fields (begin/end) is
        preserved when no planned_hours is set.
        """
        new_task_3_begin_date = self.task_1_planned_date_end - timedelta(hours=2)
        self.task_1.write({
            'planned_hours': 0,
        })
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the planned_hours into account and update the" \
                         "planned_date_begin accordingly when moving a task backward."
        self.assertEqual(self.task_1.planned_date_end - self.task_1.planned_date_begin,
                         self.task_1_planned_date_end - self.task_1_planned_date_begin, failed_message)

    def test_auto_shift_next_work_time_with_planned_hours(self):
        """
        This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
        if any is set, or with the user company resource_calendar if not.
        """
        new_task_1_planned_date_begin = self.task_3_planned_date_begin + timedelta(hours=1)
        self.task_1.write({
            'planned_date_begin': new_task_1_planned_date_begin,
            'planned_date_end': new_task_1_planned_date_begin + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_3.planned_date_begin,
                         self.task_3_planned_date_begin + relativedelta(days=1, hour=8), failed_message)

    def test_auto_shift_previous_work_time_with_planned_hours(self):
        """
        This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
        if any is set, or with the user company resource_calendar if not.
        """
        new_task_3_begin_date = self.task_1_planned_date_begin - timedelta(hours=1)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_1.planned_date_end,
                         self.task_1_planned_date_end + relativedelta(days=-1, hour=17), failed_message)

    def test_auto_shift_next_work_time_without_planned_hours(self):
        """
        This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
        if any is set, or with the user company resource_calendar if not.
        """
        new_task_1_planned_date_begin = self.task_3_planned_date_begin + timedelta(hours=1)
        self.task_3.write({
            'planned_hours': 0,
        })
        self.task_1.write({
            'planned_date_begin': new_task_1_planned_date_begin,
            'planned_date_end': new_task_1_planned_date_begin + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_3.planned_date_begin,
                         self.task_3_planned_date_begin + relativedelta(days=1, hour=8), failed_message)

    def test_auto_shift_previous_work_time_without_planned_hours(self):
        """
        This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
        if any is set, or with the user company resource_calendar if not.
        """
        new_task_3_begin_date = self.task_1_planned_date_begin - timedelta(hours=1)
        self.task_1.write({
            'planned_hours': 0,
        })
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_1.planned_date_end,
                         self.task_1_planned_date_end + relativedelta(days=-1, hour=17), failed_message)

    def test_auto_shift_next_work_time_long_leaves(self):
        """
        This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
        if any is set, or with the user company resource_calendar if not. This test is made on a long leave period to
        ensure that it works when the new dates are further than the default fetched data. This test focuses on ensuring
        that a task is pushed forward up to after the holiday leave period when a task that it depends on is moved so that
        it creates an overlap between, the tasks.
        """
        self.task_3.write({
            'planned_date_begin': self.task_4_planned_date_begin,
            'planned_date_end': self.task_4_planned_date_begin + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the user company resource_calendar into account and" \
                         "works also for long periods (requiring extending the search interval period)."
        self.assertEqual(self.task_4.planned_date_begin,
                         self.task_4_planned_date_begin + relativedelta(month=8, day=2, hour=8), failed_message)

    def test_auto_shift_previous_work_time_long_leaves(self):
        """
        This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
        if any is set, or with the user company resource_calendar if not. This test is made on a long leave period to
        ensure that it works when the new dates are further than the default fetched data. This test focuses on ensuring
        that a task is pushed backward up to before the holiday leave period when a dependent task is moved so that it
        creates an overlap between the tasks.
        """
        self.task_6.write({
            'planned_date_begin': self.task_5_planned_date_begin,
            'planned_date_end': self.task_5_planned_date_begin + (self.task_6_planned_date_end - self.task_6_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the user company resource_calendar into account and" \
                         "works also for long periods (requiring extending the search interval period)."
        self.assertEqual(self.task_5.planned_date_end,
                         self.task_5_planned_date_end + relativedelta(month=6, day=30, hour=17), failed_message)

    def test_auto_shift_cascading_forward(self):
        """
        This test purpose is to ensure that the cascade is well supported on dependent tasks
        (task A move impacts B that moves forwards and then impacts C that is moved forward).
        """
        new_task_3_planned_date_begin = self.task_4_planned_date_begin - timedelta(hours=1)
        self.task_3.write({
            'planned_date_begin': new_task_3_planned_date_begin,
            'planned_date_end': new_task_3_planned_date_begin + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should handle correctly dependencies cascades."
        self.assertEqual(self.task_4.planned_date_begin,
                         self.task_3.planned_date_end, failed_message)
        self.assertEqual(self.task_4.planned_date_end,
                         self.task_4_planned_date_begin + relativedelta(month=8, day=2, hour=9), failed_message)
        self.assertEqual(self.task_5.planned_date_begin,
                         self.task_4.planned_date_end)
        self.assertEqual(self.task_5.planned_date_end,
                         self.task_5_planned_date_end + relativedelta(days=1, hour=9), failed_message)

    def test_auto_shift_cascading_backward(self):
        """
        This test purpose is to ensure that the cascade is well supported on tasks that the current task depends on
        (task A move impacts B that moves backward and then impacts C that is moved backward).
        """
        new_task_6_planned_date_begin = self.task_5_planned_date_begin + timedelta(hours=1)
        self.task_6.write({
            'planned_date_begin': new_task_6_planned_date_begin,
            'planned_date_end': new_task_6_planned_date_begin + (self.task_6_planned_date_end - self.task_6_planned_date_begin),
        })
        failed_message = "The auto shift date feature should handle correctly dependencies cascades."
        self.assertEqual(self.task_5.planned_date_end,
                         new_task_6_planned_date_begin, failed_message)
        self.assertEqual(self.task_5.planned_date_begin,
                         datetime(year=2021, month=6, day=29, hour=9), failed_message)
        self.assertEqual(self.task_4.planned_date_end,
                         self.task_5.planned_date_begin)
        self.assertEqual(self.task_4.planned_date_begin,
                         datetime(year=2021, month=6, day=28, hour=16), failed_message)

    def test_auto_shift_project_user(self):
        new_task_6_planned_date_begin = self.task_5_planned_date_begin + timedelta(hours=1)
        self.task_6.with_user(self.user_projectuser).with_context(tracking_disable=True).write({
            'planned_date_begin': new_task_6_planned_date_begin,
            'planned_date_end': new_task_6_planned_date_begin + (self.task_6_planned_date_end - self.task_6_planned_date_begin),
        })
        failed_message = "The auto shift date feature should handle correctly dependencies cascades."
        self.assertEqual(self.task_5.planned_date_end,
                         new_task_6_planned_date_begin, failed_message)
        self.assertEqual(self.task_5.planned_date_begin,
                         datetime(year=2021, month=6, day=29, hour=9), failed_message)
        self.assertEqual(self.task_4.planned_date_end,
                         self.task_5.planned_date_begin)
        self.assertEqual(self.task_4.planned_date_begin,
                         datetime(year=2021, month=6, day=28, hour=16), failed_message)
