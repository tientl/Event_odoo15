# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.tests import tagged

import urllib.parse


@tagged('mail_enterprise_mobile')
class TestMailMobile(test_mail_common.TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailMobile, cls).setUpClass()
        cls.original_domain = cls.env['ir.config_parameter'].sudo().get_param('web.base.url')
        cls.env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://yourcompany.odoo.com')

    @classmethod
    def tearDownClass(cls):
        cls.env['ir.config_parameter'].sudo().set_param('web.base.url', cls.original_domain)
        super(TestMailMobile, cls).tearDownClass()

    def test_override_url_in_mail(self):
        url = self.env['mail.thread']._notify_get_action_link('view', model='mail.activity', res_id=1)
        original_expected_link = 'http://yourcompany.odoo.com/mail/view?model=mail.activity&res_id=1'
        expected_url = 'https://redirect-url.email/?link={0}&apn={1}&afl={0}&ibi={1}&ifl={0}'.format(
            urllib.parse.quote(original_expected_link, safe=''),
            'com.odoo.mobile',
        )
        self.assertEqual(url, expected_url)

    def test_blacklist_not_override_url_in_mail(self):
        url = self.env['mail.thread']._notify_get_action_link('view', model='mail.activity', res_id=1, access_token='test')
        self.assertFalse(url.startswith('https://redirect-url.email/'))
