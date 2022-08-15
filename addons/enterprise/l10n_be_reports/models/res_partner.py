# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import zipfile
import tempfile
import base64
import re
from stdnum.be import vat
from collections import Counter
from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError, RedirectWarning

ONSS_COUNTRY_CODE_MAPPING = {
    'AD': '00102', 'AE': '00260', 'AF': '00251', 'AG': '00403', 'AI': '00490', 'AL': '00101', 'AM': '00249',
    'AO': '00341', 'AR': '00511', 'AS': '00690', 'AT': '00105', 'AU': '00611', 'AZ': '00250', 'BA': '00149',
    'BB': '00423', 'BD': '00237', 'BE': '00000', 'BF': '00308', 'BG': '00106', 'BH': '00268', 'BI': '00303',
    'BJ': '00310', 'BM': '00485', 'BN': '00224', 'BO': '00512', 'BR': '00513', 'BS': '00425', 'BT': '00223',
    'BW': '00302', 'BY': '00142', 'BZ': '00430', 'CA': '00401', 'CD': '00306', 'CF': '00305', 'CG': '00307',
    'CH': '00127', 'CI': '00309', 'CK': '00687', 'CL': '00514', 'CM': '00304', 'CN': '00218', 'CO': '00515',
    'CR': '00411', 'CU': '00412', 'CV': '00339', 'CY': '00107', 'CZ': '00140', 'DE': '00103', 'DJ': '00345',
    'DK': '00108', 'DM': '00480', 'DO': '00427', 'DZ': '00351', 'EC': '00516', 'EE': '00136', 'EG': '00352',
    'EH': '00388', 'ER': '00349', 'ES': '00109', 'ET': '00311', 'FI': '00110', 'FJ': '00617', 'FK': '00580',
    'FM': '00602', 'FR': '00111', 'GA': '00312', 'GB': '00112', 'GD': '00426', 'GE': '00253', 'GF': '00581',
    'GH': '00314', 'GI': '00180', 'GL': '00498', 'GM': '00313', 'GN': '00315', 'GP': '00496', 'GQ': '00337',
    'GR': '00114', 'GT': '00413', 'GU': '00681', 'GW': '00338', 'GY': '00521', 'HK': '00234', 'HN': '00414',
    'HR': '00146', 'HT': '00419', 'HU': '00115', 'ID': '00208', 'IE': '00116', 'IL': '00256', 'IN': '00207',
    'IQ': '00254', 'IR': '00255', 'IS': '00117', 'IT': '00128', 'JM': '00415', 'JO': '00257', 'JP': '00209',
    'KE': '00336', 'KG': '00226', 'KH': '00216', 'KI': '00622', 'KM': '00343', 'KN': '00431', 'KP': '00219',
    'KR': '00206', 'KW': '00264', 'KY': '00492', 'KZ': '00225', 'LA': '00210', 'LB': '00258', 'LC': '00428',
    'LI': '00118', 'LK': '00203', 'LR': '00318', 'LS': '00301', 'LT': '00137', 'LU': '00113', 'LV': '00135',
    'LY': '00353', 'MA': '00354', 'MC': '00120', 'MD': '00144', 'ME': '00151', 'MG': '00324', 'MH': '00603',
    'MK': '00148', 'ML': '00319', 'MM': '00201', 'MN': '00221', 'MO': '00281', 'MQ': '00497', 'MR': '00355',
    'MS': '00493', 'MT': '00119', 'MU': '00317', 'MV': '00222', 'MW': '00358', 'MX': '00416', 'MY': '00212',
    'MZ': '00340', 'NA': '00384', 'NC': '00683', 'NE': '00321', 'NG': '00322', 'NI': '00417', 'NL': '00129',
    'NO': '00121', 'NP': '00213', 'NR': '00615', 'NU': '00604', 'NZ': '00613', 'OM': '00266', 'PA': '00418',
    'PE': '00518', 'PF': '00684', 'PG': '00619', 'PH': '00214', 'PK': '00259', 'PL': '00122', 'PM': '00495',
    'PN': '00692', 'PR': '00487', 'PS': '00271', 'PT': '00123', 'PW': '00679', 'PY': '00517', 'QA': '00267',
    'RE': '00387', 'RO': '00124', 'RS': '00152', 'RU': '00145', 'RW': '00327', 'SA': '00252', 'SB': '00623',
    'SC': '00342', 'SD': '00356', 'SE': '00126', 'SG': '00205', 'SH': '00389', 'SI': '00147', 'SK': '00141',
    'SL': '00328', 'SM': '00125', 'SN': '00320', 'SO': '00329', 'SR': '00522', 'SS': '00365', 'SV': '00421',
    'SY': '00261', 'SZ': '00347', 'TC': '00488', 'TD': '00333', 'TG': '00334', 'TH': '00235', 'TJ': '00228',
    'TL': '00282', 'TM': '00229', 'TN': '00357', 'TO': '00616', 'TR': '00262', 'TT': '00422', 'TV': '00621',
    'TW': '00204', 'TZ': '00332', 'UA': '00143', 'UG': '00323', 'US': '00402', 'UY': '00519', 'UZ': '00227',
    'VA': '00133', 'VC': '00429', 'VE': '00520', 'VG': '00479', 'VI': '00478', 'VN': '00220', 'VU': '00624',
    'WF': '00689', 'WS': '00614', 'XK': '00153', 'YE': '00270', 'ZA': '00325', 'ZM': '00335', 'ZW': '00344'
}

