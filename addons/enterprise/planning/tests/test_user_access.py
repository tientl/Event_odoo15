# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError

from datetime import datetime


@tagged('post_install', '-at_install')
class TestUserAccess(TransactionCase):

    def setUp(self):
        super(TestUserAccess, self).setUp()

        # create a planning manager
        self.planning_mgr = new_test_user(self.env,
                                          login='mgr',
                                          groups='planning.group_planning_manager',
                                          name='Planning Manager',
                                          email='mgr@example.com')

        self.hr_planning_mgr = self.env['hr.employee'].create({
            'name': 'Planning Manager',
            'user_id': self.planning_mgr.id,
        })

        # create a planning user
        self.planning_user = new_test_user(self.env,
                                           login='puser',
                                           groups='planning.group_planning_user',
                                           name='Planning User',
                                           email='user@example.com')

        self.hr_planning_user = self.env['hr.employee'].create({
            'name': 'Planning User',
            'user_id': self.planning_user.id,
        })
        self.res_planning_user = self.hr_planning_user.resource_id

        # create an internal user
        self.internal_user = new_test_user(self.env,
                                           login='iuser',
                                           groups='base.group_user',
                                           name='Internal User',
                                           email='internal_user@example.com')

        self.hr_internal_user = self.env['hr.employee'].create({
            'name': 'Internal User',
            'user_id': self.internal_user.id,
        })
        self.res_internal_user = self.hr_internal_user.resource_id

        # create several slots for users
        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 27, 17, 0, 0),
            'resource_id': self.res_planning_user.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2022, 6, 27, 17, 0, 0),
            'repeat_interval': 1,
            'state': 'published',
        })

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 28, 17, 0, 0),
            'resource_id': self.res_internal_user.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2022, 6, 28, 17, 0, 0),
            'repeat_interval': 1,
            'state': 'published',
        })

    def test_01_internal_user_read_own_slots(self):
        """
        An internal user shall be able to read its own slots.
        """
        my_slot = self.env['planning.slot'].with_user(self.internal_user).search(
            [('user_id', '=', self.internal_user.id)],
            limit=1)

        self.assertNotEqual(my_slot.id, False,
                            "An internal user shall be able to read its own slots")

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
            'resource_id': self.res_internal_user.id,
            'state': 'draft',
        })
        unpublished_count = self.env['planning.slot'].with_user(self.internal_user).search_count([('state', '=', 'draft')])
        self.assertEqual(unpublished_count, 0, "An internal user shouldn't see unpublished slots")

    def test_02_internal_user_read_other_slots(self):
        """
        An internal user shall NOT be able to read other slots.
        """
        other_slot = self.env['planning.slot'].with_user(self.internal_user).search(
                [('user_id', '=', self.planning_user.id)],
                limit=1)

        planning_user_slot = self.env['planning.slot'].with_user(self.planning_user).search(
                [('user_id', '=', self.planning_user.id)],
                limit=1)

        self.assertFalse(
            other_slot,
            "An internal user shall NOT be able to read other slots")

        self.assertNotEqual(
            planning_user_slot,
            False,
            "A planning user shall be able to access to its own slots")

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
            'resource_id': self.res_planning_user.id,
            'state': 'draft',
        })
        unpublished_count = self.env['planning.slot'].with_user(self.planning_user).search_count([('state', '=', 'draft')])
        self.assertEqual(unpublished_count, 0, "A planning user shouldn't see unpublished slots")

        mgr_unpublished_count = self.env['planning.slot'].with_user(self.planning_mgr).search_count([('state', '=', 'draft')])
        self.assertNotEqual(mgr_unpublished_count, 0, "A planning manager should see unpublished slots")

    def test_03_internal_user_write_own_slots(self):
        """
        An internal user shall NOT be able to write its own slots.
        """
        my_slot = self.env['planning.slot'].with_user(self.internal_user).search(
            [('user_id', '=', self.internal_user.id)],
            limit=1)

        with self.assertRaises(AccessError):
            my_slot.write({
                'name': 'a new name'
            })

    def test_04_internal_user_create_own_slots(self):
        """
        An internal user shall NOT be able to create its own slots.
        """
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.internal_user).create({
                'start_datetime': datetime(2019, 7, 28, 8, 0, 0),
                'end_datetime': datetime(2019, 7, 28, 17, 0, 0),
                'resource_id': self.res_internal_user.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_until': datetime(2022, 7, 28, 17, 0, 0),
                'repeat_interval': 1,
            })
