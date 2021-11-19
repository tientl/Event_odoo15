# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests import Form

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestTaskDependencies(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_pigs.write({
            'is_fsm': True,
        })

    def test_task_dependencies_settings_change(self):

        def set_task_dependencies_setting(enabled):
            features_config = self.env["res.config.settings"].create({'group_project_task_dependencies': enabled })
            features_config.execute()

        set_task_dependencies_setting(True)
        self.assertFalse(self.project_pigs.allow_task_dependencies, "FSM Projects should not follow group_project_task_dependencies setting changes")

        with Form(self.env['project.project']) as project_form:
            project_form.name = 'My Ducks Project'
            project_form.is_fsm = True
            self.assertFalse(project_form.allow_task_dependencies, "New FSM Projects allow_task_dependencies should default False")
