# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from .test_common import TestCommon


class TestPlanningLeaves(TestCommon):
    def test_simple_employee_leave(self):
        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'date_from': datetime.datetime(2020, 1, 1, 8, 0),
            'date_to': datetime.datetime(2020, 1, 1, 17, 0),
        })

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 1, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 1, 17, 0),
        })
        slot_2 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 2, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 2, 17, 0),
        })

        self.assertNotEqual(slot_1.with_context(include_past=True).leave_warning, False,
                    "leave is not validated , but warning for requested time off")

        leave.action_validate()

        self.assertNotEqual(slot_1.with_context(include_past=True).leave_warning, False,
                            "employee is on leave, should have a warning")
        # The warning should display the whole concerned leave period
        self.assertEqual(slot_1.with_context(include_past=True).leave_warning,
                         "patrick is on time off from the 01/01/2020 at 09:00:00 to the 01/01/2020 at 18:00:00. \n")

        self.assertEqual(slot_2.with_context(include_past=True).leave_warning, False,
                         "employee is not on leave, no warning")

    def test_multiple_leaves(self):
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'date_from': datetime.datetime(2020, 1, 6, 8, 0),
            'date_to': datetime.datetime(2020, 1, 7, 17, 0),
        }).action_validate()

        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'date_from': datetime.datetime(2020, 1, 8, 8, 0),
            'date_to': datetime.datetime(2020, 1, 10, 17, 0),
        }).action_validate()

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 6, 17, 0),
        })

        self.assertNotEqual(slot_1.with_context(include_past=True).leave_warning, False,
                            "employee is on leave, should have a warning")
        # The warning should display the whole concerned leave period
        self.assertEqual(slot_1.with_context(include_past=True).leave_warning,
                         "patrick is on time off from the 01/06/2020 to the 01/07/2020. \n")

        slot_2 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 7, 17, 0),
        })
        self.assertEqual(slot_2.with_context(include_past=True).leave_warning,
                         "patrick is on time off from the 01/06/2020 to the 01/07/2020. \n")

        slot_3 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 10, 17, 0),
        })
        self.assertEqual(slot_3.with_context(include_past=True).leave_warning, "patrick is on time off from the 01/06/2020 to the 01/10/2020. \n",
                         "should show the start of the 1st leave and end of the 2nd")
