# -*- coding: utf-8 -*-
{
    'name': "Documents",

    'summary': "Document management",

    'description': """
        App to upload and manage your documents.
    """,

    'author': "Odoo",
    'category': 'Productivity/Documents',
    'sequence': 80,
    'version': '1.1',
    'application': True,
    'website': 'https://www.odoo.com/app/documents',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'portal', 'web', 'attachment_indexation', 'digest'],

    # always loaded
    'data': [
        'data/ir_asset.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'data/mail_data.xml',
        'data/documents_data.xml',
        'data/workflow_data.xml',
        'data/files_data.xml',
        'data/mail_template_data.xml',
        'views/assets.xml',
        'views/documents_views.xml',
        'views/templates.xml',
        'views/activity_views.xml',
        'wizard/request_activity_views.xml',
        'wizard/link_to_record_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'documents/static/src/js/documents_controller_mixin.js',
            'documents/static/src/js/documents_model_mixin.js',
            'documents/static/src/js/documents_utils.js',
            'documents/static/src/js/documents_view_mixin.js',
            'documents/static/src/js/documents_document_viewer.js',
            'documents/static/src/js/documents_kanban_color_widget.js',
            'documents/static/src/js/documents_kanban_controller.js',
            'documents/static/src/js/documents_kanban_controller_mobile.js',
            'documents/static/src/js/documents_kanban_model.js',
            'documents/static/src/js/documents_kanban_record.js',
            'documents/static/src/js/documents_kanban_renderer.js',
            'documents/static/src/js/documents_kanban_view.js',
            'documents/static/src/js/documents_list_controller.js',
            'documents/static/src/js/documents_list_model.js',
            'documents/static/src/js/documents_list_renderer.js',
            'documents/static/src/js/documents_list_view.js',
            'documents/static/src/js/documents_search_panel.js',
            'documents/static/src/js/documents_search_panel_model_extension.js',
            'documents/static/src/js/documents_inspector.js',
            'documents/static/src/js/documents_inspector_mobile.js',
            'documents/static/src/owl/components/pdf_manager/pdf_manager.js',
            'documents/static/src/owl/components/pdf_page/pdf_page.js',
            'documents/static/src/owl/components/pdf_group_name/pdf_group_name.js',
            'documents/static/src/js/systray_activity_menu.js',
            'documents/static/src/js/tours/documents.js',
            'documents/static/src/scss/documents_views.scss',
            'documents/static/src/scss/documents_kanban_view.scss',
            'documents/static/src/owl/components/pdf_manager/pdf_manager.scss',
            'documents/static/src/owl/components/pdf_page/pdf_page.scss',
            'documents/static/src/owl/components/pdf_group_name/pdf_group_name.scss',
        ],
        'documents.public_page_assets': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'documents/static/src/scss/documents_public_pages.scss',
            'documents/static/src/js/documents_public_pages.js',
        ],
        'web.tests_assets': [
            'documents/static/tests/mock_server.js',
        ],
        'web.qunit_suite_tests': [
            'documents/static/tests/documents_test_utils.js',
            'documents/static/tests/documents_kanban_tests.js',
            'documents/static/tests/documents_pdf_manager_tests.js',
            'documents/static/tests/documents_systray_activity_menu_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'documents/static/tests/documents_test_utils.js',
            'documents/static/tests/documents_kanban_mobile_tests.js',
        ],
        'web.assets_qweb': [
            'documents/static/src/xml/*.xml',
            'documents/static/src/owl/components/pdf_manager/pdf_manager.xml',
            'documents/static/src/owl/components/pdf_page/pdf_page.xml',
            'documents/static/src/owl/components/pdf_group_name/pdf_group_name.xml',
        ],
    }
}
