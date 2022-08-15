# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import zipfile
import tempfile
import base64
from collections import Counter
from lxml import etree
from operator import itemgetter
from itertools import groupby

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class ResPartner(models.Model):
    _inherit = 'res.partner'

    citizen_identification = fields.Char(string="Citizen Identification",
                    help="This code corresponds to the personal identification number for the tax authorities.\nMore information here:\nhttps://ec.europa.eu/taxation_customs/tin/pdf/fr/TIN_-_subject_sheet_-_3_examples_fr.pdf")
    form_file = fields.Binary(readonly=True, help="Technical field to store all forms file.")

    def create_281_50_form(self):
        return {
            "name": _("Create forms 281.50"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_be_reports.281_50_wizard",
            "views": [[False, "form"]],
            "target": "new",
        }

    def _generate_281_50_form(self, file_type, wizard_values):
        '''
        Main function for the creation of the 281.50 form.\n
        This function calls severales functions to create a dictionary
        and send it into two templates.\n
        One template for the creation of the XML file and another one
        for the creation of the PDF file.\n
        When the two files are created, we send these files to the
        partner.\n
        :param file_type: List of tuple, could be xml, pdf or booth.
        :param wizard_values: Dictionary including some basic information
        like the reference year, if it is a test file, etc.
        :returns: An action to download form files (XML and PDF).
        '''
        tag_281_50_commissions = self.env.ref('l10n_be_reports.account_tag_281_50_commissions')
        tag_281_50_fees = self.env.ref('l10n_be_reports.account_tag_281_50_fees')
        tag_281_50_atn = self.env.ref('l10n_be_reports.account_tag_281_50_atn')
        tag_281_50_exposed_expenses = self.env.ref('l10n_be_reports.account_tag_281_50_exposed_expenses')
        tags = self.env['account.account.tag'] + tag_281_50_commissions + tag_281_50_fees + tag_281_50_atn + tag_281_50_exposed_expenses

        reference_year = wizard_values['reference_year']

        commissions_per_partner = self._get_balance_per_partner(tag_281_50_commissions, reference_year)
        fees_per_partner = self._get_balance_per_partner(tag_281_50_fees, reference_year)
        atn_per_partner = self._get_balance_per_partner(tag_281_50_atn, reference_year)
        exposed_expenses_per_partner = self._get_balance_per_partner(tag_281_50_exposed_expenses, reference_year)
        paid_amount_per_partner = self._get_paid_amount_per_partner(reference_year, tags)

        if not any([commissions_per_partner, fees_per_partner, atn_per_partner, exposed_expenses_per_partner, paid_amount_per_partner]):
            raise UserError(_('There are no accounts or partner with a 281.50 tag.'))

        partners = self._get_partners(commissions_per_partner, fees_per_partner, atn_per_partner, exposed_expenses_per_partner, paid_amount_per_partner) # Get only partner with a balance > 0

        attachments = []
        for partner in partners:
            partner._check_required_values()

            partner_remunerations = {
                'commissions': commissions_per_partner.get(partner.id, 0.0),
                'fees': fees_per_partner.get(partner.id, 0.0),
                'atn': atn_per_partner.get(partner.id, 0.0),
                'exposed_expenses': exposed_expenses_per_partner.get(partner.id, 0.0),
            }
            paid_amount = paid_amount_per_partner.get(partner.id, 0.0)

            partner_information = partner._get_partner_information(partner_remunerations, paid_amount)
            values_dict = partner._generate_codes_values(wizard_values, partner_information)

            file_name = '%s_%s_281_50' % (partner.name, reference_year)
            if wizard_values.get('is_test', False):
                file_name += '_test'
            if 'xml' in file_type:
                attachments.append((file_name+'.xml', partner._generate_281_50_xml(values_dict)))
            if 'pdf' in file_type:
                attachments.append((file_name+'.pdf', partner._generate_281_50_pdf(values_dict)))

        downloaded_filename = ''
        if len(attachments) > 1: # If there are more than one file, we zip all these files.
            downloaded_filename = '281_50_forms_%s.zip' % reference_year
            with tempfile.SpooledTemporaryFile() as tmp_file: # We store the zip into a temporary file.
                with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive: # We create the zip archive.
                    for attach in attachments: # And we store each file in the archive.
                        archive.writestr(attach[0], attach[1])
                tmp_file.seek(0)
                partners.form_file = base64.b64encode(tmp_file.read())
        else: # If there is only one file, we download the file directly.
            downloaded_filename = attachments[0][0]
            partners.form_file = base64.b64encode(attachments[0][1])

        return {
            'type': 'ir.actions.act_url',
            'name': 'Download 281.50 Form',
            'url': '/web/content/res.partner/%s/form_file/%s?download=true' % (partners[0].id, downloaded_filename),
        }

    def _generate_281_50_xml(self, values_dict):
        '''
        Function to create the XML file.\n
        :param: values_dict All information about the partner
        :return: A XML file
        '''
        self.ensure_one()
        partner_id = self.parent_id and self.parent_id.id or self.id
        xml, dummy = self.env.ref('l10n_be_reports.action_report_partner_281_50_xml')._render_qweb_text(partner_id, values_dict)
        xml_element = etree.fromstring(xml)
        xml_file = etree.tostring(xml_element, xml_declaration=True, encoding='utf-8') # Well format the xml and add the xml_declaration
        return xml_file

    def _generate_281_50_pdf(self, values_dict):
        '''
        Function to create the PDF file.\n
        :param: values_dict All information about the partner
        :return: A PDF file
        '''
        self.ensure_one()
        partner_id = self.parent_id and self.parent_id.id or self.id
        pdf_file, dummy = self.env.ref('l10n_be_reports.action_report_partner_281_50_pdf').sudo()._render_qweb_pdf(partner_id, values_dict)
        return pdf_file

    def _check_required_values(self):
        '''
        This functions verifies that some fields on the company and on the user are set.\n
        Company's fields:\n
        - Street\n
        - Zip Code\n
        - City\n
        - Phone number\n
        - VAT number\n
        User's fields:\n
        - Street\n
        - Zip\n
        - Citizen id or VAT number\n
        '''
        self.ensure_one()
        current_company = self.env.company
        if not (current_company.street and current_company.zip and current_company.city and current_company.phone and current_company.vat):
            raise UserError(_("Your company is not correctly configured. Please be sure that the following pieces of information are set: street, zip, city, phone and vat"))
        if not self.parent_id:
            if not (self.street and self.zip and (self.citizen_identification or self.vat)):
                raise UserError(_("The partner %s is not correctly configured. Plsea be sure that the following pieces of information are set: street, zip code and vat.", self.name))
        elif not (self.parent_id.street and self.parent_id.zip and self.parent_id.vat):
            raise UserError(_("Partner %s is not correctly configured. Please be sure that the following pieces of information are set: street, zip code and vat.", self.parent_id.name))

    def _generate_codes_values(self, wizard_values, partner_information):
        '''
        This function generates a big dictionary including all information
        about the partner.\n
        :param: wizard_values Some basics information like the reference year, etc.
        :param: partner_information Information about the partner like his name,
        his VAT number, etc.
        :return: A dictionary with all information for the creation of the XML and PDF file.
        '''
        self.ensure_one()
        current_company = self.env.company
        return {
            'V0002': wizard_values.get('reference_year'),
            'V0010': wizard_values.get('is_test') and 'BELCOTST' or 'BELCOTAX',
            'V0011': fields.Date.today().strftime('%d-%m-%Y'),
            'V0014': current_company.name,
            'V0015': current_company.street + (current_company.street2 or ''),
            'V0016': current_company.zip,
            'V0017': current_company.city,
            'V0018': current_company.phone,
            'V0021': self.env.user.name,
            'V0022': current_company.partner_id._get_lang_code(),
            'V0023': self.env.user.email,
            'V0024': current_company.vat[2:],
            'V0025': wizard_values.get('type_sending'),
            'A1002': wizard_values.get('reference_year'),
            'A1005': current_company.vat[2:],
            'A1011': current_company.name,
            'A1013': current_company.street + (current_company.street2 or ''),
            'A1015': current_company.city,
            'A1020': 1,
            'F2002': wizard_values.get('reference_year'),
            'F2005': current_company.vat[2:],
            'F2008': 28150,
            'F2009': 0,
            'F2011': partner_information.get('nature') == '1' and partner_information.get('citizen_identification') or partner_information.get('vat'),
            'F2013': partner_information.get('name'),
            'F2015': partner_information.get('address'),
            'F2016': partner_information.get('zip'),
            'F2017': partner_information.get('city'),
            'F2028': wizard_values.get('type_treatment'),
            'F2029': 0,
            'F2105': 0,
            'F2114': 0,
            'F50_2030': partner_information.get('nature'),
            'F50_2031': partner_information.get('paid_amount') != 0 and 0 or 1,
            'F50_2059': partner_information.get('total_amount'), # Total control
            'F50_2060': partner_information.get('remunerations')['commissions'],
            'F50_2061': partner_information.get('remunerations')['fees'],
            'F50_2062': partner_information.get('remunerations')['atn'],
            'F50_2063': partner_information.get('remunerations')['exposed_expenses'],
            'F50_2064': partner_information.get('total_amount'), #Total from 2060 to 2063
            'F50_2065': partner_information.get('paid_amount'),
            'F50_2066': 0.0,
            'F50_2067': 0.0,
            'F50_2099': '', # We want no comment for this field.
            'F50_2103': '', # This field is useless, if there is a problem. Please contact avw/flg.
            'F50_2107': partner_information.get('job_position'),
            'F50_2109': partner_information.get('citizen_identification'),
            'F50_2110': partner_information.get('nature') == '2' and partner_information.get('vat') or '',
            'R8002': wizard_values.get('reference_year'),
            'R8010': 1,
            'R8011': 0,
            'R8012': partner_information.get('total_amount'),
            'R9002': wizard_values.get('reference_year'),
            'R9010': 1,
            'R9011': 1,
            'R9012': 0,
            'R9013': partner_information.get('total_amount'),
        }

    def _get_lang_code(self):
        if self.lang == 'nl_BE':
            return '1'
        elif self.lang == 'fr_BE':
            return '2'
        else:
            return '3'

    def _get_partner_information(self, partner_remuneration, paid_amount):
        self.ensure_one()
        is_company_partner = not self.is_company and self.commercial_partner_id.id != self.id
        company_partner = self.commercial_partner_id
        return {
            'name':  is_company_partner and company_partner.name or self.name,
            'address': is_company_partner and (company_partner.street + (company_partner.street2 or '')) or (self.street + (self.street2 or '')),
            'zip': is_company_partner and company_partner.zip or self.zip,
            'city': is_company_partner and company_partner.city or self.city,
            'nature': (is_company_partner or self.is_company) and '2' or '1',
            'vat': (is_company_partner or self.is_company) and company_partner.vat[2:] or '',
            'remunerations': partner_remuneration,
            'paid_amount': paid_amount,
            'total_amount': sum(partner_remuneration.values()),
            'job_position': (is_company_partner or self.is_company) and '' or self.function,
            'citizen_identification': (is_company_partner or self.is_company) and '' or self.citizen_identification,
            }

    def _get_balance_per_partner(self, tag, reference_year):
        '''
        This function gets all balance (based on account.move.line)
        for each partner following some rules:\n
            - All account.move.line have an account with the "281.50 - XXXXX" tag.\n
            - All account.move.line must be between the first day and the last day\n
            of the reference year.\n
            - All account.move.line must be in a posted account.move.\n
        These information are group by partner !
        :param accounts Account: used to compute the balance (normally account with 281.50 - XXXXX tag).
        :param reference_year: The reference year.
        :return: A dict of partner_id: balance
        '''
        accounts = self.env['account.account'].search([('tag_ids', 'in', tag.ids)])
        partner_tag_281_50 = self.env.ref('l10n_be_reports.res_partner_tag_281_50')
        if not accounts:
            return {}
        date_from = fields.Date().from_string(reference_year+'-01-01')
        date_to = fields.Date().from_string(reference_year+'-12-31')

        self._cr.execute('''
            SELECT line.partner_id, SUM(line.balance) AS balance
            FROM account_move_line line
            INNER JOIN res_partner_res_partner_category_rel partner_category
            ON line.partner_id = partner_category.partner_id
            WHERE line.partner_id in %s
            AND partner_category.category_id = %s
            AND line.account_id IN %s
            AND line.date BETWEEN %s AND %s
            AND line.parent_state = 'posted'
            AND line.company_id = %s
            GROUP BY line.partner_id
        ''', [tuple(self.ids), partner_tag_281_50.id, tuple(accounts.ids), date_from, date_to, self.env.company.id])
        balance_per_partner_list = self._cr.dictfetchall()
        tmp = {}
        for bpp in balance_per_partner_list:
            bpp['balance'] = self.filtered(lambda p: p.id == bpp['partner_id']).currency_id.round(bpp['balance'])
            tmp.update({bpp['partner_id']: bpp['balance']})

        return tmp

    def _get_partners(self, commissions, fees, atn, exposed_expenses, paid_amount_per_partner):
        '''
        This method gets all partner_ids from each list in params
        and returns a recordset of res.partner.\n
        It allows us to know all partners who have been paid.\n
        :params commissions: Dict of balance by partner for the commissions tag.
        :params fees: Dict of balance by partner for the fees tag.
        :params atn: Dict of balance by partner for the atn tag.
        :params exposed_expenses: Dict of balance by partner for the exposed_expenses tag.
        :return: A recordset of res.partner
        '''
        tmp = list(commissions) + list(fees) + list(atn) + list(exposed_expenses) + list(paid_amount_per_partner)
        partner_ids = set(tmp)
        return self.env['res.partner'].browse(partner_ids)

    def _get_paid_amount_per_partner(self, reference_year, tags):
        '''
        Get all paid amount for each partner for a specific year and the previous year.
        :params reference_year: The selected year
        :params tags: Which tags to get paid amount for
        :return: A dict of paid amount (for the specific year and the previous year) per partner.
        '''
        partner_tag_281_50 = self.env.ref('l10n_be_reports.res_partner_tag_281_50')
        date_from = reference_year+'-01-01'
        date_to = reference_year+'-12-31'
        max_date_from = date_from
        max_date_to = date_to
        company_id = self.env.company.id
        self._cr.execute('''
            SELECT sub.partner_id, SUM(sub.paid_amount) AS paid_amount FROM
            (SELECT mv.partner_id AS partner_id,
            (paid_per_partner.paid_amount/SUM(mv.amount_total)) * SUM(line1.balance) AS paid_amount
            FROM
            (SELECT aml.partner_id, SUM(apr.amount) AS paid_amount
            FROM account_move_line aml
            INNER JOIN account_partial_reconcile apr ON aml.id = apr.credit_move_id
            INNER JOIN account_move_line aml2 ON aml2.id = apr.debit_move_id
            WHERE aml.parent_state = 'posted' AND aml2.parent_state = 'posted'
            AND aml.company_id = %s AND apr.max_date <= %s
            AND aml.date BETWEEN %s AND %s
            GROUP BY aml.partner_id) paid_per_partner, account_move mv
            INNER JOIN account_move_line line1 ON line1.move_id = mv.id
            INNER JOIN account_account_account_tag account_tag
            ON line1.account_id = account_tag.account_account_id
            INNER JOIN res_partner_res_partner_category_rel partner_category
            ON mv.partner_id = partner_category.partner_id
            WHERE account_tag.account_account_tag_id IN %s
            AND partner_category.category_id = %s
            AND mv.state = 'posted' AND mv.company_id = %s
            AND mv.date BETWEEN %s AND %s
            AND mv.partner_id IN %s
            AND mv.partner_id = paid_per_partner.partner_id
            GROUP BY mv.partner_id, paid_per_partner.paid_amount
            ORDER BY mv.partner_id ASC) sub
            GROUP BY sub.partner_id
        ''', [company_id, max_date_to, date_from, date_to, tuple(tags.ids), partner_tag_281_50.id, company_id, date_from, date_to, tuple(self.ids)])
        amount_per_partner = self._cr.dictfetchall()

        dict_amount_per_partner = {}
        for app in amount_per_partner:
            app['paid_amount'] = self.filtered(lambda p: p.id == app['partner_id']).currency_id.round(app['paid_amount'])
            dict_amount_per_partner.update({app['partner_id']: app['paid_amount']})

        # Get all paid amount for each partner for the previous year
        # Pay attention that the SQL query is not exactly the same as above.
        date_from = str(int(reference_year)-1)+'-01-01'
        date_to = str(int(reference_year)-1)+'-12-31'
        self._cr.execute('''
            SELECT sub.partner_id, SUM(sub.paid_amount) AS paid_amount FROM
            (SELECT mv.partner_id AS partner_id,
            (paid_per_partner.paid_amount/SUM(mv.amount_total)) * SUM(line1.balance) AS paid_amount
            FROM
            (SELECT aml.partner_id, SUM(apr.amount) AS paid_amount
            FROM account_move_line aml
            INNER JOIN account_partial_reconcile apr ON aml.id = apr.credit_move_id
            INNER JOIN account_move_line aml2 ON aml2.id = apr.debit_move_id
            WHERE aml.parent_state = 'posted' AND aml2.parent_state = 'posted'
            AND aml.company_id = %s AND apr.max_date BETWEEN %s AND %s
            AND aml.date BETWEEN %s AND %s
            GROUP BY aml.partner_id) paid_per_partner, account_move mv
            INNER JOIN account_move_line line1 ON line1.move_id = mv.id
            INNER JOIN account_account_account_tag account_tag
            ON line1.account_id = account_tag.account_account_id
            INNER JOIN res_partner_res_partner_category_rel partner_category
            ON mv.partner_id = partner_category.partner_id
            WHERE account_tag.account_account_tag_id IN %s
            AND partner_category.category_id = %s
            AND mv.state = 'posted' AND mv.company_id = %s
            AND mv.date BETWEEN %s AND %s
            AND mv.partner_id IN %s
            AND mv.partner_id = paid_per_partner.partner_id
            GROUP BY mv.partner_id, paid_per_partner.paid_amount
            ORDER BY mv.partner_id ASC) sub
            GROUP BY sub.partner_id
        ''', [company_id, max_date_from, max_date_to, date_from, date_to, tuple(tags.ids), partner_tag_281_50.id, company_id, date_from, date_to, tuple(self.ids)])
        amount_for_previous_year = self._cr.dictfetchall()

        dict_amount_for_previous_year = {}
        for app in amount_for_previous_year:
            app['paid_amount'] = self.filtered(lambda p: p.id == app['partner_id']).currency_id.round(app['paid_amount'])
            dict_amount_for_previous_year.update({app['partner_id']: app['paid_amount']})

        # Merge amount for previous year and amount for reference_year
        return Counter(dict_amount_per_partner) + Counter(dict_amount_for_previous_year)
