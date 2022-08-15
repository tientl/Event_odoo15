# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Field Service - Sale",
    'summary': "Schedule and track onsite operations, invoice time and material",
    'description': """
Create Sales order with timesheets and products from tasks
    """,
    'category': 'Services/Field Service',
    'version': '1.0',
    'depends': ['industry_fsm', 'sale_timesheet_enterprise'],
    'data': [
        'data/industry_fsm_data.xml',
        'security/industry_fsm_sale_security.xml',
        'views/project_task_views.xml',
        'views/product_product_views.xml',
        'views/project_project_views.xml',
        'views/sale_order_views.xml',
        "views/project_sharing_views.xml",
    ],
    'application': False,
    'auto_install': True,
    'demo': [],
    'post_init_hook': 'post_init',
    'assets': {
        'web.assets_backend': [
            'industry_fsm_sale/static/src/scss/fsm_product_quantity.scss',
            'industry_fsm_sale/static/src/js/fsm_product_quantity.js',
            'industry_fsm_sale/static/src/js/kanban_view/model.js',
            'industry_fsm_sale/static/src/js/kanban_view/controller.js',
            'industry_fsm_sale/static/src/js/kanban_view/renderer.js',
            'industry_fsm_sale/static/src/js/kanban_view/record.js',
            'industry_fsm_sale/static/src/js/kanban_view/view.js',
            'industry_fsm_sale/static/src/js/tours/industry_fsm_sale_tour.js',
        ],
        'web.assets_frontend': [
            'industry_fsm_sale/static/src/js/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'industry_fsm_sale/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'industry_fsm_sale/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
