# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Data Cleaning',
    'version': '1.0',
    'category': 'Productivity/Data Cleaning',
    'sequence': 135,
    'summary': """Easily format text data across multiple records. Find duplicate records and easily merge them.""",
    'description': """Easily format text data across multiple records. Find duplicate records and easily merge them.""",
    'depends': ['web', 'mail', 'phone_validation'],
    'data': [
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/data_cleaning_model_views.xml',
        'views/data_cleaning_rule_views.xml',
        'views/data_cleaning_record_views.xml',
        'views/data_cleaning_views.xml',
        'views/data_cleaning_templates.xml',
        'data/data_cleaning_data.xml',
        'data/data_cleaning_cron.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'data_cleaning/static/src/js/**/*',
        ],
        'web.assets_qweb': [
            'data_cleaning/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
