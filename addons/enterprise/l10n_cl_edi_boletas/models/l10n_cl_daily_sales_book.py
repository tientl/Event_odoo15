# -*- coding: utf-8 -*-
from itertools import groupby

import base64
import logging
from datetime import timedelta
from lxml import etree
from psycopg2 import OperationalError

from odoo import _, api, fields, models, _lt
from odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util import UnexpectedXMLResponse
from odoo.exceptions import UserError
from odoo.tools import float_repr, html_escape

_logger = logging.getLogger(__name__)

SII_STATUS_SALES_BOOK_RESULT = {
    **dict.fromkeys(['-11', 'REC', 'SOK', 'FOK', 'PRD', 'CRT'], 'ask_for_status'),
    **dict.fromkeys(['-3', 'RPT', 'RFR', 'VOF', 'RCT', 'RCH', 'RSC'], 'rejected'),
    'EPR': 'accepted',
    'RPR': 'objected',
}


class L10nClDailySalesBook(models.Model):
    _name = 'l10n_cl.daily.sales.book'
    _description = 'Daily Sales Book (CL)'
    _inherit = ['mail.thread', 'l10n_cl.edi.util']
    _rec_name = 'date'
    _order = 'date desc'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, readonly=True)
    l10n_cl_sii_send_ident = fields.Text(string='SII Send Identification', copy=False, readonly=True)
    move_ids = fields.One2many('account.move', 'l10n_cl_daily_sales_book_id')
    date = fields.Date(string='Date', default=lambda self: fields.Date.context_today(self.with_context(tz='America/Santiago')))
    send_sequence = fields.Integer(string='Send Sequence', default=1)
    l10n_cl_dte_status = fields.Selection([
        ('not_sent', 'Pending To Be Sent'),
        ('ask_for_status', 'Ask For Status'),
        ('accepted', 'Accepted'),
        ('objected', 'Accepted With Objections'),
        ('rejected', 'Rejected'),
        ('to_resend', 'To Resend'),
    ], string='SII Daily Sales Book Status', default='not_sent', copy=False, tracking=True,
        help="""Status of sending the DTE to the SII:
       - Not sent: the daily sales book has not been sent to SII but it has created.
       - Ask For Status: The daily sales book is asking for its status to the SII.
       - Accepted: The daily sales book has been accepted by SII.
       - Accepted With Objections: The daily sales book has been accepted with objections by SII.
       - Rejected: The daily sales book has been rejected by SII.
       - To resend: Boletas were added after the last send so it needs to be resent.""")
    l10n_cl_sii_send_file = fields.Many2one('ir.attachment', string='SII Send file', copy=False)

    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, '%s (%s)' % (r.date, r.send_sequence)))
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_already_accepted(self):
        if self.filtered(lambda x: x.l10n_cl_dte_status in ('accepted', 'objected', 'ask_for_status', 'to_resend')):
            raise UserError(_('You cannot delete a validated book.'))

    def _get_ranges(self, data):
        """Return a list of tuples with the ranges in the data.
        Example:
            data = [1, 2, 3, 8, 15, 16, 17, 20]
            -> [(1, 3), (8, 8), (15, 17), (20, 20)]
        """
        ranges = []
        for _, g in groupby(enumerate(sorted(data)), lambda x: x[0] - x[1]):
            group = [v for _, v in g]
            ranges.append((group[0], group[-1]))
        return ranges

    def _get_summary(self):
        summary = []
        for document_type in sorted(self.move_ids.mapped('l10n_latam_document_type_id.code')):
            values = {'document_type': document_type}
            # Get amounts
            move_ids = self.move_ids.filtered(lambda x: x.l10n_latam_document_type_id.code == document_type)
            vat_taxes = move_ids.line_ids.filtered(lambda x: x.tax_line_id.l10n_cl_sii_code == 14)
            lines_with_taxes = move_ids.invoice_line_ids.filtered(lambda x: x.tax_ids)
            lines_without_taxes = move_ids.invoice_line_ids.filtered(lambda x: not x.tax_ids)
            values.update({
                'vat_amount': float_repr(sum(vat_taxes.mapped('price_subtotal')), 0),
                # Sum of the subtotal amount affected by tax
                'subtotal_amount_taxable': float_repr(sum(lines_with_taxes.mapped('price_subtotal')), 0),
                # Sum of the subtotal amount not affected by tax
                'subtotal_amount_exempt': float_repr(sum(lines_without_taxes.mapped('price_subtotal')), 0),
                'vat_percent': '19.00' if lines_with_taxes else False,
                'total_amount': float_repr(sum(move_ids.mapped('amount_total')), 0),
            })
            document_numbers = [int(doc_number) for doc_number in move_ids.mapped('l10n_latam_document_number')]
            values.update({
                'total_documents': len(document_numbers),
                'documents_canceled': 0,
                'documents_used': len(document_numbers),
                'used_ranges': self._get_ranges(document_numbers),
                'cancelled_ranges': [],
            })
            summary.append(values)
        return summary

    def _create_month_calendar_report(self):
        now_date = fields.Date.context_today(self.with_context(tz='America/Santiago'))
        books = self.env['l10n_cl.daily.sales.book']
        # Create the month calendar report if not exists until the day before yesterday
        for day in range(1, now_date.day - 1):
            new_date = now_date.replace(day=day)
            if not self._get_report_by_date(new_date):
                books |= self._create_report(new_date)

        # Yesterday report must be created
        yesterday = now_date + timedelta(days=-1)
        yesterday_book = self._get_report_by_date(yesterday)
        if not yesterday_book:
            yesterday_book = self._create_report(yesterday)
        books |= yesterday_book

        return books

    def _create_month_calendar_report_check(self):
        if self.env['l10n_cl.dte.caf'].search([
            ('l10n_latam_document_type_id.code', 'in', ['39', '41'])]).mapped('company_id').filtered(
                lambda x: x.l10n_cl_dte_service_provider):
            return self._create_month_calendar_report()

    def _get_report_by_date(self, date):
        return self.search([('company_id', '=', self.env.company.id), ('date', '=', date)])

    def _get_move_ids_without_daily_sales_book_by_date(self, date):
        daily_sales_book_candidate_moves = self.env['account.move'].search([
            ('l10n_latam_document_type_id.code', 'in', ['39', '41', '61']),
            ('invoice_date', '=', date),
            ('company_id', '=', self.env.company.id),
            ('l10n_cl_dte_status', 'in', ['accepted', 'objected']),
            ('l10n_cl_daily_sales_book_id', '=', False)
        ])
        final_book_set = daily_sales_book_candidate_moves.filtered(
            lambda x: x.l10n_latam_document_type_id.code in ['39', '41'] or
                      x.l10n_latam_document_type_id.code == '61' and
                      x.reversed_entry_id.l10n_latam_document_type_id.code in ['39', '41']).ids
        return final_book_set

    def _update_report(self):
        if self.l10n_cl_dte_status in ['ask_for_status', 'rejected']:
            _logger.info(_('Sales Book for day %s has not been updated due to the current status is %s.') % (
                self.date, self.l10n_cl_dte_status))
            return None
        move_ids = self.move_ids.ids + self._get_move_ids_without_daily_sales_book_by_date(self.date)
        self.write({'send_sequence': self.send_sequence + 1, 'move_ids': [(6, 0, move_ids)]})
        self._create_dte()

    @api.model
    def _create_report(self, date):
        move_ids = self._get_move_ids_without_daily_sales_book_by_date(date)
        report = self.create({'date': date, 'move_ids': [(6, 0, move_ids)]})
        report._create_dte()
        return report

    def _create_dte(self):
        items = self._get_summary()
        if not items:  # The sales reporting should have at least one summary
            items.append({
                'document_type': '39',
                'subtotal_amount_taxable': 0,
                'subtotal_amount_exempt': 0,
                'total_amount': 0,
                'total_documents': 0,
                'documents_canceled': 0,
                'documents_used': 0,
                'used_ranges': [],
                'cancelled_ranges': [],
            })
        doc_id = 'CF_' + self.date.strftime('%Y-%m-%d')
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        xml_book = self.env.ref('l10n_cl_edi_boletas.dss_template')._render({
            'object': self,
            'rut_sends': digital_signature.subject_serial_number,
            'id': doc_id,
            'format_vat': self.env['l10n_cl.edi.util']._l10n_cl_format_vat,
            'timestamp': self.env['l10n_cl.edi.util']._get_cl_current_strftime(),
            'items': items,
            '__keep_empty_lines': True,
        })
        dte = self.env['l10n_cl.edi.util']._sign_full_xml(xml_book, digital_signature, doc_id, 'consu')
        attachment = self.env['ir.attachment'].create({
            'name': '%s.xml' % doc_id,
            'res_id': self.id,
            'res_model': self._name,
            'raw': dte.encode('ISO-8859-1', 'replace'),
            'type': 'binary',
        })
        self.write({'l10n_cl_dte_status': 'not_sent', 'l10n_cl_sii_send_file': attachment.id})
        self.message_post(body=_('DTE has been created'), attachment_ids=[attachment.id])

    def _l10n_cl_get_sii_reception_status_message(self, sii_response_status):
        """Get the value of the code returns by SII once the DTE has been sent to the SII."""
        return {
            '0': _lt('Upload OK'),
            '1': _lt('Sender Does Not Have Permission To Send'),
            '2': _lt('File Size Error (Too Big or Too Small)'),
            '3': _lt('Incomplete File (Size <> Parameter size)'),
            '5': _lt('Not Authenticated'),
            '6': _lt('Company Not Authorized to Send Files'),
            '7': _lt('Invalid Schema'),
            '8': _lt('Document Signature'),
            '9': _lt('System Locked'),
            'Otro': _lt('Internal Error'),
        }.get(sii_response_status, sii_response_status)

    def l10n_cl_send_dte_to_sii(self, retry_send=True):
        if not self.company_id.l10n_cl_dte_service_provider:
            self.message_post(body=_('Cannot send Sales Book Report to SII due to the service provider is not set in '
                                     'your company. Please go to your company and select one'))
            return None
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(f'SELECT 1 FROM {self._table} WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])
        except OperationalError as e:
            if e.pgcode == '55P03':
                if not self.env.context.get('cron_skip_connection_errs'):
                    raise UserError(_('This electronic document is being processed already.'))
                return
            raise e
        # To avoid double send on double-click
        if self.l10n_cl_dte_status != "not_sent":
            return None
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        response = self._send_xml_to_sii(
            self.company_id.l10n_cl_dte_service_provider,
            self.company_id.website,
            self.company_id.vat,
            self.l10n_cl_sii_send_file.name,
            base64.b64decode(self.l10n_cl_sii_send_file.datas),
            digital_signature
        )
        if not response:
            return None

        response_parsed = etree.fromstring(response)
        self.l10n_cl_sii_send_ident = response_parsed.findtext('TRACKID')
        sii_response_status = response_parsed.findtext('STATUS')
        if sii_response_status == '5':
            digital_signature.last_token = False
            _logger.error('The response status is %s. Clearing the token.',
                          self._l10n_cl_get_sii_reception_status_message(sii_response_status))
            if retry_send:
                _logger.info('Retrying send DTE to SII')
                self.l10n_cl_send_dte_to_sii(retry_send=False)

            # cleans the token and keeps the l10n_cl_dte_status until new attempt to connect
            # would like to resend from here, because we cannot wait till tomorrow to attempt
            # a new send
        else:
            self.l10n_cl_dte_status = 'ask_for_status' if sii_response_status == '0' else 'rejected'
        self.message_post(body=_('DTE has been sent to SII with response: %s.') %
                               self._l10n_cl_get_sii_reception_status_message(sii_response_status))

    def l10n_cl_verify_dte_status(self):
        if not self.company_id.l10n_cl_dte_service_provider:
            self.message_post(body=_('Cannot verify the status of the Sales Book Report to SII due to the service '
                                     'provider is not set in your company. Please go to your company and select one'))
            return None
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        response = self._get_send_status(
            self.company_id.l10n_cl_dte_service_provider,
            self.l10n_cl_sii_send_ident,
            self.env['l10n_cl.edi.util']._l10n_cl_format_vat(self.company_id.vat),
            digital_signature)
        if not response:
            self.l10n_cl_dte_status = 'ask_for_status'
            digital_signature.last_token = False
            return None

        # The response from SII has the encoding declaration then it's re-encoding with encode()
        # to ensure the string could be parsed
        response_parsed = etree.fromstring(response.encode())

        if response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO') in ['001', '002', '003']:
            digital_signature.last_token = False
            _logger.error('Token is invalid.')
            return

        try:
            self.l10n_cl_dte_status = self._analyze_sii_sales_book_result(response_parsed)
        except UnexpectedXMLResponse:
            # The assumption here is that the unexpected input is intermittent,
            # so we'll retry later. If the same input appears regularly, it should
            # be handled properly in _analyze_sii_sales_book_result.
            _logger.error("Unexpected XML response:\n{}".format(response))
            return

        self.message_post(
            body=_('Asking for DTE status with response:') +
                 '<br/><li><b>ESTADO</b>: %s</li><li><b>GLOSA</b>: %s</li><li><b>NUM_ATENCION</b>: %s</li>' % (
                     html_escape(response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO')),
                     html_escape(response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/GLOSA')),
                     html_escape(response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/NUM_ATENCION'))))

    def _analyze_sii_sales_book_result(self, xml_message):
        """Returns the status of the DTE from the xml_message. The status could be:
        ask_for_status, rejected, accepted, objected
        """
        status = xml_message.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO')
        if status in SII_STATUS_SALES_BOOK_RESULT:
            return SII_STATUS_SALES_BOOK_RESULT[status]
        else:
            raise UnexpectedXMLResponse()

    def _l10n_cl_ask_dte_status(self):
        for record in self.search([('l10n_cl_dte_status', '=', 'ask_for_status')]):
            record.l10n_cl_verify_dte_status()

    def _l10n_cl_send_books_to_sii(self):
        for book in self:
            book.l10n_cl_send_dte_to_sii()
            if book.l10n_cl_dte_status == 'ask_for_status':
                book.l10n_cl_verify_dte_status()

    def _send_pending_sales_book_report_to_sii(self):
        for report in self.search([('l10n_cl_dte_status', 'in', ['not_sent', 'to_resend'])]):
            report.l10n_cl_send_dte_to_sii()

    def l10n_cl_retry_daily_sales_book_report(self):
        self._update_report()
        self.l10n_cl_send_dte_to_sii()
        self.l10n_cl_verify_dte_status()

    @api.model
    def _cron_run_sii_sales_book_report_process(self):
        for company in self.env['res.company'].search([('partner_id.country_id.code', '=', 'CL')]):
            self_skip = self.with_company(company=company.id).with_context(cron_skip_connection_errs=True)
            books = self_skip._create_month_calendar_report_check()
            if not books:
                continue
            self.env.cr.commit()
            books._l10n_cl_send_books_to_sii()
            self_skip._send_pending_sales_book_report_to_sii()
        if fields.Date.today() > fields.Date.from_string('2022-08-02'):
            self.env.ref('l10n_cl_edi_boletas.ir_cron_send_daily_sales_book').active = False

    def _cron_ask_daily_sales_book_status(self):
        for company in self.env['res.company'].search([('partner_id.country_id.code', '=', 'CL')]):
            self.with_company(company=company.id).with_context(cron_skip_connection_errs=True)._l10n_cl_ask_dte_status()
        if fields.Date.today() > fields.Date.from_string('2022-08-02'):
            self.env.ref('l10n_cl_edi_boletas.ir_cron_ask_daily_sales_book_status').active = False
