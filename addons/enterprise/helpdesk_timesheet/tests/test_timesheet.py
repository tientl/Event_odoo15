# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.exceptions import ValidationError

from .common import TestHelpdeskTimesheetCommon


@tagged('-at_install', 'post_install')
class TestTimesheet(TestHelpdeskTimesheetCommon):

    def test_timesheet_cannot_be_linked_to_task_and_ticket(self):
        """ Test if an exception is raised when we want to link a task and a ticket in a timesheet

            Normally, now we cannot have a ticket and a task in one timesheet.

            Test Case:
            =========
            1) Create ticket and a task,
            2) Create timesheet with this ticket and task and check if an exception is raise.
        """
        # 1) Create ticket and a task
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
        })

        # 2) Create timesheet with this ticket and task and check if an exception is raise
        with self.assertRaises(ValidationError):
            self.env['account.analytic.line'].create({
                'name': 'Test Timesheet',
                'unit_amount': 1,
                'project_id': self.project.id,
                'helpdesk_ticket_id': ticket.id,
                'task_id': task.id,
            })
