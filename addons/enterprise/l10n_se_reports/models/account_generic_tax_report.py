from odoo import models, _
from odoo.tools import float_repr
from lxml import etree
from lxml.objectify import fromstring


DOCTYPE = '<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www1.skatteverket.se/demoeskd/eSKDUpload_6p0.dtd">'


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_reports_buttons(self, options):
        buttons = super(AccountGenericTaxReport, self)._get_reports_buttons(options)
        if self._get_report_country_code(options) == 'SE':
            buttons += [{'name': _('XML'), 'sequence': 3, 'action': 'print_xml', 'file_export_type': _('XML')}]
        return buttons

    def get_xml(self, options):
        if self._get_report_country_code(options) != 'SE':
            return super(AccountGenericTaxReport, self).get_xml(options)
        ctx = self._set_context(options)
        report_lines = self.with_context(ctx)._get_lines(options)

        template_context = {line['line_code']: float_repr(line['columns'][0]['balance'], 0) for line in report_lines}

        template_context['org_number'] = self._get_sender_company_for_export(options).org_number
        template_context['period'] = (options['date']['date_to'][:4] + options['date']['date_to'][5:7])
        template_context['comment'] = ''

        qweb = self.env['ir.qweb']
        doc = qweb._render('l10n_se_reports.tax_export_xml', values=template_context)
        tree = fromstring(doc)

        return etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='ISO-8859-1', doctype=DOCTYPE)
