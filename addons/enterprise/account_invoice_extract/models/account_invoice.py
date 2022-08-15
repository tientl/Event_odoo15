# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import api, fields, models, tools, _, _lt
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError, ValidationError , UserError
from odoo.tests.common import Form
from odoo.tools import float_compare, mute_logger
from odoo.tools.misc import clean_context
import logging
import math
import re
import json
import string

from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

PARTNER_AUTOCOMPLETE_ENDPOINT = 'https://partner-autocomplete.odoo.com'
EXTRACT_ENDPOINT = 'https://iap-extract.odoo.com'
CLIENT_OCR_VERSION = 120

# list of result id that can be sent by iap-extract
SUCCESS = 0
NOT_READY = 1
ERROR_INTERNAL = 2
ERROR_NOT_ENOUGH_CREDIT = 3
ERROR_DOCUMENT_NOT_FOUND = 4
ERROR_NO_DOCUMENT_NAME = 5
ERROR_UNSUPPORTED_IMAGE_FORMAT = 6
ERROR_FILE_NAMES_NOT_MATCHING = 7
ERROR_NO_CONNECTION = 8
ERROR_SERVER_IN_MAINTENANCE = 9
ERROR_PASSWORD_PROTECTED = 10
ERROR_TOO_MANY_PAGES = 11
ERROR_INVALID_ACCOUNT_TOKEN = 12

# codes above 100 are reserved for warnings
# as warnings aren't mutually exclusive, the warning codes are summed, the result represent the combination of warnings
# for example, WARNING_BASE_VALUE + WARNING_DUPLICATE_VENDOR_REFERENCE + WARNING_DATE_PRIOR_OF_LOCK_DATE means that both of these warnings should be displayed
# these constants needs to be a power of 2
WARNING_BASE_VALUE = 99
WARNING_DUPLICATE_VENDOR_REFERENCE = 1
WARNING_DATE_PRIOR_OF_LOCK_DATE = 2

ERROR_MESSAGES = {
    ERROR_INTERNAL: _lt("An error occurred"),
    ERROR_DOCUMENT_NOT_FOUND: _lt("The document could not be found"),
    ERROR_NO_DOCUMENT_NAME: _lt("No document name provided"),
    ERROR_UNSUPPORTED_IMAGE_FORMAT: _lt("Unsupported image format"),
    ERROR_FILE_NAMES_NOT_MATCHING: _lt("You must send the same quantity of documents and file names"),
    ERROR_NO_CONNECTION: _lt("Server not available. Please retry later"),
    ERROR_SERVER_IN_MAINTENANCE: _lt("Server is currently under maintenance. Please retry later"),
    ERROR_PASSWORD_PROTECTED: _lt("Your PDF file is protected by a password. The OCR can't extract data from it"),
    ERROR_TOO_MANY_PAGES: _lt("Your invoice is too heavy to be processed by the OCR. Try to reduce the number of pages and avoid pages with too many text"),
    ERROR_INVALID_ACCOUNT_TOKEN: _lt("The 'invoice_ocr' IAP account token is invalid. Please delete it to let Odoo generate a new one or fill it with a valid token."),
}
WARNING_MESSAGES = {
    WARNING_DUPLICATE_VENDOR_REFERENCE: _lt("Warning: there is already a vendor bill with this reference (%s)"),
    WARNING_DATE_PRIOR_OF_LOCK_DATE: _lt("Warning: as the bill date is prior to the lock date, the accounting date was set for the first following day"),
}


class AccountInvoiceExtractionWords(models.Model):
    _name = "account.invoice_extract.words"
    _description = "Extracted words from invoice scan"

    invoice_id = fields.Many2one("account.move", help="Invoice id")
    field = fields.Char()
    selected_status = fields.Integer("Invoice extract selected status.",
                                     help="0 for 'not selected', 1 for 'ocr selected with no user selection' and 2 for 'ocr selected with user selection (user may have selected the same box)")
    user_selected = fields.Boolean()
    word_text = fields.Char()
    word_page = fields.Integer()
    word_box_midX = fields.Float()
    word_box_midY = fields.Float()
    word_box_width = fields.Float()
    word_box_height = fields.Float()
    word_box_angle = fields.Float()


