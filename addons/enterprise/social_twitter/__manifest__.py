# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social Twitter',
    'category': 'Marketing/Social Marketing',
    'summary': 'Manage your Twitter accounts and schedule tweets',
    'version': '1.0',
    'description': """Manage your Twitter accounts and schedule tweets""",
    'depends': ['social', 'iap'],
    'data': [
        'security/ir.model.access.csv',
        'data/social_media_data.xml',
        'views/social_post_template_views.xml',
        'views/social_stream_views.xml',
        'views/social_stream_post_views.xml',
        'views/social_twitter_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'social_twitter/static/src/scss/social_twitter.scss',
            'social_twitter/static/src/js/twitter_users_autocomplete.js',
            'social_twitter/static/src/js/stream_post_twitter_comments.js',
            'social_twitter/static/src/js/stream_post_kanban_controller.js',
            ('after', 'social/static/src/js/social_post_formatter_mixin.js', 'social_twitter/static/src/js/social_post_formatter_mixin.js'),
        ],
        'web.assets_qweb': [
            'social_twitter/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
