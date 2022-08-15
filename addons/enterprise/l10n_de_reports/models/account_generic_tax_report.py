from odoo import models, fields, _
from odoo.tools import float_repr
from lxml import etree
from datetime import date, datetime


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_reports_buttons(self, options):
        buttons = super(AccountGenericTaxReport, self)._get_reports_buttons(options)
        if self._get_report_country_code(options) == 'DE':
            buttons += [{'name': _('XML'), 'sequence': 3, 'action': 'print_xml', 'file_export_type': _('XML')}]
        return buttons

    def get_xml(self, options):
        if self._get_report_country_code(options) != 'DE':
            return super(AccountGenericTaxReport, self).get_xml(options)

        ctx = self._set_context(options)
        report_lines = self.with_context(ctx)._get_lines(options)

        template_context = {}
        date_to = datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
        template_context['year'] = date_to.year
        if options['date']['period_type'] == 'month':
            template_context['period'] = date_to.strftime("%m")
        elif options['date']['period_type'] == 'quarter':
            month_end = int(date_to.month)
            if month_end % 3 != 0:
                raise ValueError('Quarter not supported')
            # For quarters, the period should be 41, 42, 43, 44 depending on the quarter.
            template_context['period'] = int(month_end / 3 + 40)
        template_context['creation_date'] = date.today().strftime("%Y%m%d")
        template_context['company'] = self._get_sender_company_for_export(options)

        qweb = self.env['ir.qweb']
        doc = qweb._render('l10n_de_reports.tax_export_xml', values=template_context)
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(doc, parser)

        taxes = tree.xpath('//Umsatzsteuervoranmeldung')[0]
        # Add the values dynamically. We do it here because the tag is generated from the code and
        # Qweb doesn't allow dynamically generated tags.
        elem = etree.SubElement(taxes, "Kz09")
        elem.text = "0.00" #please keep "0.00" until Odoo has "Kz09"
        for line in report_lines:
            if line['line_code']:
                #all "Kz" may be supplied as negative, except "Kz39"
                if line['columns'][0]['balance'] and (line['line_code'] != "39" or line['columns'][0]['balance'] > 0):
                    elem = etree.SubElement(taxes, "Kz" + line['line_code'])
                    #only "kz09" and "kz83" can be supplied with decimals
                    if line['line_code'] in ("09", "83"):
                        elem.text = float_repr(line['columns'][0]['balance'], self.env.company.currency_id.decimal_places)
                    else:
                        elem.text = float_repr(int(line['columns'][0]['balance']), 0)
                #"Kz09" and "kz83" must be supplied with 0.00 if they don't have balance
                elif line['line_code'] in ["09", "83"]:
                    elem = etree.SubElement(taxes, "Kz" + line['line_code'])
                    elem.text = "0.00"

        return etree.tostring(tree, pretty_print=True, standalone=False, encoding='ISO-8859-1',)
