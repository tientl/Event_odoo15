# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Odoo Mexican XML Polizas Export Edi bridge",
    "summary": """
        Bridge XML Polizas with EDI
    """,
    "version": "0.1",
    "author": "Odoo",
    "category": "Accounting/Localizations/Reporting",
    "website": "http://www.odoo.com/",
    "license": "OEEL-1",
    "depends": [
        "l10n_mx_edi",
        "l10n_mx_xml_polizas"
    ],
    "data": [
        "data/templates/xml_polizas.xml",
    ],
    "installable": True,
    "auto_install": True,
}
