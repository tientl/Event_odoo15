# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website IM Livechat Helpdesk',
    'category': 'Services/Helpdesk',
    'sequence': 58,
    'summary': 'Ticketing, Support, Livechat',
    'depends': [
        'website_helpdesk',
        'website_livechat',
    ],
    'description': """
Website IM Livechat integration for the helpdesk module
=======================================================

Features:

    - Have a team-related livechat channel to answer your customer's questions.
    - Create new tickets with ease using commands in the channel.

    """,
    'data': [
        'views/helpdesk_view.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'mail.assets_discuss_public': [
            'website_helpdesk_livechat/static/src/models/*/*.js',
        ],
        'web.assets_backend': [
            'website_helpdesk_livechat/static/src/models/*/*.js',
        ],
        'web.qunit_suite_tests': [
            'website_helpdesk_livechat/static/src/components/*/tests/*.js',
        ],
    },
}