class AccountMove(models.Model):
    _inherit = ['account.move']
    duplicated_vendor_ref = fields.Char(string='Duplicated vendor reference')

    @api.depends('extract_status_code')
    def _compute_error_message(self):
        for record in self:
            if record.extract_status_code not in (SUCCESS, NOT_READY):
                warnings = record.get_warnings()
                if warnings:
                    warnings_messages = []
                    if WARNING_DUPLICATE_VENDOR_REFERENCE in warnings:
                        warnings_messages.append(str(WARNING_MESSAGES[WARNING_DUPLICATE_VENDOR_REFERENCE]) % record.duplicated_vendor_ref)
                    if WARNING_DATE_PRIOR_OF_LOCK_DATE in warnings:
                        warnings_messages.append(str(WARNING_MESSAGES[WARNING_DATE_PRIOR_OF_LOCK_DATE]))
                    record.extract_error_message = '\n'.join(warnings_messages)
                else:
                    record.extract_error_message = str(ERROR_MESSAGES.get(record.extract_status_code, ERROR_MESSAGES[ERROR_INTERNAL]))
            else:
                record.extract_error_message = ''

    def _compute_can_show_send_resend(self):
        self.ensure_one()
        can_show = True
        if not self.company_id.extract_show_ocr_option_selection or self.company_id.extract_show_ocr_option_selection == 'no_send':
            can_show = False
        if self.state != 'draft':
            can_show = False
        if not self.is_invoice():
            can_show = False
        if self.message_main_attachment_id is None or len(self.message_main_attachment_id) == 0:
            can_show = False
        return can_show

    @api.depends('state', 'extract_state', 'message_main_attachment_id')
    def _compute_show_resend_button(self):
        for record in self:
            record.extract_can_show_resend_button = record._compute_can_show_send_resend()
            if record.extract_state not in ['error_status', 'not_enough_credit', 'module_not_up_to_date']:
                record.extract_can_show_resend_button = False

    @api.depends('state', 'extract_state', 'message_main_attachment_id')
    def _compute_show_send_button(self):
        for record in self:
            record.extract_can_show_send_button = record._compute_can_show_send_resend()
            if record.extract_state not in ['no_extract_requested']:
                record.extract_can_show_send_button = False

    extract_state = fields.Selection([('no_extract_requested', 'No extract requested'),
                                      ('not_enough_credit', 'Not enough credit'),
                                      ('error_status', 'An error occurred'),
                                      ('waiting_extraction', 'Waiting extraction'),
                                      ('extract_not_ready', 'waiting extraction, but it is not ready'),
                                      ('waiting_validation', 'Waiting validation'),
                                      ('done', 'Completed flow')],
                                     'Extract state', default='no_extract_requested', required=True, copy=False)
    extract_status_code = fields.Integer("Status code", copy=False)
    extract_error_message = fields.Text("Error message", compute=_compute_error_message)
    extract_remote_id = fields.Integer("Id of the request to IAP-OCR", default="-1", help="Invoice extract id", copy=False, readonly=True)
    extract_word_ids = fields.One2many("account.invoice_extract.words", inverse_name="invoice_id", copy=False)

    extract_can_show_resend_button = fields.Boolean("Can show the ocr resend button", compute=_compute_show_resend_button)
    extract_can_show_send_button = fields.Boolean("Can show the ocr send button", compute=_compute_show_send_button)

    def _domain_company(self):
        return ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)]

    @api.model
    def _contact_iap_extract(self, local_endpoint, params):
        params['version'] = CLIENT_OCR_VERSION
        endpoint = self.env['ir.config_parameter'].sudo().get_param('account_invoice_extract_endpoint', EXTRACT_ENDPOINT)
        return iap_tools.iap_jsonrpc(endpoint + local_endpoint, params=params)

    @api.model
    def _contact_iap_partner_autocomplete(self, local_endpoint, params):
        return iap_tools.iap_jsonrpc(PARTNER_AUTOCOMPLETE_ENDPOINT + local_endpoint, params=params)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        return super(AccountMove, self.with_context(from_alias=True)).message_new(msg_dict, custom_values=custom_values)

    def _needs_auto_extract(self):
        """ Returns `True` if the document should be automatically sent to the extraction server"""
        return (
            self.extract_state == "no_extract_requested"
            and self.company_id.extract_show_ocr_option_selection == 'auto_send'
            and (
                self.is_purchase_document()
                or (self.is_sale_document() and self._context.get('from_alias'))
            )
        )

    def _ocr_create_invoice_from_attachment(self, attachment):
        invoice = self.env['account.move'].create({})
        invoice.message_main_attachment_id = attachment
        invoice.retry_ocr()
        return invoice

    def _ocr_update_invoice_from_attachment(self, attachment, invoice):
        invoice.retry_ocr()
        return invoice

    def _get_create_invoice_from_attachment_decoders(self):
        # OVERRIDE
        res = super()._get_create_invoice_from_attachment_decoders()
        if self.env.company.extract_show_ocr_option_selection == 'auto_send':
            res.append((20, self._ocr_create_invoice_from_attachment))
        return res

    def _get_update_invoice_from_attachment_decoders(self, invoice):
        # OVERRIDE
        res = super()._get_update_invoice_from_attachment_decoders(invoice)
        if invoice._needs_auto_extract():
            res.append((20, self._ocr_update_invoice_from_attachment))
        return res

    def get_user_infos(self):
        user_infos = {
            'user_company_VAT': self.company_id.vat,
            'user_company_name': self.company_id.name,
            'user_company_country_code': self.company_id.country_id.code,
            'user_lang': self.env.user.lang,
            'user_email': self.env.user.email,
            'perspective': 'supplier' if self.move_type in {'out_invoice', 'out_refund'} else 'client',
        }
        return user_infos

    def retry_ocr(self):
        """Retry to contact iap to submit the first attachment in the chatter"""
        self.ensure_one()
        if not self.company_id.extract_show_ocr_option_selection or self.company_id.extract_show_ocr_option_selection == 'no_send':
            return False
        attachments = self.message_main_attachment_id
        if attachments and attachments.exists() and self.is_invoice() and self.extract_state in ['no_extract_requested', 'not_enough_credit', 'error_status', 'module_not_up_to_date']:
            account_token = self.env['iap.account'].get('invoice_ocr')
            user_infos = self.get_user_infos()
            #this line contact iap to create account if this is the first request. This allow iap to give free credits if the database is elligible
            self.env['iap.account'].get_credits('invoice_ocr')
            if not account_token.account_token:
                self.extract_state = 'error_status'
                self.extract_status_code = ERROR_INVALID_ACCOUNT_TOKEN
                return
            baseurl = self.get_base_url()
            webhook_url = f"{baseurl}/account_invoice_extract/request_done"
            params = {
                'account_token': account_token.account_token,
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'documents': [x.datas.decode('utf-8') for x in attachments],
                'file_names': [x.name for x in attachments],
                'user_infos': user_infos,
                'webhook_url': webhook_url,
            }
            try:
                result = self._contact_iap_extract('/iap/invoice_extract/parse', params)
                self.extract_status_code = result['status_code']
                if result['status_code'] == SUCCESS:
                    if self.env['ir.config_parameter'].sudo().get_param("account_invoice_extract.already_notified", True):
                        self.env['ir.config_parameter'].sudo().set_param("account_invoice_extract.already_notified", False)
                    self.extract_state = 'waiting_extraction'
                    self.extract_remote_id = result['document_id']
                elif result['status_code'] == ERROR_NOT_ENOUGH_CREDIT:
                    self.send_no_credit_notification()
                    self.extract_state = 'not_enough_credit'
                else:
                    self.extract_state = 'error_status'
                    _logger.warning('There was an issue while doing the OCR operation on this file. Error: -1')

            except AccessError:
                self.extract_state = 'error_status'
                self.extract_status_code = ERROR_NO_CONNECTION

    def send_no_credit_notification(self):
        """
        Notify about the number of credit.
        In order to avoid to spam people each hour, an ir.config_parameter is set
        """
        #If we don't find the config parameter, we consider it True, because we don't want to notify if no credits has been bought earlier.
        already_notified = self.env['ir.config_parameter'].sudo().get_param("account_invoice_extract.already_notified", True)
        if already_notified:
            return
        try:
            mail_template = self.env.ref('account_invoice_extract.account_invoice_extract_no_credit')
        except ValueError:
            #if the mail template has not been created by an upgrade of the module
            return
        iap_account = self.env['iap.account'].search([('service_name', '=', "invoice_ocr")], limit=1)
        if iap_account:
            # Get the email address of the creators of the records
            res = self.env['res.users'].search_read([('id', '=', 2)], ['email'])
            if res:
                email_values = {
                    'email_to': res[0]['email']
                }
                mail_template.send_mail(iap_account.id, force_send=True, email_values=email_values)
                self.env['ir.config_parameter'].sudo().set_param("account_invoice_extract.already_notified", True)

    def get_validation(self, field):
        """
        return the text or box corresponding to the choice of the user.
        If the user selected a box on the document, we return this box,
        but if he entered the text of the field manually, we return only the text, as we
        don't know which box is the right one (if it exists)
        """
        selected = self.env["account.invoice_extract.words"].search([("invoice_id", "=", self.id), ("field", "=", field), ("user_selected", "=", True)])
        if not selected.exists():
            selected = self.env["account.invoice_extract.words"].search([("invoice_id", "=", self.id), ("field", "=", field), ("selected_status", "=", 1)], limit=1)
        return_box = {}
        if selected.exists():
            return_box["box"] = [selected.word_text, selected.word_page, selected.word_box_midX,
                                 selected.word_box_midY, selected.word_box_width, selected.word_box_height, selected.word_box_angle]
        # now we have the user or ocr selection, check if there was manual changes

        text_to_send = {}
        if field == "total":
            text_to_send["content"] = self.amount_total
        elif field == "subtotal":
            text_to_send["content"] = self.amount_untaxed
        elif field == "global_taxes_amount":
            text_to_send["content"] = self.amount_tax
        elif field == "global_taxes":
            text_to_send["content"] = [{
                'amount': line.debit,
                'tax_amount': line.tax_line_id.amount,
                'tax_amount_type': line.tax_line_id.amount_type,
                'tax_price_include': line.tax_line_id.price_include} for line in self.line_ids.filtered('tax_repartition_line_id')]
        elif field == "date":
            text_to_send["content"] = str(self.invoice_date) if self.invoice_date else False
        elif field == "due_date":
            text_to_send["content"] = str(self.invoice_date_due) if self.invoice_date_due else False
        elif field == "invoice_id":
            if self.move_type in {'in_invoice', 'in_refund'}:
                text_to_send["content"] = self.ref
            else:
                text_to_send["content"] = self.name
        elif field == "partner":
            text_to_send["content"] = self.partner_id.name
        elif field == "VAT_Number":
            text_to_send["content"] = self.partner_id.vat
        elif field == "currency":
            text_to_send["content"] = self.currency_id.name
        elif field == "payment_ref":
            text_to_send["content"] = self.payment_reference
        elif field == "iban":
            text_to_send["content"] = self.partner_bank_id.acc_number if self.partner_bank_id else False
        elif field == "SWIFT_code":
            text_to_send["content"] = self.partner_bank_id.bank_bic if self.partner_bank_id else False
        elif field == "invoice_lines":
            text_to_send = {'lines': []}
            for il in self.invoice_line_ids:
                line = {
                    "description": il.name,
                    "quantity": il.quantity,
                    "unit_price": il.price_unit,
                    "product": il.product_id.id,
                    "taxes_amount": round(il.price_total - il.price_subtotal, 2),
                    "taxes": [{
                        'amount': tax.amount,
                        'type': tax.amount_type,
                        'price_include': tax.price_include} for tax in il.tax_ids],
                    "subtotal": il.price_subtotal,
                    "total": il.price_total
                }
                text_to_send['lines'].append(line)
        else:
            return None

        return_box.update(text_to_send)
        return return_box

    def _post(self, soft=True):
        # OVERRIDE
        # On the validation of an invoice, send the different corrected fields to iap to improve the ocr algorithm.
        posted = super()._post(soft)
        documents = {}
        for record in posted.filtered(lambda move: move.is_invoice()):
            if record.extract_state == 'waiting_validation':
                values = {
                    'total': record.get_validation('total'),
                    'subtotal': record.get_validation('subtotal'),
                    'global_taxes': record.get_validation('global_taxes'),
                    'global_taxes_amount': record.get_validation('global_taxes_amount'),
                    'date': record.get_validation('date'),
                    'due_date': record.get_validation('due_date'),
                    'invoice_id': record.get_validation('invoice_id'),
                    'partner': record.get_validation('partner'),
                    'VAT_Number': record.get_validation('VAT_Number'),
                    'currency': record.get_validation('currency'),
                    'payment_ref': record.get_validation('payment_ref'),
                    'iban': record.get_validation('iban'),
                    'SWIFT_code': record.get_validation('SWIFT_code'),
                    'merged_lines': self.env.company.extract_single_line_per_tax,
                    'invoice_lines': record.get_validation('invoice_lines')
                }
                documents[record.extract_remote_id] = values
                record.extract_state = 'done'
        params = {'documents': documents}
        if len(documents) >= 1:
            try:
                self._contact_iap_extract('/api/extract/invoice/1/validate_batch', params=params)
            except AccessError:
                pass
        posted.mapped('extract_word_ids').unlink()
        return posted

    def get_boxes(self):
        return [{
            "id": data.id,
            "feature": data.field,
            "text": data.word_text,
            "selected_status": data.selected_status,
            "user_selected": data.user_selected,
            "page": data.word_page,
            "box_midX": data.word_box_midX,
            "box_midY": data.word_box_midY,
            "box_width": data.word_box_width,
            "box_height": data.word_box_height,
            "box_angle": data.word_box_angle} for data in self.extract_word_ids]

    def remove_user_selected_box(self, id):
        """Set the selected box for a feature. The id of the box indicates the concerned feature.
        The method returns the text that can be set in the view (possibly different of the text in the file)"""
        self.ensure_one()
        word = self.env["account.invoice_extract.words"].browse(int(id))
        to_unselect = self.env["account.invoice_extract.words"].search([("invoice_id", "=", self.id), ("field", "=", word.field), '|', ("user_selected", "=", True), ("selected_status", "!=", 0)])
        user_selected_found = False
        for box in to_unselect:
            if box.user_selected:
                user_selected_found = True
                box.user_selected = False
        ocr_new_value = 0
        new_word = None
        if user_selected_found:
            ocr_new_value = 1
        for box in to_unselect:
            if box.selected_status != 0:
                box.selected_status = ocr_new_value
                if ocr_new_value != 0:
                    new_word = box
        word.user_selected = False
        if new_word is None:
            if word.field in ["VAT_Number", "supplier", "currency"]:
                return 0
            return ""
        if new_word.field == "VAT_Number":
            partner_vat = self.find_partner_id_with_vat(new_word.word_text)
            if partner_vat:
                return partner_vat.id
            return 0
        if new_word.field == "supplier":
            partner_names = self.env["res.partner"].search([("name", "ilike", new_word.word_text), *self._domain_company()])
            if partner_names.exists():
                partner = min(partner_names, key=len)
                return partner.id
            else:
                partners = {}
                for single_word in new_word.word_text.split(" "):
                    partner_names = self.env["res.partner"].search([("name", "ilike", single_word), *self._domain_company()], limit=30)
                    for partner in partner_names:
                        partners[partner.id] = partners[partner.id] + 1 if partner.id in partners else 1
                if len(partners) > 0:
                    key_max = max(partners.keys(), key=(lambda k: partners[k]))
                    return key_max
            return 0
        return new_word.word_text

    def set_user_selected_box(self, id):
        """Set the selected box for a feature. The id of the box indicates the concerned feature.
        The method returns the text that can be set in the view (possibly different of the text in the file)"""
        self.ensure_one()
        word = self.env["account.invoice_extract.words"].browse(int(id))
        to_unselect = self.env["account.invoice_extract.words"].search([("invoice_id", "=", self.id), ("field", "=", word.field), ("user_selected", "=", True)])
        for box in to_unselect:
            box.user_selected = False
        ocr_boxes = self.env["account.invoice_extract.words"].search([("invoice_id", "=", self.id), ("field", "=", word.field), ("selected_status", "=", 1)])
        for box in ocr_boxes:
            if box.selected_status != 0:
                box.selected_status = 2
        word.user_selected = True
        if word.field == "currency":
            text = word.word_text
            currency = None
            currencies = self.env["res.currency"].search([])
            for curr in currencies:
                if text == curr.currency_unit_label:
                    currency = curr
                if text == curr.name or text == curr.symbol:
                    currency = curr
            if currency:
                return currency.id
            return self.currency_id.id
        if word.field == "VAT_Number":
            partner_vat = False
            if word.word_text != "":
                partner_vat = self.find_partner_id_with_vat(word.word_text)
            if partner_vat:
                return partner_vat.id
            else:
                vat = word.word_text
                partner = self._create_supplier_from_vat(vat)
                return partner.id if partner else False

        if word.field == "supplier":
            return self.find_partner_id_with_name(word.word_text)
        return word.word_text

    def find_partner_id_with_vat(self, vat_number_ocr):
        partner_vat = self.env["res.partner"].search([("vat", "=ilike", vat_number_ocr), *self._domain_company()], limit=1)
        if not partner_vat:
            partner_vat = self.env["res.partner"].search([("vat", "=ilike", vat_number_ocr[2:]), *self._domain_company()], limit=1)
        if not partner_vat:
            for partner in self.env["res.partner"].search([("vat", "!=", False), *self._domain_company()], limit=1000):
                vat = partner.vat.upper()
                vat_cleaned = vat.replace("BTW", "").replace("MWST", "").replace("ABN", "")
                vat_cleaned = re.sub(r'[^A-Z0-9]', '', vat_cleaned)
                if vat_cleaned == vat_number_ocr or vat_cleaned == vat_number_ocr[2:]:
                    partner_vat = partner
                    break
        return partner_vat

    def _create_supplier_from_vat(self, vat_number_ocr):
        partner_autocomplete = self.env['ir.module.module'].sudo().search([('name', '=', 'partner_autocomplete')], limit=1)
        if not partner_autocomplete or partner_autocomplete.state != 'installed':
            return False

        params = {
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'account_token': self.env['iap.account'].get('partner_autocomplete').account_token,
            'country_code': self.company_id.country_id.code,
            'vat': vat_number_ocr,
        }
        try:
            response = self._contact_iap_partner_autocomplete('/iap/partner_autocomplete/enrich', params)
            if 'credit_error' in response and response['credit_error']:
                raise iap_tools.InsufficientCreditError
        except iap_tools.InsufficientCreditError:
            _logger.warning("Credit error on partner_autocomplete call")
            return False
        except Exception as exception:
            _logger.error('Check VAT error: %s' % str(exception))
            return False

        if response and response.get('company_data'):
            country_id = self.env['res.country'].search([('code', '=', response.get('company_data').get('country_code',''))])
            state_id = self.env['res.country.state'].search([('name', '=', response.get('company_data').get('state_name',''))])
            resp_values = response.get('company_data')
            if 'bank_ids' in resp_values:
                resp_values['bank_ids'] = [(0, 0, vals) for vals in resp_values['bank_ids']]
            values = {
                'name': resp_values.get('name', ''),
                'vat': resp_values.get('vat', ''),
                'bank_ids': resp_values.get('bank_ids', ''),
                'street': resp_values.get('street', ''),
                'city': resp_values.get('city', ''),
                'zip': resp_values.get('zip', ''),
                'state_id': state_id and state_id.id,
                'country_id': country_id and country_id.id,
                'phone': resp_values.get('phone', ''),
                'email': resp_values.get('email', ''),
                'is_company': True,
            }
            # partner_gid is defined in partner_autocomplete, which is not a dependency of
            # account_invoice_extract
            if 'partner_gid' in self.env['res.partner']._fields:
                values['partner_gid'] = resp_values.get('partner_gid', '')
            new_partner = self.env["res.partner"].with_context(clean_context(self.env.context)).create(values)
            return new_partner
        return False

    def find_partner_id_with_name(self, partner_name):
        if not partner_name:
            return 0

        partner = self.env["res.partner"].search([("name", "=", partner_name), *self._domain_company()], limit=1)
        if partner:
            return partner.id if partner.id != self.company_id.partner_id.id else 0

        self.env.cr.execute("""
            SELECT id, name
            FROM res_partner
            WHERE active = true 
              AND supplier_rank > 0 
              AND name IS NOT NULL
              AND (company_id IS NULL OR company_id = %s)
        """, [self.company_id.id])

        partners_dict = {name.lower().replace('-', ' '): partner_id for partner_id, name in self.env.cr.fetchall()}
        partner_name = partner_name.lower().strip()

        partners = {}
        for single_word in [word for word in re.findall(r"\w+", partner_name) if len(word) >= 3]:
            partners_matched = [partner for partner in partners_dict if single_word in partner.split()]
            if len(partners_matched) == 1:
                partner = partners_matched[0]
                partners[partner] = partners[partner] + 1 if partner in partners else 1

        if partners:
            sorted_partners = sorted(partners, key=partners.get, reverse=True)
            if len(sorted_partners) == 1 or partners[sorted_partners[0]] != partners[sorted_partners[1]]:
                partner = sorted_partners[0]
                if partners_dict[partner] != self.company_id.partner_id.id:
                    return partners_dict[partner]
        return 0

    def _get_taxes_record(self, taxes_ocr, taxes_type_ocr):
        """
        Find taxes records to use from the taxes detected for an invoice line.
        """
        taxes_found = self.env['account.tax']
        type_tax_use = 'purchase' if self.move_type in {'in_invoice', 'in_refund'} else 'sale'
        for (taxes, taxes_type) in zip(taxes_ocr, taxes_type_ocr):
            if taxes != 0.0:
                related_documents = self.env['account.move'].search([
                    ('state', '!=', 'draft'),
                    ('move_type', '=', self.move_type), 
                    ('partner_id', '=', self.partner_id.id),
                    *self._domain_company(),
                ], limit=100, order='id desc')
                lines = related_documents.mapped('invoice_line_ids')
                taxes_ids = related_documents.mapped('invoice_line_ids.tax_ids')
                taxes_ids = taxes_ids.filtered(
                    lambda tax:
                        tax.active and
                        tax.amount == taxes and
                        tax.amount_type == taxes_type and
                        tax.type_tax_use == type_tax_use
                )
                taxes_by_document = []
                for tax in taxes_ids:
                    taxes_by_document.append((tax, lines.filtered(lambda line: tax in line.tax_ids)))
                if len(taxes_by_document) != 0:
                    taxes_found |= max(taxes_by_document, key=lambda tax: len(tax[1]))[0]
                else:
                    if self.company_id.account_purchase_tax_id and self.company_id.account_purchase_tax_id.amount == taxes and self.company_id.account_purchase_tax_id.amount_type == taxes_type:
                        taxes_found |= self.company_id.account_purchase_tax_id
                    else:
                        taxes_records = self.env['account.tax'].search([
                            ('amount', '=', taxes),
                            ('amount_type', '=', taxes_type),
                            ('type_tax_use', '=', type_tax_use),
                            *self._domain_company(),
                        ])
                        if taxes_records:
                            # prioritize taxes based on db setting
                            line_tax_type = self.env['ir.config_parameter'].sudo().get_param('account.show_line_subtotals_tax_selection')
                            taxes_records_setting_based = taxes_records.filtered(lambda r: not r.price_include if line_tax_type == 'tax_excluded' else r.price_include)
                            if taxes_records_setting_based:
                                taxes_record = taxes_records_setting_based[0]
                            else:
                                taxes_record = taxes_records[0]
                            taxes_found |= taxes_record
        return taxes_found

    def _get_invoice_lines(self, invoice_lines, subtotal_ocr):
        """
        Get write values for invoice lines.
        """
        self.ensure_one()
        invoice_lines_to_create = []
        if self.company_id.extract_single_line_per_tax:
            merged_lines = {}
            for il in invoice_lines:
                description = il['description']['selected_value']['content'] if 'description' in il else None
                total = il['total']['selected_value']['content'] if 'total' in il else 0.0
                subtotal = il['subtotal']['selected_value']['content'] if 'subtotal' in il else total
                taxes_ocr = [value['content'] for value in il['taxes']['selected_values']] if 'taxes' in il else []
                taxes_type_ocr = [value['amount_type'] if 'amount_type' in value else 'percent' for value in il['taxes']['selected_values']] if 'taxes' in il else []
                taxes_records = self._get_taxes_record(taxes_ocr, taxes_type_ocr)

                taxes_ids = tuple(sorted(taxes_records.ids))
                if taxes_ids not in merged_lines:
                    merged_lines[taxes_ids] = {'subtotal': subtotal, 'description': [description] if description is not None else []}
                else:
                    merged_lines[taxes_ids]['subtotal'] += subtotal
                    if description is not None:
                        merged_lines[taxes_ids]['description'].append(description)
                merged_lines[taxes_ids]['taxes_records'] = taxes_records

            # if there is only one line after aggregating the lines, use the total found by the ocr as it is less error-prone
            if len(merged_lines) == 1:
                merged_lines[list(merged_lines.keys())[0]]['subtotal'] = subtotal_ocr

            for taxes_ids, il in merged_lines.items():
                vals = {
                    'name': "\n".join(il['description']) if len(il['description']) > 0 else "/",
                    'price_unit': il['subtotal'],
                    'quantity': 1.0,
                    'tax_ids': il['taxes_records']
                }

                invoice_lines_to_create.append(vals)
        else:
            for il in invoice_lines:
                description = il['description']['selected_value']['content'] if 'description' in il else "/"
                total = il['total']['selected_value']['content'] if 'total' in il else 0.0
                subtotal = il['subtotal']['selected_value']['content'] if 'subtotal' in il else total
                unit_price = il['unit_price']['selected_value']['content'] if 'unit_price' in il else subtotal
                quantity = il['quantity']['selected_value']['content'] if 'quantity' in il else 1.0
                taxes_ocr = [value['content'] for value in il['taxes']['selected_values']] if 'taxes' in il else []
                taxes_type_ocr = [value['amount_type'] if 'amount_type' in value else 'percent' for value in il['taxes']['selected_values']] if 'taxes' in il else []

                vals = {
                    'name': description,
                    'price_unit': unit_price,
                    'quantity': quantity,
                    'tax_ids': self._get_taxes_record(taxes_ocr, taxes_type_ocr)
                }

                invoice_lines_to_create.append(vals)

        return invoice_lines_to_create

    @api.model
    def check_all_status(self):
        for record in self.search([('state', '=', 'draft'), ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready'])]):
            try:
                with self.env.cr.savepoint():
                    record._check_status()
                self.env.cr.commit()
            except Exception as e:
                _logger.error("Couldn't check status of account.move with id %d: %s", record.id, str(e))

    def check_status(self):
        """contact iap to get the actual status of the ocr requests"""
        records_to_update = self.filtered(lambda inv: inv.extract_state in ['waiting_extraction', 'extract_not_ready'] and inv.state == 'draft')

        for record in records_to_update:
            record._check_status()

        limit = max(0, 20 - len(records_to_update))
        if limit > 0:
            records_to_preupdate = self.search([('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']), ('id', 'not in', records_to_update.ids), ('state', '=', 'draft')], limit=limit)
            for record in records_to_preupdate:
                try:
                    with self.env.cr.savepoint():
                        record._check_status()
                except Exception as e:
                    _logger.error("Couldn't check status of account.move with id %d: %s", record.id, str(e))

    def _check_status(self):
        self.ensure_one()
        if self.state == 'draft':
            params = {
                'document_id': self.extract_remote_id
            }
            result = self._contact_iap_extract('/iap/invoice_extract/get_result', params=params)
            self.extract_status_code = result['status_code']
            if result['status_code'] == SUCCESS:
                self.extract_state = "waiting_validation"
                ocr_results = result['results'][0]
                self.extract_word_ids.unlink()

                # We still want to save all other fields when there is a duplicate vendor reference
                try:
                    # Savepoint so the transactions don't go through if the save raises an exception
                    with self.env.cr.savepoint():
                        self._save_form(ocr_results)
                # Retry saving without the ref, then set the error status to show the user a warning
                except ValidationError as e:
                    self._save_form(ocr_results, no_ref=True)
                    self.add_warning(WARNING_DUPLICATE_VENDOR_REFERENCE)
                    self.duplicated_vendor_ref = ocr_results['invoice_id']['selected_value']['content'] if 'invoice_id' in ocr_results else ""

                fields_with_boxes = ['supplier', 'date', 'due_date', 'invoice_id', 'currency', 'VAT_Number']
                for field in fields_with_boxes:
                    if field in ocr_results:
                        value = ocr_results[field]
                        data = []
                        for word in value["words"]:
                            data.append((0, 0, {
                                "field": field,
                                "selected_status": 1 if value["selected_value"] == word else 0,
                                "word_text": word['content'],
                                "word_page": word['page'],
                                "word_box_midX": word['coords'][0],
                                "word_box_midY": word['coords'][1],
                                "word_box_width": word['coords'][2],
                                "word_box_height": word['coords'][3],
                                "word_box_angle": word['coords'][4],
                            }))
                        self.write({'extract_word_ids': data})
            elif result['status_code'] == NOT_READY:
                self.extract_state = 'extract_not_ready'
            else:
                self.extract_state = 'error_status'

    def _save_form(self, ocr_results, no_ref=False):
        supplier_ocr = ocr_results['supplier']['selected_value']['content'] if 'supplier' in ocr_results else ""
        client_ocr = ocr_results['client']['selected_value']['content'] if 'client' in ocr_results else ""
        date_ocr = ocr_results['date']['selected_value']['content'] if 'date' in ocr_results else ""
        due_date_ocr = ocr_results['due_date']['selected_value']['content'] if 'due_date' in ocr_results else ""
        total_ocr = ocr_results['total']['selected_value']['content'] if 'total' in ocr_results else ""
        subtotal_ocr = ocr_results['subtotal']['selected_value']['content'] if 'subtotal' in ocr_results else ""
        invoice_id_ocr = ocr_results['invoice_id']['selected_value']['content'] if 'invoice_id' in ocr_results else ""
        currency_ocr = ocr_results['currency']['selected_value']['content'] if 'currency' in ocr_results else ""
        vat_number_ocr = ocr_results['VAT_Number']['selected_value']['content'] if 'VAT_Number' in ocr_results else ""
        payment_ref_ocr = ocr_results['payment_ref']['selected_value']['content'] if 'payment_ref' in ocr_results else ""
        iban_ocr = ocr_results['iban']['selected_value']['content'] if 'iban' in ocr_results else ""
        SWIFT_code_ocr = json.loads(ocr_results['SWIFT_code']['selected_value']['content']) if 'SWIFT_code' in ocr_results else None
        qr_bill_ocr = ocr_results['qr-bill']['selected_value']['content'] if 'qr-bill' in ocr_results else None
        invoice_lines = ocr_results['invoice_lines'] if 'invoice_lines' in ocr_results else []

        with self.get_form_context_manager() as move_form:
            move_form.date = datetime.strptime(move_form.date, tools.DEFAULT_SERVER_DATE_FORMAT).date()
            if not move_form.partner_id:
                if vat_number_ocr:
                    partner_vat = self.find_partner_id_with_vat(vat_number_ocr)
                    if partner_vat:
                        move_form.partner_id = partner_vat
                if self.move_type in {'in_invoice', 'in_refund'} and not move_form.partner_id and iban_ocr:
                    bank_account = self.env['res.partner.bank'].search([('acc_number', '=ilike', iban_ocr), *self._domain_company()])
                    if len(bank_account) == 1:
                        move_form.partner_id = bank_account.partner_id
                if not move_form.partner_id:
                    partner_id = self.find_partner_id_with_name(client_ocr if self.move_type in {'out_invoice', 'out_refund'} else supplier_ocr)
                    if partner_id != 0:
                        move_form.partner_id = self.env["res.partner"].browse(partner_id)
                if not move_form.partner_id and vat_number_ocr:
                    created_supplier = self._create_supplier_from_vat(vat_number_ocr)
                    if created_supplier:
                        move_form.partner_id = created_supplier
                        if iban_ocr and not move_form.partner_bank_id and self.move_type in {'in_invoice', 'in_refund'}:
                            bank_account = self.env['res.partner.bank'].search([('acc_number', '=ilike', iban_ocr), *self._domain_company()])
                            if bank_account.exists():
                                if bank_account.partner_id == move_form.partner_id.id:
                                    move_form.partner_bank_id = bank_account
                            else:
                                vals = {
                                        'partner_id': move_form.partner_id.id,
                                        'acc_number': iban_ocr
                                       }
                                if SWIFT_code_ocr:
                                    bank_id = self.env['res.bank'].search([('bic', '=', SWIFT_code_ocr['bic'])], limit=1)
                                    if bank_id.exists():
                                        vals['bank_id'] = bank_id.id
                                    if not bank_id.exists() and SWIFT_code_ocr['verified_bic']:
                                        country_id = self.env['res.country'].search([('code', '=', SWIFT_code_ocr['country_code'])], limit=1)
                                        if country_id.exists():
                                            vals['bank_id'] = self.env['res.bank'].create({'name': SWIFT_code_ocr['name'], 'country': country_id.id, 'city': SWIFT_code_ocr['city'], 'bic': SWIFT_code_ocr['bic']}).id
                                move_form.partner_bank_id = self.with_context(clean_context(self.env.context)).env['res.partner.bank'].create(vals)

            if qr_bill_ocr:
                qr_content_list = qr_bill_ocr.splitlines()

                if not move_form.partner_id:
                    move_form.partner_id = self.env["res.partner"].with_context(clean_context(self.env.context)).create({
                        'name': qr_content_list[5],
                        'is_company': True,
                    })

                partner = move_form.partner_id
                supplier_address_type = qr_content_list[4]
                if supplier_address_type == 'S':
                    if not partner.street:
                        street = qr_content_list[6]
                        house_nb = qr_content_list[7]
                        partner.street = " ".join((street, house_nb))

                    if not partner.zip:
                        partner.zip = qr_content_list[8]

                    if not partner.city:
                        partner.city = qr_content_list[9]
                elif supplier_address_type == 'K':
                    if not partner.street:
                        partner.street = qr_content_list[6]
                        partner.street2 = qr_content_list[7]

                supplier_country_code = qr_content_list[10]
                if not partner.country_id and supplier_country_code:
                    country = self.env['res.country'].search([('code', '=', supplier_country_code)])
                    partner.country_id = country and country.id

                iban = qr_content_list[3]
                if iban and not self.env['res.partner.bank'].search([('acc_number', '=ilike', iban)]):
                    self.env['res.partner.bank'].create({
                        'acc_number': iban,
                        'company_id': move_form.company_id.id,
                        'currency_id': move_form.currency_id.id,
                        'partner_id': partner.id,
                    })

            due_date_move_form = move_form.invoice_date_due  # remember the due_date, as it could be modified by the onchange() of invoice_date
            context_create_date = str(fields.Date.context_today(self, self.create_date))
            if date_ocr and (not move_form.invoice_date or move_form.invoice_date == context_create_date):
                move_form.invoice_date = date_ocr
                if self.company_id.tax_lock_date and move_form.date and move_form.date <= self.company_id.tax_lock_date:
                    move_form.date = self.company_id.tax_lock_date + timedelta(days=1)
                    self.add_warning(WARNING_DATE_PRIOR_OF_LOCK_DATE)
            if due_date_ocr and (not due_date_move_form or due_date_move_form == context_create_date):
                if date_ocr == due_date_ocr and move_form.partner_id and move_form.partner_id.property_supplier_payment_term_id:
                    # if the invoice date and the due date found by the OCR are the same, we use the payment terms of the detected supplier instead, if there is one
                    move_form.invoice_payment_term_id = move_form.partner_id.property_supplier_payment_term_id
                else:
                    move_form.invoice_date_due = due_date_ocr
            if self.move_type in {'in_invoice', 'in_refund'} and not move_form.ref and not no_ref:
                move_form.ref = invoice_id_ocr

            if self.move_type in {'out_invoice', 'out_refund'}:
                with mute_logger('odoo.tests.common.onchange'):
                    move_form.name = invoice_id_ocr

            if not move_form.currency_id or move_form.currency_id == self._get_default_currency():
                currency = self.env["res.currency"].search([
                        '|', '|', ('currency_unit_label', 'ilike', currency_ocr),
                        ('name', 'ilike', currency_ocr), ('symbol', 'ilike', currency_ocr)], limit=1)
                if currency:
                    move_form.currency_id = currency

            if payment_ref_ocr and not move_form.payment_reference:
                move_form.payment_reference = payment_ref_ocr

            if not move_form.invoice_line_ids:
                # we save here as _get_invoice_lines() uses the record values in self to determine the tax records to use
                move_form.save()

                vals_invoice_lines = self._get_invoice_lines(invoice_lines, subtotal_ocr)
                self._set_invoice_lines(move_form, vals_invoice_lines)

                # if the total on the invoice doesn't match the total computed by Odoo, adjust the taxes so that it matches
                for i in range(len(move_form.line_ids)):
                    with move_form.line_ids.edit(i) as line:
                        if line.tax_repartition_line_id and total_ocr:
                            rounding_error = move_form.amount_total - total_ocr
                            threshold = len(vals_invoice_lines) * move_form.currency_id.rounding
                            if not move_form.currency_id.is_zero(rounding_error) and float_compare(abs(rounding_error), threshold, precision_digits=2) <= 0:
                                if self.is_purchase_document():
                                    line.debit -= rounding_error
                                else:
                                    line.credit -= rounding_error
                            break

    def _set_invoice_lines(self, move_form, vals_invoice_lines):
        for i, line_val in enumerate(vals_invoice_lines, start=len(move_form.invoice_line_ids)):
            with move_form.invoice_line_ids.new() as line:
                line.name = line_val['name']
                if not line.account_id:
                    raise ValidationError(_("The OCR module is not able to generate the invoice lines because the default accounts are not correctly set on the %s journal.", move_form.journal_id.name_get()[0][1]))

            # We close and re-open the line to let account_predictive_bills do the predictions based on the label
            with move_form.invoice_line_ids.edit(i) as line:
                line.price_unit = line_val['price_unit']
                line.quantity = line_val['quantity']
                taxes_dict = {}
                for tax in line.tax_ids:
                    taxes_dict[(tax.amount, tax.amount_type, tax.price_include)] = {
                        'found_by_OCR': False,
                        'tax_record': tax,
                    }
                for taxes_record in line_val['tax_ids']:
                    tax_tuple = (taxes_record.amount, taxes_record.amount_type, taxes_record.price_include)
                    if tax_tuple not in taxes_dict:
                        line.tax_ids.add(taxes_record)
                    else:
                        taxes_dict[tax_tuple]['found_by_OCR'] = True
                    if taxes_record.price_include:
                        line.price_unit *= 1 + taxes_record.amount / 100
                for tax_info in taxes_dict.values():
                    if not tax_info['found_by_OCR']:
                        amount_before = line.price_total
                        line.tax_ids.remove(tax_info['tax_record'].id)
                        # If the total amount didn't change after removing it, we can actually leave it.
                        # This is intended as a way to keep intra-community taxes
                        if line.price_total == amount_before:
                            line.tax_ids.add(tax_info['tax_record'])

    @contextmanager
    def get_form_context_manager(self):
        self_ctx = self.with_context(default_move_type=self.move_type) if 'default_move_type' not in self._context else self
        self_ctx = self_ctx.with_company(self.company_id.id)
        if 'default_journal_id' not in self_ctx._context:
            self_ctx = self_ctx.with_context(default_journal_id=self_ctx.journal_id.id)
        with patch.object(Form, '_process_fvg', side_effect=_process_fvg, autospec=True), Form(self_ctx) as move_form:
            yield move_form

    def buy_credits(self):
        url = self.env['iap.account'].get_credits_url(base_url='', service_name='invoice_ocr')
        return {
            'type': 'ir.actions.act_url',
            'url': url,
        }

    def add_warning(self, warning_code):
        if self.extract_status_code <= WARNING_BASE_VALUE:
            self.extract_status_code = WARNING_BASE_VALUE
        self.extract_status_code += warning_code

    def get_warnings(self):
        """Returns the active warnings as a set"""
        warnings = set()
        if self.extract_status_code > WARNING_BASE_VALUE:
            # convert the status code to a 8 characters 0-padded string representation of the binary number
            codes = format(self.extract_status_code - WARNING_BASE_VALUE, '08b')

            # revert the string so that the first character will correspond to the first bit
            codes = codes[::-1]
            for warning_code in WARNING_MESSAGES:
                if codes[int(math.log2(warning_code))] == '1':
                    warnings.add(warning_code)
        return warnings


old_process_fvg = Form._process_fvg


def _process_fvg(self, model, fvg, level=2):
    old_process_fvg(self, model, fvg, level=level)
    for modifiers in fvg['modifiers'].values():
        if 'required' in modifiers:
            modifiers['required'] = False