def _vat_to_bce(vat_number: str) -> str:
    return vat.compact(vat_number)

def format_if_float(amount):
    return f"{amount * 100:.0f}" if isinstance(amount, float) else amount  # amounts in € requires to be formatted for xml

def format_325_form_values(values):
    tmp_dict = {}
    for key, value in values.items():
        if isinstance(value, list):
            tmp_dict[key] = [format_325_form_values(v) for v in value]
        else:
            tmp_dict[key] = format_if_float(value)
    return tmp_dict


class ResPartner(models.Model):
    _inherit = 'res.partner'

    citizen_identification = fields.Char(
        string="Citizen Identification",
        help="This code corresponds to the personal identification number for the tax authorities.\n"
             "More information here:\n"
             "https://ec.europa.eu/taxation_customs/tin/pdf/fr/TIN_-_subject_sheet_-_3_examples_fr.pdf"
    )
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
        debtor = self.env.company.partner_id
        sender = wizard_values.get('sender') or self.env.company.partner_id
        partner_325_form = self._generate_form_325_values(debtor, sender, wizard_values)

        attachments = []
        file_name = f"{wizard_values.get('reference_year')}_281_50{wizard_values.get('is_test') and '_test' or ''}"
        if 'xml' in file_type:
            attachments.append((f"{file_name}.xml", debtor._generate_325_form_xml(partner_325_form)))
        if 'pdf' in file_type:
            for fiche_281_50 in partner_325_form.pop('Fiches28150'):
                pdf_file = debtor._generate_281_50_form_pdf({**partner_325_form, **fiche_281_50})
                vendor_name = fiche_281_50.get('F2013')
                attachments.append((f"{vendor_name}-{file_name}.pdf", pdf_file))

        if len(attachments) > 1: # If there are more than one file, we zip all these files.
            downloaded_filename = f"281_50_forms_{wizard_values.get('reference_year')}.zip"
            with tempfile.SpooledTemporaryFile() as tmp_file: # We store the zip into a temporary file.
                with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive: # We create the zip archive.
                    for attach in attachments: # And we store each file in the archive.
                        archive.writestr(attach[0], attach[1])
                tmp_file.seek(0)
                debtor.form_file = base64.b64encode(tmp_file.read())
        else: # If there is only one file, we download the file directly.
            downloaded_filename = attachments[0][0]
            debtor.form_file = base64.b64encode(attachments[0][1])

        return {
            'type': 'ir.actions.act_url',
            'name': _("Download 281.50 Form"),
            'url': f"/web/content/res.partner/{debtor.id}/form_file/{downloaded_filename}?download=true"
        }

    def _generate_form_325_values(self, debtor, sender, wizard_values):
        reference_year = wizard_values['reference_year']

        sender._check_partner_281_50_required_values(check_phone_number=True)
        debtor._check_partner_281_50_required_values(check_phone_number=True)

        amount_per_partner = self._get_remuneration_281_50_per_partner(reference_year)

        partner_281_50_forms = []
        for form_number, (partner, remuneration) in enumerate(amount_per_partner.items(), start=1):
            partner_281_50_forms.append(partner._get_281_50_partner_fiche(
                _vat_to_bce(debtor.vat),
                remuneration,
                wizard_values,
                form_number
            ))

        debtor_form = debtor._get_debtor_form(partner_281_50_forms, reference_year)
        return sender._get_sender_form(wizard_values, debtor_form)

    def _generate_325_form_xml(self, form_values):
        """ Function to create the XML file.
            :param: form_values All information about the partner
            :return: A XML stringified
        """
        self.ensure_one()
        formated_form_values = format_325_form_values(form_values)
        xml, dummy = self.env.ref('l10n_be_reports.action_report_partner_281_50_xml')._render_qweb_text(self, formated_form_values)
        xml_element = etree.fromstring(xml)
        return etree.tostring(xml_element, xml_declaration=True, encoding='utf-8') # Well format the xml and add the xml_declaration

    def _generate_281_50_form_pdf(self, form_values):
        """ Function to create the PDF file.
            :param: values_dict All information about the partner
            :return: A PDF file
        """
        self.ensure_one()
        pdf_file, dummy = self.env.ref('l10n_be_reports.action_report_partner_281_50_pdf')._render_qweb_pdf(self, form_values)
        return pdf_file

    def _check_partner_281_50_required_values(self, check_phone_number=False):
        """ This function verifies that some fields on partners are set.
            Partner's fields:
            - Street
            - Zip
            - Citizen id or VAT number
            - Country
        """
        partner_missing_data = self._get_partner_missing_data(check_phone_number=check_phone_number)
        if partner_missing_data:
            raise RedirectWarning(_(
                "Some partners are not correctly configured. "
                "Please be sure that the following pieces of information are set: "
                "street, zip code, country and vat or citizen identification."
            ), partner_missing_data._open_partner_with_missing_data(), _("Open list"))

    def _get_partner_missing_data(self, check_phone_number=False):
        partner_missing_data = self.env['res.partner']
        for partner in self:
            partner = partner.commercial_partner_id
            if not all([partner.street, partner.zip, partner.country_id, (partner.citizen_identification or partner.vat)]):
                partner_missing_data |= partner
            if check_phone_number and not partner.phone:
                partner_missing_data |= partner
        return partner_missing_data

    def _open_partner_with_missing_data(self):
        required_field_view_list = self.env.ref('l10n_be_reports.view_partner_28150_required_fields')
        required_field_view_form = self.env.ref('l10n_be_reports.res_partner_view_form_281_50_required_field')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Missing partner data"),
            'res_model': 'res.partner',
            'views': [(required_field_view_list.id, 'list'), (required_field_view_form.id, 'form')],
            'domain': [('id', 'in', self.ids)],
        }

    def _get_remuneration_281_50_per_partner(self, reference_year):
        tag_281_50_atn, tag_281_50_commissions, tag_281_50_exposed_expenses, tag_281_50_fees = self._get_281_50_tags()

        account_281_50_tags = tag_281_50_commissions + tag_281_50_fees + tag_281_50_atn + tag_281_50_exposed_expenses

        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['account.partial.reconcile'].flush()
        commissions_per_partner = self._get_balance_per_partner(tag_281_50_commissions, reference_year)
        fees_per_partner = self._get_balance_per_partner(tag_281_50_fees, reference_year)
        atn_per_partner = self._get_balance_per_partner(tag_281_50_atn, reference_year)
        exposed_expenses_per_partner = self._get_balance_per_partner(tag_281_50_exposed_expenses, reference_year)
        paid_amount_per_partner = self._get_paid_amount_per_partner(reference_year, account_281_50_tags)

        partner_ids = self.env['res.partner'].browse(
            set(
                list(commissions_per_partner)
                + list(fees_per_partner)
                + list(atn_per_partner)
                + list(exposed_expenses_per_partner)
                + list(paid_amount_per_partner)
            )
        )

        if not partner_ids:
            raise UserError(_(
                "Either there isn't any account nor partner with a 281.50 tag "
                "or there isn't any amount to report for this period."
            ))

        partner_ids._check_partner_281_50_required_values()

        amount_per_partner = {
            partner_id: {
                'commissions': commissions_per_partner.get(partner_id.id, 0.0),
                'fees': fees_per_partner.get(partner_id.id, 0.0),
                'atn': atn_per_partner.get(partner_id.id, 0.0),
                'exposed_expenses': exposed_expenses_per_partner.get(partner_id.id, 0.0),
                'paid_amount': paid_amount_per_partner.get(partner_id.id, 0.0),
            }
            for partner_id in partner_ids.sorted(lambda p: (p.zip, p.name))
        }
        return amount_per_partner

    def _get_281_50_tags(self):
        missing_tag = []
        def try_to_load_tags(xml_id):
            tag = self.env.ref(xml_id, raise_if_not_found=False)
            if not tag:
                missing_tag.append(xml_id)
            return tag

        tag_281_50_commissions = try_to_load_tags('l10n_be_reports.account_tag_281_50_commissions')
        tag_281_50_fees = try_to_load_tags('l10n_be_reports.account_tag_281_50_fees')
        tag_281_50_atn = try_to_load_tags('l10n_be_reports.account_tag_281_50_atn')
        tag_281_50_exposed_expenses = try_to_load_tags('l10n_be_reports.account_tag_281_50_exposed_expenses')
        if missing_tag:
            raise UserError(_("Internal reference to the following 281.50 tags are missing:\n") + missing_tag)
        return tag_281_50_atn, tag_281_50_commissions, tag_281_50_exposed_expenses, tag_281_50_fees

    def _get_sender_form(self, wizard_values, debtor_form):
        """:return a dict containing the following structure (which follow the belcotax standard for xml)
        - sender information
        - list of aangiften: (report)
            - debtor information
            - list of 325.50:
                - vendor information
                - amounts of expense for this partner by type
                - amount paid to this partner related to the previous amounts
        """
        self.ensure_one()
        return {
            'V0002': wizard_values.get('reference_year'),
            'V0010': wizard_values.get('is_test') and 'BELCOTST' or 'BELCOTAX',
            'V0011': fields.Date.today().strftime('%d-%m-%Y'),
            'V0014': self.name,
            'V0015': f"{self.street}{(', ' + self.street2) if self.street2 else ''}",
            'V0016': self.zip,
            'V0017': self.city,
            'V0018': re.sub(r"\D", '', self.phone),
            'V0021': self.env.user.name,
            'V0022': self._get_lang_code(),
            'V0023': self.env.user.email,
            'V0024': _vat_to_bce(self.vat),
            'V0025': wizard_values.get('type_sending'),
            **debtor_form,
            'R9002': wizard_values.get('reference_year'),
            'R9010': 3,  # from the xml validation: number of report (aangifte) + 2
            'R9011': 2 + debtor_form.get('R8010'),  # sum of all R8010 + 2 (1 for the V fields and 1 for R fields)
            'R9012': debtor_form.get('R8011'),  # sum all sequences
            'R9013': debtor_form.get('R8012'),  # sum of all 8012
        }

    def _get_debtor_form(self, partner_281_50_forms, reference_year):
        self.ensure_one()
        debtor_bce_number = _vat_to_bce(self.vat)
        return {
            'A1002': reference_year,
            'A1005': debtor_bce_number,
            'A1011': self.name,
            'A1013': f"{self.street}{(', ' + self.street2) if self.street2 else ''}",
            'A1014': self.zip,
            'A1015': self.city,
            'A1016': ONSS_COUNTRY_CODE_MAPPING.get(self.country_id.code),
            'A1020': 1,
            'Fiches28150': partner_281_50_forms, # Official name from the XML
            'R8002': reference_year,
            'R8005': debtor_bce_number,
            'R8010': 2 + len(partner_281_50_forms),  # number of record for this declaration: A1XXX + R8XXX + Fiches28150
            'R8011': sum((form.get('F2009') for form in partner_281_50_forms)), # Sum sequence
            'R8012': sum((p.get('F50_2059') for p in partner_281_50_forms)), # Total control
        }

    def _get_281_50_partner_fiche(self, income_debtor_bce_number, remuneration, wizard_values, form_number):
        self.ensure_one()
        partner_information = self._get_partner_information()
        is_partner_from_belgium = partner_information.get('country_code') == 'BE'
        total_remuneration = sum([
            remuneration['commissions'],
            remuneration['fees'],
            remuneration['atn'],
            remuneration['exposed_expenses'],
        ])
        sum_control = sum([
            remuneration['commissions'],
            remuneration['fees'],
            remuneration['atn'],
            remuneration['exposed_expenses'],
            total_remuneration,
            remuneration['paid_amount'],
        ])

        return {
            # F2XXX: info for this 281.XX tax form
            'F2002': wizard_values.get('reference_year'),
            'F2005': income_debtor_bce_number,
            'F2008': 28150,  # fiche type
            'F2009': form_number,  # id number of this fiche for this beneficiary
            'F2013': partner_information.get('name')[:41],  # max length accepted in xml
            'F2015': partner_information.get('address'),
            'F2016': partner_information.get('zip') if is_partner_from_belgium else '',
            'F2017': partner_information.get('city'),
            'F2028': wizard_values.get('type_treatment'),  # fiche treatment: 0 -> ordinary, 1 -> modification, 2 -> adding, 3 -> cancellation
            'F2029': 0,
            'F2105': 0,  # birthplace
            'F2018': ONSS_COUNTRY_CODE_MAPPING.get(partner_information.get('country_code')),
            'F2018_display': partner_information.get('country_name'),
            'F2112': '' if is_partner_from_belgium else partner_information.get('zip'),
            'F2114': '',  # firstname: full name is set on F2013
            # F50_2XXX: info for this 281.50 tax form
            'F50_2030': partner_information.get('nature'),
            'F50_2031': 0 if remuneration['paid_amount'] != 0 else 1,
            'F50_2059': sum_control,  # Total control : sum 2060 to 2088 for this 281.50 form
            'F50_2060': remuneration['commissions'],
            'F50_2061': remuneration['fees'],
            'F50_2062': remuneration['atn'],
            'F50_2063': remuneration['exposed_expenses'],
            'F50_2064': total_remuneration,  # Total from 2060 to 2063
            'F50_2065': remuneration['paid_amount'],
            'F50_2065_display': 'NÉANT' if remuneration['paid_amount'] == 0 else (0 if remuneration['paid_amount'] == total_remuneration else remuneration['paid_amount']),
            'F50_2066': 0,  # irrelevant: sport remuneration
            'F50_2067': 0,  # irrelevant: manager remuneration
            'F50_2099': '',  # further comments concerning amounts from 2060 to 2067
            'F50_2103': '',  # nature of the amounts
            'F50_2107': partner_information.get('job_position'),
            'F50_2109': partner_information.get('citizen_identification'),
            'F50_2110': partner_information.get('bce_number') if is_partner_from_belgium else '',  # KBO/BCE number
            'F50_2110_display': partner_information.get('bce_number'),  # For the PDF, we want to display the KBO/BCE number
        }

    def _get_lang_code(self):
        return {
            'nl': '1',
            'fr': '2',
            'de': '3',
        }.get((self.lang or "")[:2], '2')

    def _get_partner_information(self):
        self.ensure_one()
        is_company_partner = not self.is_company and self.commercial_partner_id.id != self.id
        company_partner = self.commercial_partner_id
        partner = company_partner if is_company_partner else self
        return {
            'name':  partner.name,
            'address': ", ".join(street for street in [partner.street, partner.street2] if street),
            'country_code': partner.country_id.code,
            'country_name': partner.country_id.name,
            'zip': partner.zip,
            'city': partner.city,
            'nature': '2' if partner.is_company else '1',
            'bce_number': _vat_to_bce(company_partner.vat) if partner.is_company else '',
            'job_position': '' if partner.is_company else self.function,
            'citizen_identification': '' if partner.is_company else self.citizen_identification,
        }

    def _get_balance_per_partner(self, tag_ids, reference_year):
        """ This function gets all balance (based on account.move.line)
            for each partner following some rules:\n
                - All account.move.line have an account with the "281.50 - XXXXX" tag.\n
                - All account.move.line must be between the first day and the last day\n
                of the reference year.\n
                - All account.move.line must be in a posted account.move.\n
            These information are group by partner !
            :param tag_ids tag_ids: used to compute the balance (normally account with 281.50 - XXXXX tag).
            :param reference_year: The reference year.
            :return: A dict of partner_id: balance
        """
        accounts = self.env['account.account'].search([('tag_ids', 'in', tag_ids.ids)])
        if not accounts:
            return {}
        move_date_from = fields.Date().from_string(f'{reference_year}-01-01')
        move_date_to = fields.Date().from_string(f'{reference_year}-12-31')

        self.env.cr.execute("""
            SELECT COALESCE(move.commercial_partner_id, line.partner_id), ROUND(SUM(line.balance), currency.decimal_places) AS balance
              FROM account_move_line line
              JOIN account_move move ON move.id = line.move_id
              JOIN res_currency AS currency ON line.company_currency_id = currency.id
             WHERE COALESCE(move.commercial_partner_id, line.partner_id) = ANY(%(partners)s)
               AND line.account_id = ANY(%(accounts)s)
               AND line.date BETWEEN %(move_date_from)s AND %(move_date_to)s
               AND line.parent_state = 'posted'
               AND line.company_id = %(company)s
          GROUP BY COALESCE(move.commercial_partner_id, line.partner_id), currency.id
        """, {
            'partners': self.ids,
            'accounts': accounts.ids,
            'move_date_from': move_date_from,
            'move_date_to': move_date_to,
            'company': self.env.company.id,
        })
        return dict(self.env.cr.fetchall())

    def _get_paid_amount_per_partner(self, reference_year, tags):
        """ Get all paid amount for each partner for a specific year and the previous year.
            :param reference_year: The selected year
            :param tags: Which tags to get paid amount for
            :return: A dict of paid amount (for the specific year and the previous year) per partner.
        """
        self.env.cr.execute("""
          WITH paid_expense_line AS (
              SELECT aml_payable.id AS payable_id,
                     COALESCE(move_payable.commercial_partner_id, aml_payable.partner_id) as partner_id,
                     aml_expense.move_id,
                     aml_expense.balance
                FROM account_move_line aml_payable
                JOIN account_move move_payable ON aml_payable.move_id = move_payable.id
                JOIN account_account account ON aml_payable.account_id = account.id
                JOIN account_move_line aml_expense ON aml_payable.move_id = aml_expense.move_id
                JOIN account_account_account_tag account_tag_rel ON aml_expense.account_id = account_tag_rel.account_account_id
               WHERE account_tag_rel.account_account_tag_id = ANY(%(tag_ids)s)
                 AND account.internal_type IN ('payable', 'receivable')
                 AND aml_payable.parent_state = 'posted'
                 AND aml_payable.company_id = %(company_id)s
                 AND aml_payable.date BETWEEN %(invoice_date_from)s AND %(invoice_date_to)s
                 AND aml_expense.date BETWEEN %(invoice_date_from)s AND %(invoice_date_to)s
                 AND COALESCE(move_payable.commercial_partner_id, aml_payable.partner_id) = ANY(%(partner_ids)s)
          ),
          amount_paid_per_partner_based_on_bill_reconciled AS (
              SELECT paid_expense_line.partner_id AS partner_id,
                     -- amount_total_signed is negative for in_invoice
                     SUM((apr.amount / - move.amount_total_signed) * (paid_expense_line.balance)) AS paid_amount
                FROM paid_expense_line
                JOIN account_move move ON paid_expense_line.move_id = move.id
                JOIN account_partial_reconcile apr ON paid_expense_line.payable_id = apr.credit_move_id
                JOIN account_move_line aml_payment ON aml_payment.id = apr.debit_move_id
               WHERE aml_payment.parent_state = 'posted'
                 AND apr.max_date BETWEEN %(payment_date_from)s AND %(payment_date_to)s
            GROUP BY paid_expense_line.partner_id
          ),
          amount_send_to_expense_without_bill AS (
              SELECT line.partner_id,
                     line.balance AS paid_amount
                FROM account_move_line AS line
                JOIN account_journal journal ON journal.id = line.journal_id
                JOIN account_account_account_tag account_tag_rel ON line.account_id = account_tag_rel.account_account_id
               WHERE line.company_id = %(company_id)s
                 AND journal.type IN ('bank', 'cash')
                 AND line.parent_state = 'posted'
                 AND account_tag_rel.account_account_tag_id = ANY(%(tag_ids)s)
                 AND line.date BETWEEN %(payment_date_from)s AND %(payment_date_to)s
          ),
          amount_paid AS (
              SELECT * FROM amount_paid_per_partner_based_on_bill_reconciled
           UNION ALL
              SELECT * FROM amount_send_to_expense_without_bill
          )
          SELECT sub.partner_id, ROUND(SUM(sub.paid_amount), %(decimal_places)s) AS paid_amount
            FROM amount_paid AS sub
        GROUP BY sub.partner_id
          """, {
            'company_id': self.env.company.id,
            'payment_date_from': f'{reference_year}-01-01',
            'payment_date_to': f'{reference_year}-12-31',
            'invoice_date_from': f'{int(reference_year) - 1}-01-01',
            'invoice_date_to': f'{reference_year}-12-31',
            'tag_ids': tags.ids,
            'partner_ids': self.ids,
            'decimal_places': self.env.company.currency_id.decimal_places,
        })
        return dict(self.env.cr.fetchall())
