# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import Form, tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestBasicFeaturesSettings(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_pigs.write({
            'is_fsm': True,
        })

    def test_task_dependencies_settings_change(self):
        self.env["res.config.settings"].create({'group_project_task_dependencies': True}).execute()

        self.assertFalse(self.project_pigs.allow_task_dependencies, "FSM Projects should not follow group_project_task_dependencies setting changes")

        with Form(self.env['project.project']) as project_form:
            project_form.name = 'My Ducks Project'
            project_form.is_fsm = True
            self.assertFalse(project_form.allow_task_dependencies, "The allow_task_dependencies feature should be disabled by default on new FSM projects")

        self.project_pigs.write({'allow_task_dependencies': True})
        self.assertTrue(self.project_pigs.allow_task_dependencies, "The allow_task_dependencies feature should be enabled on the project")

        self.env["res.config.settings"].create({'group_project_task_dependencies': False}).execute()
        self.assertFalse(self.project_pigs.allow_task_dependencies, "The feature should be disabled on the FSM project when disabled globally")

    def test_subtasks_settings_change(self):
        self.env["res.config.settings"].create({'group_subtask_project': True}).execute()

        self.assertFalse(self.project_pigs.allow_subtasks, "FSM Projects should not follow group_subtask_project setting changes")

        with Form(self.env['project.project']) as project_form:
            project_form.name = 'My Ducks Project'
            project_form.is_fsm = True
            self.assertFalse(project_form.allow_subtasks, "The allow_subtasks feature should be disabled by default on new FSM projects")

        self.project_pigs.write({'allow_subtasks': True})
        self.assertTrue(self.project_pigs.allow_subtasks, "The allow_subtasks feature should be enabled on the project")

        self.env["res.config.settings"].create({'group_subtask_project': False}).execute()
        self.assertFalse(self.project_pigs.allow_subtasks, "The feature should be disabled on the FSM project when disabled globally")
