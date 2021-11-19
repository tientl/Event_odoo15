# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestHrAppraisal(TransactionCase):
    """ Test used to check that when doing appraisal creation."""

    def setUp(self):
        super(TestHrAppraisal, self).setUp()
        self.HrEmployee = self.env['hr.employee']
        self.HrAppraisal = self.env['hr.appraisal']
        self.main_company = self.env.ref('base.main_company')

        self.dep_rd = self.env['hr.department'].create({'name': 'RD Test'})
        self.manager_user = self.env['res.users'].create({
            'name': 'Manager User',
            'login': 'manager_user',
            'password': 'manager_user',
            'email': 'demo@demo.com',
            'partner_id': self.env['res.partner'].create({'name': 'Manager Partner'}).id,
        })
        self.manager = self.env['hr.employee'].create({
            'name': 'Manager Test',
            'department_id': self.dep_rd.id,
            'user_id': self.manager_user.id,
        })

        self.job = self.env['hr.job'].create({'name': 'Developer Test', 'department_id': self.dep_rd.id})
        self.colleague = self.env['hr.employee'].create({'name': 'Colleague Test', 'department_id': self.dep_rd.id})

        group = self.env.ref('hr_appraisal.group_hr_appraisal_user').id
        self.user = self.env['res.users'].create({
            'name': 'Michael Hawkins',
            'login': 'test',
            'groups_id': [(6, 0, [group])],
            'notification_type': 'email',
        })

        self.hr_employee = self.HrEmployee.create(dict(
            name="Michael Hawkins",
            user_id=self.user.id,
            department_id=self.dep_rd.id,
            parent_id=self.manager.id,
            job_id=self.job.id,
            work_phone="+3281813700",
            work_email='michael@odoo.com',
            create_date=date.today() + relativedelta(months=-6),
            last_appraisal_date=date.today() + relativedelta(months=-6)
        ))
        self.hr_employee.write({'work_location_id': [(0, 0, {'name': "Grand-Rosière"})]})

        self.env.company.appraisal_plan = True
        self.env['ir.config_parameter'].sudo().set_param("hr_appraisal.appraisal_create_in_advance_days", 8)
        self.duration_after_recruitment = 6
        self.duration_first_appraisal = 9
        self.duration_next_appraisal = 12
        self.env.company.write({
            'duration_after_recruitment': self.duration_after_recruitment,
            'duration_first_appraisal': self.duration_first_appraisal,
            'duration_next_appraisal': self.duration_next_appraisal,
        })

    def test_hr_appraisal(self):
        # I run the scheduler
        self.env['res.company']._run_employee_appraisal_plans()  # cronjob

        # I check whether new appraisal is created for above employee or not
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")

        # I start the appraisal process by click on "Start Appraisal" button.
        appraisals.action_confirm()

        # I check that state is "Appraisal Sent".
        self.assertEqual(appraisals.state, 'pending', "appraisal should be 'Appraisal Sent' state")
        # I check that "Final Interview Date" is set or not.
        event = self.env['calendar.event'].create({
            "name":"Appraisal Meeting",
            "start": datetime.now() + relativedelta(months=1),
            "stop":datetime.now() + relativedelta(months=1, hours=2),
            "duration":2,
            "allday": False,
            'res_id': appraisals.id,
            'res_model_id': self.env.ref('hr_appraisal.model_hr_appraisal').id
        })
        self.assertTrue(appraisals.date_final_interview, "Interview Date is not created")
        # I check whether final interview meeting is created or not
        self.assertTrue(appraisals.meeting_ids, "Meeting is not linked")
        # I close this Apprisal
        appraisals.action_done()
        # I check that state of Appraisal is done.
        self.assertEqual(appraisals.state, 'done', "Appraisal should be in done state")

    def test_new_employee_next_appraisal_date_generation(self):
        # keep this test to ensure we don't break this functionnality at 
        # a later date
        hr_employee3 = self.HrEmployee.create(dict(
            name="Jane Doe",
        ))

        self.assertEqual(hr_employee3.last_appraisal_date, date.today())

    def test_01_appraisal_generation(self):
        """
            Set appraisal date at the exact time it should be to 
            generate a new appraisal
            Run the cron and check that the next appraisal_date is set properly
        """
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=6, days=-8)
        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")
        self.assertEqual(appraisals.date_close, date.today() + relativedelta(days=8))
        self.assertEqual(self.hr_employee.next_appraisal_date, date.today() + relativedelta(days=8))

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals_2 = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertEqual(len(appraisals), len(appraisals_2))

    def test_02_no_appraisal_generation(self):
        """
            Set appraisal date later than the time it should be to generate
            a new appraisal
            Run the cron and check the appraisal is not created
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=12, days=-9)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=12, days=-9)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertFalse(appraisals, "Appraisal created")

    def test_03_appraisal_generation_in_the_past(self):
        """
            Set appraisal date way before the time it should be to generate
            a new appraisal
            Run the cron and check the appraisal is created with the proper
            close_date and appraisal date
        """
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=24)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")
        self.assertEqual(appraisals.date_close, date.today() + relativedelta(days=8))
        self.assertEqual(self.hr_employee.next_appraisal_date, date.today() + relativedelta(days=8))

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals_2 = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertEqual(len(appraisals), len(appraisals_2))

    def test_07_check_manual_appraisal_set_appraisal_date(self):
        """
            Create manualy an appraisal with a date_close
            Check the appraisal_date is set properly
        """
        future_appraisal = self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() + relativedelta(months=1),
            'state': 'new'
        })
        self.assertEqual(self.hr_employee.next_appraisal_date, date.today() + relativedelta(months=1))

    def test_08_check_new_employee_no_appraisal(self):
        """
            Employee has started working recenlty
            less than duration_after_recruitment ago,
            check that appraisal is not set
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=3)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=3)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertFalse(appraisals, "Appraisal created")

    def test_09_check_appraisal_after_recruitment(self):
        """
            Employee has started working recently
            Time for a first appraisal after
            some time (duration_after_recruitment) has evolved
            since recruitment
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=self.duration_after_recruitment, days=10)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")

    def test_10_check_no_appraisal_since_recruitment_appraisal(self):
        """
            After employees first recruitment appraisal some time has evolved,
            but not enough for the first real appraisal.
            Check that appraisal is not created
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + 2, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=2, days=10)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertFalse(appraisals, "Appraisal created")

    def test_11_check_first_appraisal_since_recruitment_appraisal(self):
        """
            Employee started while ago, has already had
            first recruitment appraisal and now it is
            time for a first real appraisal
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + self.duration_first_appraisal, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=self.duration_first_appraisal, days=10)
        # In order to make the second appraisal, cron checks that
        # there is alraedy one done appraisal for the employee
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_first_appraisal, days=10),
            'state': 'done'
        })

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")

    def test_12_check_no_appraisal_after_first_appraisal(self):
        """
            Employee has already had first recruitment appraisal
            and first real appraisal, but its not time yet
            for recurring appraisal. Check that
            appraisal is not set
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + self.duration_first_appraisal + 2, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=2, days=10)
        # In order to make recurring appraisal, cron checks that
        # there are alraedy two done appraisals for the employee
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_first_appraisal + 2, days=10),
            'state': 'done'
        })
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=2, days=10),
            'state': 'done'
        })

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id), ('state', '=', 'new')])
        self.assertFalse(appraisals, "Appraisal created")

    def test_12_check_recurring_appraisal(self):
        """
            check that recurring appraisal is created
        """

        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + self.duration_first_appraisal + self.duration_next_appraisal, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=self.duration_next_appraisal, days=10)

        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_first_appraisal + self.duration_next_appraisal, days=10),
            'state': 'done'
        })
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_next_appraisal, days=10),
            'state': 'done'
        })

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")
