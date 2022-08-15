# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import division

from contextlib import contextmanager
import locale
import re
import json
import logging
from unicodedata import normalize
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_compare, translate

_logger = logging.getLogger(__name__)


class MxReportPartnerLedger(models.AbstractModel):
    _name = "l10n_mx.account.diot"
    _inherit = "account.report"
    _description = "DIOT"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_all_entries = None

    def _get_columns_name(self, options):
        return [
            {},
            {'name': _('Type of Third')},
            {'name': _('Type of Operation')},
            {'name': _('VAT')},
            {'name': _('Country')},
            {'name': _('Nationality')},
            {'name': _('Paid 16%'), 'class': 'number'},
            {'name': _('Paid 16% - Non-Creditable'), 'class': 'number'},
            {'name': _('Paid 8 %'), 'class': 'number'},
            {'name': _('Paid 8 % - Non-Creditable'), 'class': 'number'},
            {'name': _('Importation 16%'), 'class': 'number'},
            {'name': _('Paid 0%'), 'class': 'number'},
            {'name': _('Exempt'), 'class': 'number'},
            {'name': _('Withheld'), 'class': 'number'},
            {'name': _('Refunds'), 'class': 'number'},
        ]

    def _do_query_group_by_account(self, options, line_id):
        select = ',\"account_move_line_account_tax_rel\".account_tax_id tax_id, SUM(\"account_move_line\".debit) debit, SUM(\"account_move_line\".credit) credit'  # noqa
        sql = "SELECT \"account_move_line\".partner_id%s FROM %s WHERE %s%s AND \"account_move_line_account_tax_rel\".account_move_line_id = \"account_move_line\".id GROUP BY \"account_move_line\".partner_id, \"account_move_line_account_tax_rel\".account_tax_id"  # noqa
        journal_ids = []
        for company in self.env.companies.filtered('tax_cash_basis_journal_id'):
            journal_ids.append(company.tax_cash_basis_journal_id.id)
        tax_ids = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', 'purchase'),
            ('tax_exigibility', '=', 'on_payment')])
        account_tax_ids = tax_ids.mapped('invoice_repartition_line_ids.account_id')
        domain = [
            ('journal_id', 'in', journal_ids),
            ('account_id', 'not in', account_tax_ids.ids),
            ('tax_ids', 'in', tax_ids.ids),
            ('date', '>=', options['date']['date_from']),
            ('move_id.state', '=', 'posted'),
        ]
        tables, where_clause, where_params = self._query_get(options, domain=domain)
        tables += ',"account_move_line_account_tax_rel"'
        line_clause = line_id and\
            ' AND \"account_move_line\".partner_id = ' + str(line_id) or ''
        query = sql % (select, tables, where_clause, line_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.dictfetchall()
        result = {}
        for res in results:
            result.setdefault(res['partner_id'], {}).setdefault(res['tax_id'], [res['debit'], res['credit']])
        return result

    def _group_by_partner_id(self, options, line_id):
        partners = {}
        results = self._do_query_group_by_account(options, line_id)
        journal_ids = []
        for company in self.env.companies.filtered('tax_cash_basis_journal_id'):
            journal_ids.append(company.tax_cash_basis_journal_id.id)
        tax_ids = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', 'purchase'),
            ('tax_exigibility', '=', 'on_payment')])
        account_tax_ids = tax_ids.mapped('invoice_repartition_line_ids.account_id')
        base_domain = [
            ('date', '<=', options['date']['date_to']),
            ('date', '>=', options['date']['date_from']),
            ('company_id', 'in', self.env.companies.ids),
            ('journal_id', 'in', journal_ids),
            ('account_id', 'not in', account_tax_ids.ids),
            ('tax_ids', 'in', tax_ids.ids),
        ]
        without_vat = []
        without_too = []
        for partner_id, result in results.items():
            domain = list(base_domain)  # copying the base domain
            domain.append(('partner_id', '=', partner_id))
            partner = self.env['res.partner'].browse(partner_id)
            partners[partner] = result
            if not self._context.get('print_mode'):
                #  fetch the 81 first amls. The report only displays the first
                # 80 amls. We will use the 81st to know if there are more than
                # 80 in which case a link to the list view must be displayed.
                partners[partner]['lines'] = self.env['account.move.line'].search(domain, limit=81)
            else:
                partners[partner]['lines'] = self.env['account.move.line'].search(domain)

            if partner.country_id.code == "MX" and not partner.vat and partners[partner]['lines']:
                without_vat.append(partner.name)

            if not partner.l10n_mx_type_of_operation and partners[partner]['lines']:
                without_too.append(partner.name)

        if (without_vat or without_too) and self._context.get('raise'):
            msg = _('The report cannot be generated because of: ')
            msg += (
                _('\n\nThe following partners do not have a '
                  'valid RFC: \n - %s') %
                '\n - '.join(without_vat) if without_vat else '')
            msg += (
                _('\n\nThe following partners do not have a '
                  'type of operation: \n - %s') %
                '\n - '.join(without_too) if without_too else '')
            msg += _(
                '\n\nPlease fill the missing information in the partners and '
                'try again.')

            raise UserError(msg)

        return partners

    @api.model
    def get_taxes_with_financial_tag(self, tag_xmlid, allowed_tax_ids):
         rep_lines = self.env['account.tax.repartition.line'].search([
             '|', ('invoice_tax_id', 'in', allowed_tax_ids), ('refund_tax_id', 'in', allowed_tax_ids),
             ('tag_ids', 'in', self.env['ir.model.data']._xmlid_to_res_id(tag_xmlid))])

         return rep_lines.mapped('invoice_tax_id') | rep_lines.mapped('refund_tax_id')

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        if line_id:
            line_id = line_id.replace('partner_', '')
        grouped_partners = self._group_by_partner_id(options, line_id)
        # Aml go back to the beginning of the user chosen range but the
        # amount on the partner line should go back to either the beginning of
        # the fy or the beginning of times depending on the partner
        sorted_partners = sorted(grouped_partners, key=lambda p: p.name or '')
        unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')
        tag_16 = self.env.ref('l10n_mx.tag_diot_16')
        tag_16_non_cre = self.env.ref('l10n_mx.tag_diot_16_non_cre')
        tag_8 = self.env.ref('l10n_mx.tag_diot_8')
        tag_8_non_cre = self.env.ref('l10n_mx.tag_diot_8_non_cre')
        tag_imp = self.env.ref('l10n_mx.tag_diot_16_imp')
        tag_0 = self.env.ref('l10n_mx.tag_diot_0')
        tag_ret = self.env.ref('l10n_mx.tag_diot_ret')
        tag_exe = self.env.ref('l10n_mx.tag_diot_exento')

        purchase_tax_ids = self.env['account.tax'].with_context(active_test=False).search([('type_tax_use', '=', 'purchase')]).ids
        diot_common_domain = ['|', ('invoice_tax_id', 'in', purchase_tax_ids), ('refund_tax_id', 'in', purchase_tax_ids)]

        company = self.env.company.id
        taxes_dict = {}
        for tag in (tag_16, tag_16_non_cre, tag_8, tag_8_non_cre, tag_imp, tag_0, tag_exe, tag_ret):
            taxes = self.env['account.tax.repartition.line']\
                .with_context(active_test=False)\
                .search([('tag_ids', 'in', tag.ids), ('company_id', '=', self.env.company.id)] + diot_common_domain)\
                .mapped('tax_id')
            taxes_dict.setdefault(tag, taxes)

        grouped_taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', 'purchase'),
            ('company_id', '=', company),
            ('amount_type', '=', 'group')])
        taxes_in_groups = self.env['account.tax'].with_context(active_test=False)
        if grouped_taxes:
            self.env.cr.execute(
                """
                SELECT child_tax
                FROM account_tax_filiation_rel
                WHERE parent_tax IN %s
                """, [tuple(grouped_taxes.ids)])
            taxes_in_groups = taxes_in_groups.browse([x[0] for x in self.env.cr.fetchall()])
        for partner in sorted_partners:
            amls = grouped_partners[partner]['lines']
            if not amls:
                continue
            if not partner:
                for line in amls:
                    lines.append({
                        'id': str(line.id),
                        'name': '',
                        'columns': [{'name': ''}],
                        'level': 1,
                        'colspan': 10
                    })
                continue
            p_columns = [
                partner.l10n_mx_type_of_third or '', partner.l10n_mx_type_of_operation or '',
                partner.vat or '', partner.country_id.code or '',
                self.str_format(partner.l10n_mx_nationality, True)]
            partner_data = grouped_partners[partner]  # {<tax_id>: [<debit>, <credit>], ..., 'lines': <amls>}
            total_withheld = total_credit = 0
            for tag, taxes in taxes_dict.items():
                total_partner_debit = 0
                for tax in taxes:
                    debit, credit = partner_data.get(tax.id, [0, 0])
                    balance = debit - credit
                    if tag == tag_16 and tax in taxes_in_groups:
                        diff = 16 - tax.amount
                        total_withheld += diff * balance / 100
                    if tag == tag_ret:
                        total_withheld += abs(balance / (100 / tax.amount))
                        continue
                    total_partner_debit += debit
                    total_credit += credit
                if tag != tag_ret:
                    p_columns.append(total_partner_debit)
            p_columns.append(total_withheld)
            p_columns.append(total_credit)
            unfolded = 'partner_' + str(partner.id) in options.get('unfolded_lines') or unfold_all
            lines.append({
                'id': 'partner_' + str(partner.id),
                'name': self.str_format(partner.name)[:45],
                'columns': [{'name': v if index < 5 else int(round(v, 0))} for index, v in enumerate(p_columns)],
                'level': 2,
                'unfoldable': True,
                'unfolded': unfolded,
            })
            if not (unfolded):
                continue
            progress = 0
            domain_lines = []
            amls = grouped_partners[partner]['lines']
            too_many = False
            if len(amls) > 80 and not self._context.get('print_mode'):
                amls = amls[:80]
                too_many = True
            for line in amls:
                line_debit = line.debit
                line_credit = line.credit
                progress = progress + line_debit - line_credit
                name = line.display_name
                name = name[:32] + "..." if len(name) > 35 else name
                columns = ['', '', '', '']
                columns.append('')
                balance_withheld = line_credit = 0
                for tag, taxes in taxes_dict.items():
                    line_debit = 0
                    for tax in taxes.filtered(lambda t: t in line.tax_ids):
                        balance = line.debit - line.credit
                        if tag == tag_16 and tax in taxes_in_groups:
                            diff = 16 - tax.amount
                            balance_withheld += diff * balance / 100
                        if tag == tag_ret:
                            balance_withheld += abs(balance / (100 / tax.amount))
                            continue
                        line_debit += line.debit
                        line_credit += line.credit
                    if tag != tag_ret:
                        columns.append(self.format_value(line_debit))
                columns.append(self.format_value(balance_withheld))
                columns.append(self.format_value(line_credit))
                if line.payment_id:
                    caret_type = 'account.payment'
                else:
                    caret_type = 'account.move'
                domain_lines.append({
                    'id': str(line.id),
                    'parent_id': 'partner_' + str(partner.id),
                    'name': name,
                    'columns': [{'name':v} for v in columns],
                    'caret_options': caret_type,
                    'level': 1,
                })
            domain_lines.append({
                'id': 'total_' + str(partner.id),
                'parent_id': 'partner_' + str(partner.id),
                'class': 'o_account_reports_domain_total',
                'name': _('Total') + ' ' + partner.name,
                'columns': [{'name': v if index < 5 else self.format_value(v)} for index, v in enumerate(p_columns)],
                'level': 1,
            })
            if too_many:
                domain_lines.append({
                    'id': 'too_many_' + str(partner.id),
                    'parent_id': 'partner_' + str(partner.id),
                    'name': _('There are more than 80 items in this list, '
                              'click here to see all of them'),
                    'colspan': 10,
                    'columns': [{}],
                    'level': 3,
                })
            lines += domain_lines
        return lines

    __diot_supplier_re = re.compile(u'''[^A-Za-z0-9 Ññ&]''')
    __diot_nationality_re = re.compile(u'''[^rA-Za-z0-9 Ññ]''')

    @staticmethod
    def str_format(text, is_nationality=False):
        if not text:
            return ''
        trans_tab = {
            ord(char): None for char in (
                u'\N{COMBINING GRAVE ACCENT}',
                u'\N{COMBINING ACUTE ACCENT}',
                u'\N{COMBINING DIAERESIS}',
            )
        }
        text_n = normalize(
            'NFKC', normalize('NFKD', text).translate(trans_tab))
        check_re = MxReportPartnerLedger.__diot_supplier_re
        if is_nationality:
            check_re = MxReportPartnerLedger.__diot_nationality_re
        return check_re.sub('', text_n)

    @api.model
    def _get_report_name(self):
        return _('DIOT')

    def _get_reports_buttons(self, options):
        buttons = super(MxReportPartnerLedger, self)._get_reports_buttons(options)
        buttons += [{'name': _('DIOT (txt)'), 'sequence': 3, 'action': 'print_txt', 'file_export_type': _('DIOT')}]
        buttons += [{'name': _('DPIVA (txt)'), 'sequence': 4, 'action': 'print_dpiva_txt', 'file_export_type': _('DPIVA')}]
        return buttons

    def print_dpiva_txt(self, options):
        options.update({'is_dpiva': True})
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'output_format': 'txt',
                'financial_id': self.env.context.get('id'),
            }
        }

    def get_txt(self, options):
        ctx = self._set_context(options)
        ctx.update({'no_format':True, 'print_mode':True, 'raise': True})
        if options.get('is_dpiva'):
            return self.with_context(ctx)._l10n_mx_dpiva_txt_export(options)
        return self.with_context(ctx)._l10n_mx_diot_txt_export(options)

    @contextmanager
    def _custom_setlocale(self):
        old_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'es_MX.utf8')
        except locale.Error:
            _logger.info('Error when try to set locale "es_MX". Please '
                         'contact your system administrator.')
        try:
            yield
        finally:
            locale.setlocale(locale.LC_TIME, old_locale)

    def _l10n_mx_dpiva_txt_export(self, options):
        txt_data = self._get_lines(options)
        lines = ''
        date = fields.datetime.strptime(options['date']['date_from'], DEFAULT_SERVER_DATE_FORMAT)
        with self._custom_setlocale():
            month = date.strftime("%B").capitalize()

        for line in txt_data:
            if not line.get('id').startswith('partner_'):
                continue
            columns = line.get('columns', [])
            if not sum([c.get('name', 0) for c in columns[5:]]):
                continue
            data = [''] * 48
            data[0] = '1.0'  # Version
            data[1] = date.year  # Fiscal Year
            data[2] = 'MES'  # Cabling value
            data[3] = month  # Period
            data[4] = 1  # 1 Because has data
            data[5] = 1  # 1 = Normal, 2 = Complementary (Not supported now).
            data[8] = len([x for x in txt_data if x.get(
                'parent_id') == line.get('id') and 'total' not in x.get(
                    'id', '')])  # Count the operations
            for num in range(9, 26):
                data[num] = '0'
            data[26] = columns[0]['name']  # Supplier Type
            data[27] = columns[1]['name']  # Operation Type
            data[28] = columns[2]['name'] if columns[0]['name'] == '04' else ''  # Federal Taxpayer Registry Code
            data[29] = columns[2]['name'] if columns[0]['name'] != '04' else ''  # Fiscal ID
            data[30] = u''.join(line.get('name', '')).encode('utf-8').strip().decode('utf-8') if columns[0]['name'] != '04' else ''  # Name
            data[31] = columns[3]['name'] if columns[0]['name'] != '04' else ''  # Country
            data[32] = u''.join(columns[4]['name']).encode('utf-8').strip().decode('utf-8') if columns[0]['name'] != '04' else ''  # Nationality
            data[33] = int(columns[5]['name']) if columns[5]['name'] else ''  # 16%
            data[36] = int(columns[7]['name']) if columns[7]['name'] else ''  # 8%
            data[39] = int(columns[9]['name']) if columns[9]['name'] else ''  # 16% - Importation
            data[44] = int(columns[10]['name']) if columns[10]['name'] else ''  # 0%
            data[45] = int(columns[11]['name']) if columns[11]['name'] else ''  # Exempt
            data[46] = int(columns[12]['name']) if columns[12]['name'] else ''  # Withheld
            data[47] = int(columns[13]['name']) if columns[13]['name'] else ''  # Refunds
            lines += '|%s|\n' % '|'.join(str(d) for d in data)
        return lines

    def _l10n_mx_diot_txt_export(self, options):
        txt_data = self._get_lines(options)
        lines = ''
        for line in txt_data:
            if not line.get('id').startswith('partner_'):
                continue
            columns = line.get('columns', [])
            if not sum([c.get('name', 0) for c in columns[5:]]):
                continue
            data = [''] * 25
            data[0] = columns[0]['name']  # Supplier Type
            data[1] = columns[1]['name']  # Operation Type
            data[2] = columns[2]['name'] if columns[0]['name'] == '04' else ''  # Tax Number
            data[3] = columns[2]['name'] if columns[0]['name'] != '04' else ''  # Tax Number for Foreigners
            data[4] = u''.join(line.get('name', '')).encode('utf-8').strip().decode('utf-8') if columns[0]['name'] != '04' else ''  # Name
            data[5] = columns[3]['name'] if columns[0]['name'] != '04' else ''  # Country
            data[6] = u''.join(columns[4]['name']).encode('utf-8').strip().decode('utf-8') if columns[0]['name'] != '04' else ''  # Nationality
            data[7] = int(columns[5]['name']) if columns[5]['name'] else ''  # 16%
            data[9] = int(columns[6]['name']) if columns[6]['name'] else ''  # 16% Non-Creditable
            data[12] = int(columns[7]['name']) if columns[7]['name'] else ''  # 8%
            data[14] = int(columns[8]['name']) if columns[8]['name'] else ''  # 8% Non-Creditable
            data[15] = int(columns[9]['name']) if columns[9]['name'] else ''  # 16% - Importation
            data[20] = int(columns[10]['name']) if columns[10]['name'] else ''  # 0%
            data[21] = int(columns[11]['name']) if columns[11]['name'] else ''  # Exempt
            data[22] = int(columns[12]['name']) if columns[12]['name'] else ''  # Withheld
            data[23] = int(columns[13]['name']) if columns[13]['name'] else ''  # Refunds
            lines += '|'.join(str(d) for d in data) + '\n'
        return lines
