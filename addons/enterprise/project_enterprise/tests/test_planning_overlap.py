# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestTaskDependencies(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task_1.write({
            'planned_date_begin': datetime(2022, 2, 25, 8, 0, 0),
            'planned_date_end': datetime(2022, 2, 25, 10, 0, 0)
        })

    def test_same_user_no_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': datetime(2022, 2, 24, 13, 0, 0),
            'planned_date_end': datetime(2022, 2, 24, 15, 0, 0)
        })

        self.assertEqual(self.task_1.planning_overlap, 0)
        self.assertEqual(self.task_2.planning_overlap, 0)

        search_result = self.env['project.task'].search([('planning_overlap', '=', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_different_users_overlap(self):
        self.task_2.write({
            'planned_date_begin': datetime(2022, 2, 25, 9, 0, 0),
            'planned_date_end': datetime(2022, 2, 25, 11, 0, 0)
        })

        self.assertEqual(self.task_1.planning_overlap, 0)
        self.assertEqual(self.task_2.planning_overlap, 0)

        search_result = self.env['project.task'].search([('planning_overlap', '=', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': datetime(2022, 2, 25, 9, 0, 0),
            'planned_date_end': datetime(2022, 2, 25, 11, 0, 0)
        })

        self.assertEqual(self.task_1.planning_overlap, 1)
        self.assertEqual(self.task_2.planning_overlap, 1)

        search_result = self.env['project.task'].search([('planning_overlap', '>', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)
