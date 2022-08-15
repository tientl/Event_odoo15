# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import time

from freezegun import freeze_time
from logging import getLogger

from odoo.addons.appointment.tests.test_performance import AppointmentUIPerformanceCase
from odoo.tests import tagged
from odoo.tests.common import warmup

_logger = getLogger(__name__)


@tagged('appointment_performance', 'post_install', '-at_install')
class OnelineWAppointmentPerformance(AppointmentUIPerformanceCase):

    @classmethod
    def setUpClass(cls):
        super(OnelineWAppointmentPerformance, cls).setUpClass()
        cls.test_apt_type.is_published = True

    @warmup
    def test_appointment_type_page_website_whours_public(self):
        random.seed(1871)  # fix shuffle in _slots_available

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=42):  # apt only: 41
                self._test_url_open('/calendar/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /calendar/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~1.00 (but with boilerplate)
        # Time after optimization: ~0.35

    @warmup
    def test_appointment_type_page_website_whours_user(self):
        random.seed(1871)  # fix shuffle in _slots_available

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate('staff_user_bxls', 'staff_user_bxls')
            with self.assertQueryCount(default=46):  # apt only: 43
                self._test_url_open('/calendar/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /calendar/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~1.00 (but with boilerplate)
        # Time after optimization: ~0.35
