# -*- coding: utf-8 -*-
{
    'name':"Map View",
    'summary':"Defines the map view for odoo enterprise",
    'description':"Allows the viewing of records on a map",
    'category': 'Hidden',
    'version':'1.0',
    'depends':['web', 'base_setup'],
    'data':[
        "views/res_config_settings.xml",
        "views/res_partner_views.xml",
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'web_map/static/src/js/map_controller.js',
            'web_map/static/src/js/map_model.js',
            'web_map/static/src/js/map_renderer.js',
            'web_map/static/src/js/map_view.js',
            'web_map/static/lib/leaflet/leaflet.css',
            'web_map/static/src/scss/map_view.scss',
        ],
        'web.qunit_suite_tests': [
            'web_map/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'web_map/static/src/xml/**/*',
        ],
    }
}
