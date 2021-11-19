# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import common
from odoo.addons.mail.tests.common import mail_new_test_user


class TestTaskFlow(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.project_user = mail_new_test_user(
            self.env, login='Armande',
            name='Armande Project_user', email='armande.project_user@example.com',
            notification_type='inbox',
            groups='project.group_project_user',
        )

        self.project_test = self.env['project.project'].create({
            'name': 'Project Test',
        })

    def test_planning_overlap(self):
        task_A = self.env['project.task'].create({
            'name': 'Fsm task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now(),
            'planned_date_end': datetime.now() + relativedelta(hours=4)
        })
        task_B = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=2),
            'planned_date_end': datetime.now() + relativedelta(hours=6)
        })
        task_C = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=5),
            'planned_date_end': datetime.now() + relativedelta(hours=7)
        })
        task_D = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=8),
            'planned_date_end': datetime.now() + relativedelta(hours=9)
        })
        self.assertEqual(task_A.planning_overlap, 1, "One task should be overlapping with task_A")
        self.assertEqual(task_B.planning_overlap, 2, "Two tasks should be overlapping with task_B")
        self.assertFalse(task_D.planning_overlap, "No task should be overlapping with task_D")
