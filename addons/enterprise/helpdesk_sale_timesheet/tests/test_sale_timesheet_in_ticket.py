# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged("-at_install", "post_install", "helpdesk_sale_timesheet")
class TestSaleTimesheetInTicket(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.helpdesk_team = cls.env['helpdesk.team'].create({
            'name': 'Test Team',
            'use_helpdesk_timesheet': True,
            'use_helpdesk_sale_timesheet': True,
            'project_id': cls.project_task_rate.id,
        })

    def test_compute_sale_line_id_in_ticket(self):
        """ Test to check if the _compute_sale_line_id method correctly works

            Test Case:
            =========
            1) Create ticket in the team,
            2) Check if the SOL defined in ticket is the one containing the prepaid service product
        """
        # 1) Create ticket in the team
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner_b.id,
        })

        # 2) Check if the SOL defined in ticket is the one containing the prepaid service product
        self.assertEqual(ticket.sale_line_id, self.so.order_line[-1], "The SOL in the ticket should be the one containing the prepaid service product.")

    def test_compute_so_line_in_timesheet(self):
        """ Test to check if the SOL computed for the timesheets in the ticket is the expected one.

            Test Case:
            =========
            1) Create ticket in the team,
            2) Check if the SOL defined in the ticket is the one containing the prepaid service product,
            3) Create timesheet and check if the SOL in the timesheet is the one in the SOL,
            4) Change the SOL in the ticket and check if the SOL in the timesheet also changes.
        """
        # 1) Create ticket in the team
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner_b.id,
        })

        # 2) Check if the SOL defined in ticket is the one containing the prepaid service product
        self.assertEqual(ticket.sale_line_id, self.so.order_line[-1], "The SOL in the ticket should be the one containing the prepaid service product.")

        # 3) Create timesheet and check if the SOL in the timesheet is the one in the SOL
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'project_id': self.project_task_rate,
            'helpdesk_ticket_id': ticket.id,
            'unit_amount': 2,
        })
        self.assertEqual(timesheet.so_line, ticket.sale_line_id, "The SOL in the timesheet should be the one in the ticket.")

        # 4) Change the SOL in the ticket and check if the SOL in the timesheet also changes.
        ticket.write({
            'sale_line_id': self.so.order_line[0].id
        })
        self.assertEqual(ticket.sale_line_id, self.so.order_line[0], "The SOL in the ticket should be the one chosen.")
        self.assertEqual(timesheet.so_line, ticket.sale_line_id, "The SOL in the timesheet should be the one in the ticket.")
