# -*- coding: utf-8 -*-
from odoo import api, models, fields, tools, _
from odoo.tools.xml_utils import _check_with_xsd

import logging
import re
import base64
import json
import requests
import random
import string

from lxml import etree
from lxml.objectify import fromstring
from math import copysign
from datetime import datetime
from io import BytesIO
from zeep import Client
from zeep.transports import Transport
from json.decoder import JSONDecodeError

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # CFDI: Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_mx_edi_get_serie_and_folio(self, move):
        name_numbers = list(re.finditer('\d+', move.name))
        serie_number = move.name[:name_numbers[-1].start()]
        folio_number = name_numbers[-1].group().lstrip('0')
        return {
            'serie_number': serie_number,
            'folio_number': folio_number,
        }

    @api.model
    def _l10n_mx_edi_cfdi_append_addenda(self, move, cfdi, addenda):
        ''' Append an additional block to the signed CFDI passed as parameter.
        :param move:    The account.move record.
        :param cfdi:    The invoice's CFDI as a string.
        :param addenda: The addenda to add as a string.
        :return cfdi:   The cfdi including the addenda.
        '''
        addenda_values = {'record': move, 'cfdi': cfdi}

        addenda = addenda._render(values=addenda_values).strip()
        if not addenda:
            return cfdi

        cfdi_node = fromstring(cfdi)
        addenda_node = fromstring(addenda)

        # Add a root node Addenda if not specified explicitly by the user.
        if addenda_node.tag != '{http://www.sat.gob.mx/cfd/3}Addenda':
            node = etree.Element(etree.QName('http://www.sat.gob.mx/cfd/3', 'Addenda'))
            node.append(addenda_node)
            addenda_node = node

        cfdi_node.append(addenda_node)
        return etree.tostring(cfdi_node, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    @api.model
    def _l10n_mx_edi_check_configuration(self, move):
        company = move.company_id
        pac_name = company.l10n_mx_edi_pac

        errors = []

        # == Check the certificate ==
        certificate = company.l10n_mx_edi_certificate_ids.sudo().get_valid_certificate()
        if not certificate:
            errors.append(_('No valid certificate found'))

        # == Check the credentials to call the PAC web-service ==
        if pac_name:
            pac_test_env = company.l10n_mx_edi_pac_test_env
            pac_password = company.l10n_mx_edi_pac_password
            if not pac_test_env and not pac_password:
                errors.append(_('No PAC credentials specified.'))
        else:
            errors.append(_('No PAC specified.'))

        # == Check the 'l10n_mx_edi_decimal_places' field set on the currency  ==
        currency_precision = move.currency_id.l10n_mx_edi_decimal_places
        if currency_precision is False:
            errors.append(_(
                "The SAT does not provide information for the currency %s.\n"
                "You must get manually a key from the PAC to confirm the "
                "currency rate is accurate enough.") % move.currency_id)

        return errors

    @api.model
    def _l10n_mx_edi_format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % msg for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)

    # -------------------------------------------------------------------------
    # CFDI Generation: Generic
    # ----------------------------------------

    def _l10n_mx_edi_get_common_cfdi_values(self, move):
        ''' Generic values to generate a cfdi for a journal entry.
        :param move:    The account.move record to which generate the CFDI.
        :return:        A python dictionary.
        '''

        def _format_string_cfdi(text, size=100):
            """Replace from text received the characters that are not found in the
            regex. This regex is taken from SAT documentation
            https://goo.gl/C9sKH6
            text: Text to remove extra characters
            size: Cut the string in size len
            Ex. 'Product ABC (small size)' - 'Product ABC small size'"""
            if not text:
                return None
            text = text.replace('|', ' ')
            return text.strip()[:size]

        def _format_float_cfdi(amount, precision):
            if amount is None or amount is False:
                return None
            # Avoid things like -0.0, see: https://stackoverflow.com/a/11010869
            return '%.*f' % (precision, amount if amount != 0 else 0.0)

        company = move.company_id
        certificate = company.l10n_mx_edi_certificate_ids.sudo().get_valid_certificate()
        currency_precision = move.currency_id.l10n_mx_edi_decimal_places

        customer = move.partner_id if move.partner_id.type == 'invoice' else move.partner_id.commercial_partner_id
        supplier = move.company_id.partner_id.commercial_partner_id

        if not customer:
            customer_rfc = False
        elif customer.country_id and customer.country_id.code != 'MX':
            customer_rfc = 'XEXX010101000'
        elif customer.vat:
            customer_rfc = customer.vat.strip()
        elif customer.country_id.code in (False, 'MX'):
            customer_rfc = 'XAXX010101000'
        else:
            customer_rfc = 'XEXX010101000'

        if move.l10n_mx_edi_origin:
            origin_type, origin_uuids = move._l10n_mx_edi_read_cfdi_origin(move.l10n_mx_edi_origin)
        else:
            origin_type = None
            origin_uuids = []

        return {
            **self._l10n_mx_edi_get_serie_and_folio(move),
            'certificate': certificate,
            'certificate_number': certificate.serial_number,
            'certificate_key': certificate.sudo().get_data()[0].decode('utf-8'),
            'record': move,
            'supplier': supplier,
            'customer': customer,
            'customer_rfc': customer_rfc,
            'issued_address': move._get_l10n_mx_edi_issued_address(),
            'currency_precision': currency_precision,
            'origin_type': origin_type,
            'origin_uuids': origin_uuids,
            'format_string': _format_string_cfdi,
            'format_float': _format_float_cfdi,
        }

    # -------------------------------------------------------------------------
    # CFDI Generation: Invoices
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_get_invoice_cfdi_values(self, invoice):
        ''' Doesn't check if the config is correct so you need to call _l10n_mx_edi_check_config first.

        :param invoice:
        :return:
        '''
        cfdi_date = datetime.combine(
            fields.Datetime.from_string(invoice.invoice_date),
            invoice.l10n_mx_edi_post_time.time(),
        ).strftime('%Y-%m-%dT%H:%M:%S')

        cfdi_values = {
            **invoice._prepare_edi_vals_to_export(),
            **self._l10n_mx_edi_get_common_cfdi_values(invoice),
            'document_type': 'I' if invoice.move_type == 'out_invoice' else 'E',
            'currency_name': invoice.currency_id.name,
            'payment_method_code': (invoice.l10n_mx_edi_payment_method_id.code or '').replace('NA', '99'),
            'payment_policy': invoice.l10n_mx_edi_payment_policy,
            'cfdi_date': cfdi_date,
        }

        # ==== Invoice Values ====
        if invoice.currency_id.name == 'MXN':
            cfdi_values['currency_conversion_rate'] = None
        else:  # assumes that invoice.company_id.country_id.code == 'MX', as checked in '_is_required_for_invoice'
            cfdi_values['currency_conversion_rate'] = abs(invoice.amount_total_signed) / abs(invoice.amount_total)

        if invoice.partner_bank_id:
            digits = [s for s in invoice.partner_bank_id.acc_number if s.isdigit()]
            acc_4number = ''.join(digits)[-4:]
            cfdi_values['account_4num'] = acc_4number if len(acc_4number) == 4 else None
        else:
            cfdi_values['account_4num'] = None

        if cfdi_values['customer'].country_id.l10n_mx_edi_code != 'MEX' and cfdi_values['customer_rfc'] not in ('XEXX010101000', 'XAXX010101000'):
            cfdi_values['customer_fiscal_residence'] = cfdi_values['customer'].country_id.l10n_mx_edi_code
        else:
            cfdi_values['customer_fiscal_residence'] = None

        # ==== Tax details ====

        def get_tax_cfdi_name(tax_detail_vals):
            tags = set()
            for detail in tax_detail_vals['group_tax_details']:
                for tag in detail['tax_repartition_line_id'].tag_ids:
                    tags.add(tag)
            tags = list(tags)
            if len(tags) == 1:
                return {'ISR': '001', 'IVA': '002', 'IEPS': '003'}.get(tags[0].name)
            elif tax_detail_vals['tax'].l10n_mx_tax_type == 'Exento':
                return '002'
            else:
                return None

        def filter_tax_transferred(tax_values):
            return tax_values['tax_id'].amount >= 0.0

        def filter_tax_withholding(tax_values):
            return tax_values['tax_id'].amount < 0.0

        cfdi_values.update({
            'get_tax_cfdi_name': get_tax_cfdi_name,
            'tax_details_transferred': invoice._prepare_edi_tax_details(filter_to_apply=filter_tax_transferred),
            'tax_details_withholding': invoice._prepare_edi_tax_details(filter_to_apply=filter_tax_withholding),
        })

        cfdi_values.update({
            'has_tax_details_transferred_no_exento': any(x['tax'].l10n_mx_tax_type != 'Exento' for x in cfdi_values['tax_details_transferred']['tax_details'].values()),
            'has_tax_details_withholding_no_exento': any(x['tax'].l10n_mx_tax_type != 'Exento' for x in cfdi_values['tax_details_withholding']['tax_details'].values()),
        })

        if not invoice._l10n_mx_edi_is_managing_invoice_negative_lines_allowed():
            return cfdi_values

        # ==== Distribute negative lines ====

        def is_discount_line(line):
            return line.price_subtotal < 0.0

        def is_candidate(discount_line, other_line):
            discount_taxes = discount_line.tax_ids.flatten_taxes_hierarchy()
            other_line_taxes = other_line.tax_ids.flatten_taxes_hierarchy()
            return set(discount_taxes.ids) == set(other_line_taxes.ids)

        def put_discount_on(cfdi_values, discount_vals, other_line_vals):
            discount_line = discount_vals['line']
            other_line = other_line_vals['line']

            # Update price_discount.

            remaining_discount = discount_vals['price_discount'] - discount_line.price_subtotal
            remaining_price_subtotal = other_line_vals['price_subtotal_before_discount'] - other_line_vals['price_discount']
            discount_to_allow = min(remaining_discount, remaining_price_subtotal)

            other_line_vals['price_discount'] += discount_to_allow
            discount_vals['price_discount'] -= discount_to_allow

            # Update taxes.

            for tax_key in ('tax_details_transferred', 'tax_details_withholding'):
                discount_line_tax_details = cfdi_values[tax_key]['invoice_line_tax_details'][discount_line]['tax_details']
                other_line_tax_details = cfdi_values[tax_key]['invoice_line_tax_details'][other_line]['tax_details']
                for k, tax_values in discount_line_tax_details.items():
                    if discount_line.currency_id.is_zero(tax_values['tax_amount_currency']):
                        continue

                    other_tax_values = other_line_tax_details[k]
                    tax_amount_to_allow = copysign(
                        min(abs(tax_values['tax_amount_currency']), abs(other_tax_values['tax_amount_currency'])),
                        other_tax_values['tax_amount_currency'],
                    )
                    other_tax_values['tax_amount_currency'] -= tax_amount_to_allow
                    tax_values['tax_amount_currency'] += tax_amount_to_allow
                    base_amount_to_allow = copysign(
                        min(abs(tax_values['base_amount_currency']), abs(other_tax_values['base_amount_currency'])),
                        other_tax_values['base_amount_currency'],
                    )
                    other_tax_values['base_amount_currency'] -= base_amount_to_allow
                    tax_values['base_amount_currency'] += base_amount_to_allow

            return discount_line.currency_id.is_zero(remaining_discount - discount_to_allow)

        for line_vals in cfdi_values['invoice_line_vals_list']:
            line = line_vals['line']

            if not is_discount_line(line):
                continue

            # Search for lines on which distribute the global discount.
            candidate_vals_list = [x for x in cfdi_values['invoice_line_vals_list']
                                   if not is_discount_line(x['line']) and is_candidate(line, x['line'])]

            # Put the discount on the biggest lines first.
            candidate_vals_list = sorted(candidate_vals_list, key=lambda x: x['line'].price_subtotal, reverse=True)
            for candidate_vals in candidate_vals_list:
                if put_discount_on(cfdi_values, line_vals, candidate_vals):
                    break

        # ==== Remove discount lines ====

        cfdi_values['invoice_line_vals_list'] = [x for x in cfdi_values['invoice_line_vals_list']
                                                 if not is_discount_line(x['line'])]

        # ==== Remove taxes for zero lines ====

        for line_vals in cfdi_values['invoice_line_vals_list']:
            line = line_vals['line']

            if line.currency_id.is_zero(line_vals['price_subtotal_before_discount'] - line_vals['price_discount']):
                for tax_key in ('tax_details_transferred', 'tax_details_withholding'):
                    cfdi_values[tax_key]['invoice_line_tax_details'].pop(line, None)

        # Recompute Totals since lines changed.
        cfdi_values.update({
            'total_price_subtotal_before_discount': sum(x['price_subtotal_before_discount'] for x in cfdi_values['invoice_line_vals_list']),
            'total_price_discount': sum(x['price_discount'] for x in cfdi_values['invoice_line_vals_list']),
        })

        return cfdi_values

    def _l10n_mx_edi_export_invoice_cfdi(self, invoice):
        ''' Create the CFDI attachment for the invoice passed as parameter.

        :param move:    An account.move record.
        :return:        A dictionary with one of the following key:
        * cfdi_str:     A string of the unsigned cfdi of the invoice.
        * error:        An error if the cfdi was not successfuly generated.
        '''

        # == CFDI values ==
        cfdi_values = self._l10n_mx_edi_get_invoice_cfdi_values(invoice)

        # == Generate the CFDI ==
        cfdi = self.env.ref('l10n_mx_edi.cfdiv33')._render(cfdi_values)
        decoded_cfdi_values = invoice._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo().get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted

        # == Optional check using the XSD ==
        xsd_attachment = self.env.ref('l10n_mx_edi.xsd_cached_cfdv33_xsd', False)
        xsd_datas = base64.b64decode(xsd_attachment.datas) if xsd_attachment else None

        if xsd_datas:
            try:
                with BytesIO(xsd_datas) as xsd:
                    _check_with_xsd(decoded_cfdi_values['cfdi_node'], xsd)
            except (IOError, ValueError):
                _logger.info(_('The xsd file to validate the XML structure was not found'))
            except Exception as e:
                return {'errors': str(e).split('\\n')}

        return {
            'cfdi_str': etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8'),
        }

    # -------------------------------------------------------------------------
    # CFDI Generation: Payments
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_export_payment_cfdi(self, move):
        ''' Create the CFDI attachment for the journal entry passed as parameter being a payment used to pay some
        invoices.

        :param move:    An account.move record.
        :return:        A dictionary with one of the following key:
        * cfdi_str:     A string of the unsigned cfdi of the invoice.
        * error:        An error if the cfdi was not successfully generated.
        '''
        if move.payment_id:
            currency = move.payment_id.currency_id
            total_amount = move.payment_id.amount
        else:
            if move.statement_line_id.foreign_currency_id:
                total_amount = move.statement_line_id.amount_currency
                currency = move.statement_line_id.foreign_currency_id
            else:
                total_amount = move.statement_line_id.amount
                currency = move.statement_line_id.currency_id

        # Process reconciled invoices.
        invoice_vals_list = []
        pay_rec_lines = move.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        paid_amount = abs(sum(pay_rec_lines.mapped('amount_currency')))

        mxn_currency = self.env["res.currency"].search([('name', '=', 'MXN')], limit=1)
        if move.currency_id == mxn_currency:
            rate_payment_curr_mxn = None
            paid_amount_comp_curr = paid_amount
        else:
            rate_payment_curr_mxn = move.currency_id._convert(1.0, mxn_currency, move.company_id, move.date, round=False)
            paid_amount_comp_curr = move.company_currency_id.round(paid_amount * rate_payment_curr_mxn)

        for field1, field2 in (('debit', 'credit'), ('credit', 'debit')):
            for partial in pay_rec_lines[f'matched_{field1}_ids']:
                payment_line = partial[f'{field2}_move_id']
                invoice_line = partial[f'{field1}_move_id']
                invoice_amount = partial[f'{field1}_amount_currency']
                exchange_move = invoice_line.full_reconcile_id.exchange_move_id
                invoice = invoice_line.move_id

                if not invoice.l10n_mx_edi_cfdi_request:
                    continue

                if exchange_move:
                    exchange_partial = invoice_line[f'matched_{field2}_ids']\
                        .filtered(lambda x: x[f'{field2}_move_id'].move_id == exchange_move)
                    if exchange_partial:
                        invoice_amount += exchange_partial[f'{field2}_amount_currency']

                if invoice_line.currency_id == payment_line.currency_id:
                    # Same currency
                    amount_paid_invoice_curr = invoice_amount
                    exchange_rate = None
                else:
                    # It needs to be how much invoice currency you pay for one payment currency
                    amount_paid_invoice_comp_curr = payment_line.company_currency_id.round(
                        total_amount * (partial.amount / paid_amount_comp_curr))
                    invoice_rate = abs(invoice_line.amount_currency) / abs(invoice_line.balance)
                    amount_paid_invoice_curr = invoice_line.currency_id.round(partial.amount * invoice_rate)
                    exchange_rate = amount_paid_invoice_curr / amount_paid_invoice_comp_curr

                invoice_vals_list.append({
                    'invoice': invoice,
                    'exchange_rate': exchange_rate,
                    'payment_policy': invoice.l10n_mx_edi_payment_policy,
                    'number_of_payments': len(invoice._get_reconciled_payments()) + len(invoice._get_reconciled_statement_lines()),
                    'amount_paid': amount_paid_invoice_curr,
                    'amount_before_paid': min(invoice.amount_residual + amount_paid_invoice_curr, invoice.amount_total),
                    **self._l10n_mx_edi_get_serie_and_folio(invoice),
                })

        payment_method_code = move.l10n_mx_edi_payment_method_id.code
        is_payment_code_emitter_ok = payment_method_code in ('02', '03', '04', '05', '06', '28', '29', '99')
        is_payment_code_receiver_ok = payment_method_code in ('02', '03', '04', '05', '28', '29', '99')
        is_payment_code_bank_ok = payment_method_code in ('02', '03', '04', '28', '29', '99')

        partner_bank = move.partner_bank_id.bank_id
        if partner_bank.country and partner_bank.country.code != 'MX':
            partner_bank_vat = 'XEXX010101000'
        else:  # if no partner_bank (e.g. cash payment), partner_bank_vat is not set.
            partner_bank_vat = partner_bank.l10n_mx_edi_vat

        payment_account_ord = re.sub(r'\s+', '', move.partner_bank_id.acc_number or '') or None
        payment_account_receiver = re.sub(r'\s+', '', move.journal_id.bank_account_id.acc_number or '') or None

        cfdi_values = {
            **self._l10n_mx_edi_get_common_cfdi_values(move),
            'invoice_vals_list': invoice_vals_list,
            'currency': currency,
            'amount': total_amount,
            'rate_payment_curr_mxn': rate_payment_curr_mxn,
            'emitter_vat_ord': is_payment_code_emitter_ok and partner_bank_vat,
            'bank_vat_ord': is_payment_code_bank_ok and partner_bank.name,
            'payment_account_ord': is_payment_code_emitter_ok and payment_account_ord,
            'receiver_vat_ord': is_payment_code_receiver_ok and move.journal_id.bank_account_id.bank_id.l10n_mx_edi_vat,
            'payment_account_receiver': is_payment_code_receiver_ok and payment_account_receiver,
            'cfdi_date': move.l10n_mx_edi_post_time.strftime('%Y-%m-%dT%H:%M:%S'),
        }

        cfdi_payment_datetime = datetime.combine(fields.Datetime.from_string(move.date), datetime.strptime('12:00:00', '%H:%M:%S').time())
        cfdi_values['cfdi_payment_date'] = cfdi_payment_datetime.strftime('%Y-%m-%dT%H:%M:%S')

        if cfdi_values['customer'].country_id.l10n_mx_edi_code != 'MEX':
            cfdi_values['customer_fiscal_residence'] = cfdi_values['customer'].country_id.l10n_mx_edi_code
        else:
            cfdi_values['customer_fiscal_residence'] = None

        cfdi = self.env.ref('l10n_mx_edi.payment10')._render(cfdi_values)
        decoded_cfdi_values = move._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo().get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted

        return {
            'cfdi_str': etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8'),
        }

    # -------------------------------------------------------------------------
    # CFDI: PACs
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_post_invoice_pac(self, invoice, exported):
        pac_name = invoice.company_id.l10n_mx_edi_pac

        credentials = getattr(self, '_l10n_mx_edi_get_%s_credentials' % pac_name)(invoice)
        if credentials.get('errors'):
            return {
                'error': self._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors']),
            }

        res = getattr(self, '_l10n_mx_edi_%s_sign_invoice' % pac_name)(invoice, credentials, exported['cfdi_str'])
        if res.get('errors'):
            return {
                'error': self._l10n_mx_edi_format_error_message(_("PAC failed to sign the CFDI:"), res['errors']),
            }

        return res

    def _l10n_mx_edi_post_payment_pac(self, move, exported):
        pac_name = move.company_id.l10n_mx_edi_pac
        credentials = getattr(self, '_l10n_mx_edi_get_%s_credentials' % pac_name)(move)
        if credentials.get('errors'):
            return {
                'error': self._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors']),
            }

        res = getattr(self, '_l10n_mx_edi_%s_sign_payment' % pac_name)(move, credentials, exported['cfdi_str'])
        if res.get('errors'):
            return {
                'error': self._l10n_mx_edi_format_error_message(_("PAC failed to sign the CFDI:"), res['errors']),
            }

        return res

    def _l10n_mx_edi_get_finkok_credentials(self, move):
        if move.company_id.l10n_mx_edi_pac_test_env:
            return {
                'username': 'cfdi@vauxoo.com',
                'password': 'vAux00__',
                'sign_url': 'http://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl',
                'cancel_url': 'http://demo-facturacion.finkok.com/servicios/soap/cancel.wsdl',
            }
        else:
            if not move.company_id.l10n_mx_edi_pac_username or not move.company_id.l10n_mx_edi_pac_password:
                return {
                    'errors': [_("The username and/or password are missing.")]
                }

            return {
                'username': move.company_id.l10n_mx_edi_pac_username,
                'password': move.company_id.l10n_mx_edi_pac_password,
                'sign_url': 'http://facturacion.finkok.com/servicios/soap/stamp.wsdl',
                'cancel_url': 'http://facturacion.finkok.com/servicios/soap/cancel.wsdl',
            }

    def _l10n_mx_edi_finkok_sign(self, move, credentials, cfdi):
        try:
            transport = Transport(timeout=20)
            client = Client(credentials['sign_url'], transport=transport)
            response = client.service.stamp(cfdi, credentials['username'], credentials['password'])
        except Exception as e:
            return {
                'errors': [_("The Finkok service failed to sign with the following error: %s", str(e))],
            }

        if response.Incidencias and not response.xml:
            code = getattr(response.Incidencias.Incidencia[0], 'CodigoError', None)
            msg = getattr(response.Incidencias.Incidencia[0], 'MensajeIncidencia', None)
            errors = []
            if code:
                errors.append(_("Code : %s") % code)
            if msg:
                errors.append(_("Message : %s") % msg)
            return {'errors': errors}

        cfdi_signed = getattr(response, 'xml', None)
        if cfdi_signed:
            cfdi_signed = cfdi_signed.encode('utf-8')

        return {
            'cfdi_signed': cfdi_signed,
            'cfdi_encoding': 'str',
        }

    def _l10n_mx_edi_finkok_cancel(self, move, credentials, cfdi):
        uuid = move.l10n_mx_edi_cfdi_uuid
        certificates = move.company_id.l10n_mx_edi_certificate_ids
        certificate = certificates.sudo().get_valid_certificate()
        company = move.company_id
        cer_pem = certificate.get_pem_cer(certificate.content)
        key_pem = certificate.get_pem_key(certificate.key, certificate.password)
        try:
            transport = Transport(timeout=20)
            client = Client(credentials['cancel_url'], transport=transport)
            uuid_type = client.get_type('ns0:stringArray')()
            uuid_type.string = [uuid]
            invoices_list = client.get_type('ns1:UUIDS')(uuid_type)
            response = client.service.cancel(
                invoices_list,
                credentials['username'],
                credentials['password'],
                company.vat,
                cer_pem,
                key_pem,
            )
        except Exception as e:
            return {
                'errors': [_("The Finkok service failed to cancel with the following error: %s", str(e))],
            }

        if not getattr(response, 'Folios', None):
            code = getattr(response, 'CodEstatus', None)
            msg = _("Cancelling got an error") if code else _('A delay of 2 hours has to be respected before to cancel')
        else:
            code = getattr(response.Folios.Folio[0], 'EstatusUUID', None)
            cancelled = code in ('201', '202')  # cancelled or previously cancelled
            # no show code and response message if cancel was success
            code = '' if cancelled else code
            msg = '' if cancelled else _("Cancelling got an error")

        errors = []
        if code:
            errors.append(_("Code : %s") % code)
        if msg:
            errors.append(_("Message : %s") % msg)
        if errors:
            return {'errors': errors}

        return {'success': True}

    def _l10n_mx_edi_finkok_sign_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_finkok_sign(invoice, credentials, cfdi)

    def _l10n_mx_edi_finkok_cancel_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_finkok_cancel(invoice, credentials, cfdi)

    def _l10n_mx_edi_finkok_sign_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_finkok_sign(move, credentials, cfdi)

    def _l10n_mx_edi_finkok_cancel_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_finkok_cancel(move, credentials, cfdi)

    def _l10n_mx_edi_get_solfact_credentials(self, move):
        if move.company_id.l10n_mx_edi_pac_test_env:
            return {
                'username': 'testing@solucionfactible.com',
                'password': 'timbrado.SF.16672',
                'url': 'https://testing.solucionfactible.com/ws/services/Timbrado?wsdl',
            }
        else:
            if not move.company_id.l10n_mx_edi_pac_username or not move.company_id.l10n_mx_edi_pac_password:
                return {
                    'errors': [_("The username and/or password are missing.")]
                }

            return {
                'username': move.company_id.l10n_mx_edi_pac_username,
                'password': move.company_id.l10n_mx_edi_pac_password,
                'url': 'https://solucionfactible.com/ws/services/Timbrado?wsdl',
            }

    def _l10n_mx_edi_solfact_sign(self, move, credentials, cfdi):
        try:
            transport = Transport(timeout=20)
            client = Client(credentials['url'], transport=transport)
            response = client.service.timbrar(credentials['username'], credentials['password'], cfdi, False)
        except Exception as e:
            return {
                'errors': [_("The Solucion Factible service failed to sign with the following error: %s", str(e))],
            }

        if (response.status != 200):
            # ws-timbrado-timbrar - status 200 : CFDI correctamente validado y timbrado.
            return {
                'errors': [_("The Solucion Factible service failed to sign with the following error: %s", response.mensaje)],
            }

        res = response.resultados

        cfdi_signed = getattr(res[0] if res else response, 'cfdiTimbrado', None)
        if cfdi_signed:
            return {
                'cfdi_signed': cfdi_signed,
                'cfdi_encoding': 'str',
            }

        msg = getattr(res[0] if res else response, 'mensaje', None)
        code = getattr(res[0] if res else response, 'status', None)
        errors = []
        if code:
            errors.append(_("Code : %s") % code)
        if msg:
            errors.append(_("Message : %s") % msg)
        return {'errors': errors}

    def _l10n_mx_edi_solfact_cancel(self, move, credentials, cfdi):
        uuids = [move.l10n_mx_edi_cfdi_uuid]
        certificates = move.company_id.l10n_mx_edi_certificate_ids
        certificate = certificates.sudo().get_valid_certificate()
        cer_pem = certificate.get_pem_cer(certificate.content)
        key_pem = certificate.get_pem_key(certificate.key, certificate.password)
        key_password = certificate.password

        try:
            transport = Transport(timeout=20)
            client = Client(credentials['url'], transport=transport)
            response = client.service.cancelar(
                credentials['username'], credentials['password'], uuids, cer_pem, key_pem, key_password)
        except Exception as e:
            return {
                'errors': [_("The Solucion Factible service failed to cancel with the following error: %s", str(e))],
            }

        if (response.status not in (200, 201)):
            # ws-timbrado-cancelar - status 200 : El proceso de cancelación se ha completado correctamente.
            # ws-timbrado-cancelar - status 201 : El folio se ha cancelado con éxito.
            return {
                'errors': [_("The Solucion Factible service failed to cancel with the following error: %s", response.mensaje)],
            }

        res = response.resultados
        code = getattr(res[0], 'statusUUID', None) if res else getattr(response, 'status', None)
        cancelled = code in ('201', '202')  # cancelled or previously cancelled
        # no show code and response message if cancel was success
        msg = '' if cancelled else getattr(res[0] if res else response, 'mensaje', None)
        code = '' if cancelled else code

        errors = []
        if code:
            errors.append(_("Code : %s") % code)
        if msg:
            errors.append(_("Message : %s") % msg)
        if errors:
            return {'errors': errors}

        return {'success': True}

    def _l10n_mx_edi_solfact_sign_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_solfact_sign(invoice, credentials, cfdi)

    def _l10n_mx_edi_solfact_cancel_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_solfact_cancel(invoice, credentials, cfdi)

    def _l10n_mx_edi_solfact_sign_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_solfact_sign(move, credentials, cfdi)

    def _l10n_mx_edi_solfact_cancel_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_solfact_cancel(move, credentials, cfdi)

    def _l10n_mx_edi_get_sw_token(self, credentials):
        if credentials['password'] and not credentials['username']:
            # token is configured directly instead of user/password
            return {
                'token': credentials['password'].strip(),
            }

        try:
            headers = {
                'user': credentials['username'],
                'password': credentials['password'],
                'Cache-Control': "no-cache"
            }
            response = requests.post(credentials['login_url'], headers=headers)
            response.raise_for_status()
            response_json = response.json()
            return {
                'token': response_json['data']['token'],
            }
        except (requests.exceptions.RequestException, KeyError, TypeError) as req_e:
            return {
                'errors': [str(req_e)],
            }

    def _l10n_mx_edi_get_sw_credentials(self, move):
        if not move.company_id.l10n_mx_edi_pac_username or not move.company_id.l10n_mx_edi_pac_password:
            return {
                'errors': [_("The username and/or password are missing.")]
            }

        credentials = {
            'username': move.company_id.l10n_mx_edi_pac_username,
            'password': move.company_id.l10n_mx_edi_pac_password,
        }

        if move.company_id.l10n_mx_edi_pac_test_env:
            credentials.update({
                'login_url': 'https://services.test.sw.com.mx/security/authenticate',
                'sign_url': 'https://services.test.sw.com.mx/cfdi33/stamp/v3/b64',
                'cancel_url': 'https://services.test.sw.com.mx/cfdi33/cancel/csd',
            })
        else:
            credentials.update({
                'login_url': 'https://services.sw.com.mx/security/authenticate',
                'sign_url': 'https://services.sw.com.mx/cfdi33/stamp/v3/b64',
                'cancel_url': 'https://services.sw.com.mx/cfdi33/cancel/csd',
            })

        # Retrieve a valid token.
        credentials.update(self._l10n_mx_edi_get_sw_token(credentials))

        return credentials

    def _l10n_mx_edi_sw_call(self, url, headers, payload=None):
        try:
            response = requests.post(url, data=payload, headers=headers,
                                     verify=True, timeout=20)
        except requests.exceptions.RequestException as req_e:
            return {'status': 'error', 'message': str(req_e)}
        msg = ""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as res_e:
            msg = str(res_e)
        try:
            response_json = response.json()
        except JSONDecodeError:
            # If it is not possible get json then
            # use response exception message
            return {'status': 'error', 'message': msg}
        if (response_json['status'] == 'error' and
                response_json['message'].startswith('307')):
            # XML signed previously
            cfdi = base64.encodebytes(
                response_json['messageDetail'].encode('UTF-8'))
            cfdi = cfdi.decode('UTF-8')
            response_json['data'] = {'cfdi': cfdi}
            # We do not need an error message if XML signed was
            # retrieved then cleaning them
            response_json.update({
                'message': None,
                'messageDetail': None,
                'status': 'success',
            })
        return response_json

    def _l10n_mx_edi_sw_sign(self, move, credentials, cfdi):
        cfdi_b64 = base64.encodebytes(cfdi).decode('UTF-8')
        random_values = [random.choice(string.ascii_letters + string.digits) for n in range(30)]
        boundary = ''.join(random_values)
        payload = """--%(boundary)s
Content-Type: text/xml
Content-Transfer-Encoding: binary
Content-Disposition: form-data; name="xml"; filename="xml"

%(cfdi_b64)s
--%(boundary)s--
""" % {'boundary': boundary, 'cfdi_b64': cfdi_b64}
        payload = payload.replace('\n', '\r\n').encode('UTF-8')

        headers = {
            'Authorization': "bearer " + credentials['token'],
            'Content-Type': ('multipart/form-data; '
                             'boundary="%s"') % boundary,
        }

        response_json = self._l10n_mx_edi_sw_call(credentials['sign_url'], headers, payload=payload)

        try:
            cfdi_signed = response_json['data']['cfdi']
        except (KeyError, TypeError):
            cfdi_signed = None

        if cfdi_signed:
            return {
                'cfdi_signed': cfdi_signed.encode('UTF-8'),
                'cfdi_encoding': 'base64',
            }
        else:
            code = response_json.get('message')
            msg = response_json.get('messageDetail')
            errors = []
            if code:
                errors.append(_("Code : %s") % code)
            if msg:
                errors.append(_("Message : %s") % msg)
            return {'errors': errors}

    def _l10n_mx_edi_sw_cancel(self, move, credentials, cfdi):
        headers = {
            'Authorization': "bearer " + credentials['token'],
            'Content-Type': "application/json"
        }
        certificates = move.company_id.l10n_mx_edi_certificate_ids
        certificate = certificates.sudo().get_valid_certificate()

        cfdi_infos = move._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)

        payload = json.dumps({
            'rfc': cfdi_infos['supplier_rfc'],
            'b64Cer': certificate.content.decode('UTF-8'),
            'b64Key': certificate.key.decode('UTF-8'),
            'password': certificate.password,
            'uuid': cfdi_infos['uuid'],
        })
        response_json = self._l10n_mx_edi_sw_call(credentials['cancel_url'], headers, payload=payload.encode('UTF-8'))

        cancelled = response_json['status'] == 'success'
        if cancelled:
            return {
                'success': cancelled
            }

        code = response_json.get('message')
        msg = response_json.get('messageDetail')
        errors = []
        if code:
            errors.append(_("Code : %s") % code)
        if msg:
            errors.append(_("Message : %s") % msg)
        return {'errors': errors}

    def _l10n_mx_edi_sw_sign_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_sw_sign(invoice, credentials, cfdi)

    def _l10n_mx_edi_sw_cancel_invoice(self, invoice, credentials, cfdi):
        return self._l10n_mx_edi_sw_cancel(invoice, credentials, cfdi)

    def _l10n_mx_edi_sw_sign_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_sw_sign(move, credentials, cfdi)

    def _l10n_mx_edi_sw_cancel_payment(self, move, credentials, cfdi):
        return self._l10n_mx_edi_sw_cancel(move, credentials, cfdi)

    # -------------------------------------------------------------------------
    # BUSINESS FLOW: EDI
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == 'cfdi_3_3' or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'cfdi_3_3':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'MX' and \
            journal.company_id.currency_id.name == 'MXN'

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'cfdi_3_3':
            return super()._is_required_for_invoice(invoice)

        # Determine on which invoices the Mexican CFDI must be generated.
        return invoice.move_type in ('out_invoice', 'out_refund') and \
            invoice.country_code == 'MX' and \
            invoice.company_id.currency_id.name == 'MXN'

    def _is_required_for_payment(self, move):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'cfdi_3_3':
            return super()._is_required_for_payment(move)

        # Determine on which invoices the Mexican CFDI must be generated.
        if move.country_code != 'MX':
            return False

        if (move.payment_id or move.statement_line_id).l10n_mx_edi_force_generate_cfdi:
            return True

        reconciled_invoices = move._get_reconciled_invoices()
        return 'PPD' in reconciled_invoices.mapped('l10n_mx_edi_payment_policy')

    def _post_invoice_edi(self, invoices):
        # OVERRIDE
        edi_result = super()._post_invoice_edi(invoices)
        if self.code != 'cfdi_3_3':
            return edi_result

        for invoice in invoices:

            # == Check the configuration ==
            errors = self._l10n_mx_edi_check_configuration(invoice)
            if errors:
                edi_result[invoice] = {
                    'error': self._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors),
                }
                continue

            # == Generate the CFDI ==
            res = self._l10n_mx_edi_export_invoice_cfdi(invoice)
            if res.get('errors'):
                edi_result[invoice] = {
                    'error': self._l10n_mx_edi_format_error_message(_("Failure during the generation of the CFDI:"), res['errors']),
                }
                continue

            # == Call the web-service ==
            res = self._l10n_mx_edi_post_invoice_pac(invoice, res)
            if res.get('error'):
                edi_result[invoice] = res
                continue

            addenda = invoice.partner_id.l10n_mx_edi_addenda or invoice.partner_id.commercial_partner_id.l10n_mx_edi_addenda
            if addenda:
                if res['cfdi_encoding'] == 'base64':
                    res.update({
                        'cfdi_signed': base64.decodebytes(res['cfdi_signed']),
                        'cfdi_encoding': 'str',
                    })
                res['cfdi_signed'] = self._l10n_mx_edi_cfdi_append_addenda(invoice, res['cfdi_signed'], addenda)

            if res['cfdi_encoding'] == 'str':
                res.update({
                    'cfdi_signed': base64.encodebytes(res['cfdi_signed']),
                    'cfdi_encoding': 'base64',
                })

            # == Create the attachment ==
            cfdi_filename = ('%s-%s-MX-Invoice-3.3.xml' % (invoice.journal_id.code, invoice.payment_reference)).replace('/', '')
            cfdi_attachment = self.env['ir.attachment'].create({
                'name': cfdi_filename,
                'res_id': invoice.id,
                'res_model': invoice._name,
                'type': 'binary',
                'datas': res['cfdi_signed'],
                'mimetype': 'application/xml',
                'description': _('Mexican invoice CFDI generated for the %s document.') % invoice.name,
            })
            edi_result[invoice] = {'success': True, 'attachment': cfdi_attachment}

            # == Chatter ==
            invoice.with_context(no_new_invoice=True).message_post(
                body=_("The CFDI document was successfully created and signed by the government."),
                attachment_ids=cfdi_attachment.ids,
            )
        return edi_result

    def _cancel_invoice_edi(self, invoices):
        # OVERRIDE
        edi_result = super()._cancel_invoice_edi(invoices)
        if self.code != 'cfdi_3_3':
            return edi_result

        for invoice in invoices:

            # == Check the configuration ==
            errors = self._l10n_mx_edi_check_configuration(invoice)
            if errors:
                edi_result[invoice] = {'error': self._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors)}
                continue

            # == Call the web-service ==
            pac_name = invoice.company_id.l10n_mx_edi_pac

            credentials = getattr(self, '_l10n_mx_edi_get_%s_credentials' % pac_name)(invoice)
            if credentials.get('errors'):
                edi_result[invoice] = {'error': self._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors'])}
                continue

            signed_edi = invoice._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)
            res = getattr(self, '_l10n_mx_edi_%s_cancel_invoice' % pac_name)(invoice, credentials, cfdi_data)
            if res.get('errors'):
                edi_result[invoice] = {'error': self._l10n_mx_edi_format_error_message(_("PAC failed to cancel the CFDI:"), res['errors'])}
                continue

            edi_result[invoice] = res

            # == Chatter ==
            invoice.with_context(no_new_invoice=True).message_post(
                body=_("The CFDI document has been successfully cancelled."),
                subtype_xmlid='account.mt_invoice_validated',
            )

        return edi_result

    def _post_payment_edi(self, payments):
        # OVERRIDE
        edi_result = super()._post_payment_edi(payments)
        if self.code != 'cfdi_3_3':
            return edi_result

        for move in payments:

            # == Check the configuration ==
            errors = self._l10n_mx_edi_check_configuration(move)
            if errors:
                edi_result[move] = {
                    'error': self._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors),
                }
                continue

            # == Generate the CFDI ==
            res = self._l10n_mx_edi_export_payment_cfdi(move)
            if res.get('errors'):
                edi_result[move] = {
                    'error': self._l10n_mx_edi_format_error_message(_("Failure during the generation of the CFDI:"), res['errors']),
                }
                continue

            # == Call the web-service ==
            res = self._l10n_mx_edi_post_payment_pac(move, res)
            if res.get('error'):
                edi_result[move] = res
                continue

            # == Create the attachment ==
            cfdi_signed = res['cfdi_signed'] if res['cfdi_encoding'] == 'base64' else base64.encodebytes(res['cfdi_signed'])
            cfdi_filename = ('%s-%s-MX-Payment-10.xml' % (move.journal_id.code, move.name)).replace('/', '')
            cfdi_attachment = self.env['ir.attachment'].create({
                'name': cfdi_filename,
                'res_id': move.id,
                'res_model': move._name,
                'type': 'binary',
                'datas': cfdi_signed,
                'mimetype': 'application/xml',
                'description': _('Mexican payment CFDI generated for the %s document.') % move.name,
            })
            edi_result[move] = {'success': True, 'attachment': cfdi_attachment}

            # == Chatter ==
            message = _("The CFDI document has been successfully signed.")
            move.message_post(body=message, attachment_ids=cfdi_attachment.ids)
            if move.payment_id:
                move.payment_id.message_post(body=message, attachment_ids=cfdi_attachment.ids)

        return edi_result

    def _cancel_payment_edi(self, moves, ):
        # OVERRIDE
        edi_result = super()._cancel_payment_edi(moves)
        if self.code != 'cfdi_3_3':
            return edi_result

        for move in moves:

            # == Check the configuration ==
            errors = self._l10n_mx_edi_check_configuration(move)
            if errors:
                edi_result[move] = {'error': self._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors)}
                continue

            # == Call the web-service ==
            pac_name = move.company_id.l10n_mx_edi_pac

            credentials = getattr(self, '_l10n_mx_edi_get_%s_credentials' % pac_name)(move)
            if credentials.get('errors'):
                edi_result[move] = {'error': self._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors'])}
                continue

            signed_edi = move._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)
            res = getattr(self, '_l10n_mx_edi_%s_cancel_payment' % pac_name)(move, credentials, cfdi_data)
            if res.get('errors'):
                edi_result[move] = {'error': self._l10n_mx_edi_format_error_message(_("PAC failed to cancel the CFDI:"), res['errors'])}
                continue

            edi_result[move] = res

            # == Chatter ==
            message = _("The CFDI document has been successfully cancelled.")
            move.message_post(body=message)
            if move.payment_id:
                move.payment_id.message_post(body=message)

        return edi_result
