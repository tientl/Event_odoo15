# -*- coding: utf-8 -*-
{
    'name': "Spain - Accounting reports (2021 update)",

    'description': """
        New fields and BOE export format for mod 303.
    """,

    'category': 'Accounting',

    'version': '0.1',

    'depends': ['l10n_es_reports'],

    'data': [
        'wizard/aeat_boe_export_wizards.xml',
        'wizard/aeat_tax_reports_wizards.xml',
    ],

    'auto_install': True,
    'license': 'OEEL-1',
}
