from odoo import models, api, fields, _
from odoo.exceptions import UserError
import calendar
import re


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_reports_buttons(self, options):
        buttons = super(AccountGenericTaxReport, self)._get_reports_buttons(options)
        if self._get_report_country_code(options) == 'BE':
            buttons += [{'name': _('XML'), 'sequence': 3, 'action': 'l10n_be_print_xml', 'file_export_type': _('XML')}]
        return buttons

    def l10n_be_print_xml(self, options):
        # add options to context and return action to open transient model
        ctx = self.env.context.copy()
        ctx['l10n_be_reports_generation_options'] = options
        new_wizard = self.env['l10n_be_reports.periodic.vat.xml.export'].create({})
        view_id = self.env.ref('l10n_be_reports.view_account_financial_report_export').id
        return {
            'name': _('XML Export Options'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_be_reports.periodic.vat.xml.export',
            'type': 'ir.actions.act_window',
            'res_id': new_wizard.id,
            'target': 'new',
            'context': ctx,
            }

    def get_xml(self, options):
        # Check
        if self._get_report_country_code(options) != 'BE':
            return super(AccountGenericTaxReport, self).get_xml(options)

        vat_no, country_from_vat = self._split_vat_number_and_country_code(self.get_vat_for_export(options))

        sender_company = self._get_sender_company_for_export(options)
        default_address = sender_company.partner_id.address_get()
        address = self.env['res.partner'].browse(default_address.get("default")) or sender_company.partner_id
        if not address.email:
            raise UserError(_('No email address associated with company %s.', sender_company.name))
        if not address.phone:
            raise UserError(_('No phone associated with company %s.', sender_company.name))

        # Compute xml

        issued_by = vat_no
        dt_from = options['date'].get('date_from')
        dt_to = options['date'].get('date_to')
        send_ref = str(sender_company.partner_id.id) + str(dt_from[5:7]) + str(dt_to[:4])
        starting_month = dt_from[5:7]
        ending_month = dt_to[5:7]
        quarter = str(((int(starting_month) - 1) // 3) + 1)

        date_from = dt_from[0:7] + '-01'
        date_to = dt_to[0:7] + '-' + str(calendar.monthrange(int(dt_to[0:4]), int(ending_month))[1])

        data = {'client_nihil': options.get('client_nihil'), 'ask_restitution': options.get('ask_restitution', False), 'ask_payment': options.get('ask_payment', False)}

        complete_vat = (country_from_vat or (address.country_id and address.country_id.code or "")) + vat_no
        file_data = {
                        'issued_by': issued_by,
                        'vat_no': complete_vat,
                        'only_vat': vat_no,
                        # Company name can contain only latin characters
                        'cmpny_name': re.sub('[^-A-Za-z0-9/?:().,\'+ ]', ' ', sender_company.name),
                        'address': "%s %s" % (address.street or "", address.street2 or ""),
                        'post_code': address.zip or "",
                        'city': address.city or "",
                        'country_code': address.country_id and address.country_id.code or "",
                        'email': address.email or "",
                        'phone': address.phone.replace('.', '').replace('/', '').replace('(', '').replace(')', '').replace(' ', ''),
                        'send_ref': send_ref,
                        'quarter': quarter,
                        'month': starting_month,
                        'year': str(dt_to[:4]),
                        'client_nihil': (data['client_nihil'] and 'YES' or 'NO'),
                        'ask_restitution': (data['ask_restitution'] and 'YES' or 'NO'),
                        'ask_payment': (data['ask_payment'] and 'YES' or 'NO'),
                        'comments': self._get_report_manager(options).summary or '',
                     }

        rslt = """<?xml version="1.0"?>
<ns2:VATConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/VATConsignment" VATDeclarationsNbr="1">
""" + self._get_belgian_xml_export_representative_node() + """
    <ns2:VATDeclaration SequenceNumber="1" DeclarantReference="%(send_ref)s">
        <ns2:Declarant>
            <VATNumber xmlns="http://www.minfin.fgov.be/InputCommon">%(only_vat)s</VATNumber>
            <Name>%(cmpny_name)s</Name>
            <Street>%(address)s</Street>
            <PostCode>%(post_code)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country_code)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>
    """ % (file_data)

        if starting_month != ending_month:
            # starting month and ending month of selected period are not the same
            # it means that the accounting isn't based on periods of 1 month but on quarters
            rslt += '\t\t<ns2:Quarter>%(quarter)s</ns2:Quarter>\n\t\t' % (file_data)
        else:
            rslt += '\t\t<ns2:Month>%(month)s</ns2:Month>\n\t\t' % (file_data)
        rslt += '\t<ns2:Year>%(year)s</ns2:Year>' % (file_data)
        rslt += '\n\t\t</ns2:Period>\n'
        rslt += '\t\t<ns2:Data>\t'

        grids_list = []
        currency_id = self.env.company.currency_id

        ctx = self._set_context(options)
        ctx.update({'no_format': True, 'date_from': date_from, 'date_to': date_to})
        lines = self.with_context(ctx)._get_lines(options)

        # Create a mapping between report line ids and actual grid names
        non_compound_rep_lines = self.env['account.tax.report.line'].search([('tag_name', 'not in', ('48s44', '48s46L', '48s46T', '46L', '46T')), ('report_id.country_id.code', '=', 'BE')])
        lines_grids_map = {line.id: line.tag_name for line in non_compound_rep_lines}
        lines_grids_map[self.env.ref('l10n_be.tax_report_title_operations_sortie_46').id] = '46'
        lines_grids_map[self.env.ref('l10n_be.tax_report_title_operations_sortie_48').id] = '48'
        lines_grids_map[self.env.ref('l10n_be.tax_report_line_71').id] = '71'
        lines_grids_map[self.env.ref('l10n_be.tax_report_line_72').id] = '72'

        # Iterate on the report lines, using this mapping
        for line in lines:
            model, line_id = self._parse_line_id(line['id'])[-1][1:]
            if (
                    model == 'account.tax.report.line'
                    and line_id in lines_grids_map
                    and not currency_id.is_zero(line['columns'][0]['name'])
            ):
                grids_list.append((lines_grids_map[line_id],
                                   line['columns'][0]['name'],
                                   line['columns'][0].get('carryover_bounds', False),
                                   line.get('tax_report_line', False)))

        if options.get('grid91') and not currency_id.is_zero(options['grid91']):
            grids_list.append(('91', options['grid91'], False, None))

        # We are ignoring all grids that have 0 as values, but the belgian government always require a value at
        # least in either the grid 71 or 72. So in the case where both are set to 0, we are adding the grid 71 in the
        # xml with 0 as a value.
        if len([item for item in grids_list if item[0] == '71' or item[0] == '72']) == 0:
            grids_list.append(('71', 0, False, None))

        grids_list = sorted(grids_list, key=lambda a: a[0])
        for code, amount, carryover_bounds, tax_line in grids_list:
            if carryover_bounds:
                amount, dummy = self.get_amounts_after_carryover(tax_line, amount,
                                                                 carryover_bounds, options, 0)
                # Do not add grids that became 0 after carry over
                if amount == 0:
                    continue

            grid_amount_data = {
                    'code': code,
                    'amount': '%.2f' % amount,
                    }
            rslt += '\n\t\t\t<ns2:Amount GridNumber="%(code)s">%(amount)s</ns2:Amount''>' % (grid_amount_data)

        rslt += '\n\t\t</ns2:Data>'
        rslt += '\n\t\t<ns2:ClientListingNihil>%(client_nihil)s</ns2:ClientListingNihil>' % (file_data)
        rslt += '\n\t\t<ns2:Ask Restitution="%(ask_restitution)s" Payment="%(ask_payment)s"/>' % (file_data)
        rslt += '\n\t\t<ns2:Comment>%(comments)s</ns2:Comment>' % (file_data)
        rslt += '\n\t</ns2:VATDeclaration> \n</ns2:VATConsignment>'

        return rslt.encode()

    def _split_vat_number_and_country_code(self, vat_number):
        """
        Even with base_vat, the vat number doesn't necessarily starts
        with the country code
        We should make sure the vat is set with the country code
        to avoid submitting this declaration with a wrong vat number
        """
        vat_number = vat_number.replace(' ', '').upper()
        try:
            int(vat_number[:2])
            country_code = None
        except ValueError:
            country_code = vat_number[:2]
            vat_number = vat_number[2:]

        return vat_number, country_code

    def _get_popup_messages(self, line_balance, carryover_balance, options, tax_report_line):
        country_id = self.env['account.tax.report'].browse(options['tax_report']).country_id
        if country_id.code != 'BE':
            return super()._get_popup_messages(line_balance, carryover_balance, options, tax_report_line)
        return {
            'positive': {
                'description1': _("This amount in the XML file will be increased by the positive amount from"),
                'description2': _(" past period(s), previously stored on the corresponding tax line."),
                'description3': _("The amount in the xml will be : %s", self.format_value(line_balance)),
            },
            'negative': {
                'description1': _("This amount in the XML file will be reduced by the negative amount from"),
                'description2': _(" past period(s), previously stored on the corresponding tax line."),
                'description3': _("The amount in the xml will be : %s", self.format_value(line_balance)),
            },
            'out_of_bounds': {
                'description1': _("This amount in the XML file will be set to %s.", self.format_value(line_balance)),
                'description2': _("The difference will be carried over to the next period's declaration."),
            },
            'balance': _("The carried over balance will be : %s", carryover_balance),
        }
