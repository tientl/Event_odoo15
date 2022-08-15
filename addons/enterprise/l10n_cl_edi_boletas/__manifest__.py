# -*- coding: utf-8 -*-
{
    "name": """Chile - Electronic Receipt""",
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'sequence': 12,
    'author': 'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'depends': ['l10n_cl_edi'],
    'data': [
        'data/cron.xml',
        'template/daily_sales_book_template.xml',
        'template/dte_template.xml',
        'security/ir.model.access.csv',
        'security/l10n_cl_edi_boletas_security.xml',
        'views/l10n_cl_daily_sales_book_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'description': """
Purpose of the Module:
======================

As part of the SII requirements (Legal requirement in Chile), 
beginning on March 2021 boletas transactions must be sent to the SII under the 
electronic workflow using a different web service than the one used for electronic Invoices. 
Previously, there was no need to send the boletas to the SII, just a daily report.

Additionally of sending the Boleta individually (with the EDI workflow),
at the end of the day, a daily summary with all the Boletas transactions
should be sent to the SII - electronically (also a legal requirement).
This is called "Libro de ventas diarias" (former "reporte de consumo de folios" or RCOF).


Differences between Electronic boletas vs Electronic Invoicing Workflows:
=========================================================================

These workflows have some important differences that lead us to do this PR with the specific changes.
Here are the differences:

* The mechanism for sending the electronic boletas information needs dedicated servers, different from those used at the reception electronic invoice ("Palena" for the production environment - palena.sii.cl and "Maullin" for the test environment - maullin.sii.cl).
* The authentication services, querying the status of a delivery and the status of a document will be different.
* The authentication token obtained
* The XML schema for sending the electronic boletas was updated with the incorporation of new tags
* The validation diagnosis of electronic boletas will be delivered through a "REST" web service that has as an input the track-id of the delivery. Electronic Invoices will continue to receive their diagnoses via e-mail.
* The track-id ("identificador de envío") associated with the electronic boletas will be 15 digits long. (Electronics Invoice is 10)

Highlights from this SII Guide:
    https://www.sii.cl/factura_electronica/factura_mercado/Instructivo_Emision_Boleta_Elect.pdf
    """,
    'license': 'OEEL-1',
}
