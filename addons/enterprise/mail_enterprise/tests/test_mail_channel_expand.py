# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, HttpCase


@tagged('-at_install', 'post_install')
class TestMailChannelExpand(HttpCase):

    def test_channel_expand_tour(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [(6, 0, [self.ref('base.group_user')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        MailChannelAsUser = self.env['mail.channel'].with_user(testuser)
        channel = MailChannelAsUser.channel_create("test-mail-channel-expand-tour")
        MailChannelAsUser.channel_fold(channel['uuid'], 'folded')
        MailChannelAsUser.browse(channel['id']).message_post(
            body="<p>test-message-mail-channel-expand-tour</p>",
            subtype_xmlid='mail.mt_comment'
        )
        self.start_tour("/web", 'mail_enterprise/static/tests/tours/mail_channel_expand_test_tour.js', login='testuser')
