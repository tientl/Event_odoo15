# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.release import version

try:
    from stdnum.au.abn import is_valid_abn
except ImportError:
    is_valid_abn = None

RUN_TYPE = 'P'  # T for test or P for production

VALID_STATES = {'ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'OTH'}


class TaxReport(models.AbstractModel):
    """Generate the TPAR for Australia.

    This file was generated using https://softwaredevelopers.ato.gov.au/TPARspecification
    as a reference.
    """

    _name = 'l10n.au.tax.report'
    _description = "Taxable Payments Annual Reports (TPAR) for Australia"
    _inherit = 'account.report'

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_cash_basis = True

    def _get_country_for_fiscal_position_filter(self, options):
        return self.env.ref('base.au')

    def _get_report_name(self):
        return _('Taxable Payments Annual Reports (TPAR)')

    def _get_data(self, options, raise_warning=False):
        ctx = self._set_context(options)
        self.with_context(ctx)._prepare_lines_for_cash_basis()
        params = {
            'company_id': self.env.company.id,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'tag_tpar_id': self.env.ref('l10n_au.service_tag').id,
            'tag_withheld_id': self.env.ref('l10n_au.tax_withheld_tag').id,
        }
        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['res.partner'].flush()

        query = """
            SELECT
                payee.id as id,
                payee.vat as vat,
                payee.name as name,
                payee.name as commercial_partner_name,
                payee.street as street,
                payee.street2 as street2,
                payee.city as city,
                payee_state.name as state_name,
                payee_state.code as state_code,
                payee.zip as zip,
                payee_country.name as country_name,
                payee.phone as phone,
                payee_bank.sanitized_acc_number as account_number,
                payee.email as email,
                -- # 6.61
                -- the total of all payments made to the payee for the financial year (which may be different to invoiced amounts). It includes:
                -- • any GST in the payments
                -- • any tax withheld where an ABN was not quoted, and
                -- • the market value of any non-cash benefits
                COALESCE(SUM(
                    CASE WHEN journal.type IN ('bank', 'cash') THEN aml.credit ELSE 0 END
                ), 0) AS gross_paid,
                -- # 6.62
                -- if tax is withheld from payments where an ABN was not quoted, this can be reported
                -- in either a Taxable payments annual report or a PAYG withholding where ABN not
                -- quoted - annual report. If those amounts are included in the Taxable payments annual
                -- report, this field must contain the amount of tax withheld from all relevant payments
                -- for the financial year. This amount includes any amounts withheld on the market value
                -- of non-cash benefits. The amount must be reported in whole dollars.
                COALESCE(-SUM(
                    CASE WHEN aml_tag.account_account_tag_id = %(tag_withheld_id)s THEN aml.balance ELSE 0 END
                ), 0) AS tax_withheld,
                -- # 6.63
                -- the total of any GST included in the amounts paid
                COALESCE(SUM(
                    CASE WHEN aml_tag.account_account_tag_id = %(tag_tpar_id)s THEN aml.balance ELSE 0 END
                ), 0) AS total_gst
            FROM res_partner payee
            LEFT JOIN res_country_state payee_state ON payee_state.id = payee.state_id
            LEFT JOIN res_country payee_country ON payee_country.id = payee.country_id
            LEFT JOIN res_partner_bank payee_bank ON payee_bank.partner_id = payee.id
            LEFT JOIN account_move_line aml ON aml.date >= %(date_from)s
                                           AND aml.date <= %(date_to)s
                                           AND aml.company_id = %(company_id)s
                                           AND aml.partner_id = payee.id
            LEFT JOIN account_journal journal ON aml.journal_id = journal.id
            LEFT JOIN account_account_tag_account_move_line_rel aml_tag ON aml.id = aml_tag.account_move_line_id
            GROUP BY payee.id, payee.vat, payee.name, payee.name, payee.street, payee.street2, payee.city, payee_state.name, payee_state.code, payee.zip, payee_country.name, payee.phone, payee_bank.sanitized_acc_number, payee.email
            HAVING bool_or(aml_tag.account_account_tag_id IN (%(tag_withheld_id)s, %(tag_tpar_id)s))
            ORDER BY payee.name
        """

        self.env.cr.execute(query, params)
        partner_values = self.env.cr.dictfetchall()
        for p in partner_values:
            if p.get('total_gst', 0) > p.get('gross_paid', 0) and raise_warning:
                raise UserError(_('The total GST is higher than the Gross Paid for %s.', p['name']))
        return partner_values

    def _get_columns_name(self, options):
        return [{}, {'name': _('ABN')}, {'name': _('Total GST'), 'class': 'number'}, {'name': _('Gross Paid'), 'class': 'number'}, {'name': _('Tax Withheld'), 'class': 'number'}]

    def _get_lines(self, options, line_id=None):
        data = self._get_data(options)
        lines = []
        for row in data:
            lines += [{
                'id': row['id'],
                'caret_options': 'res.partner',
                'model': 'res.partner',
                'name': row['name'],
                'columns': [
                    {'name': row['vat']},
                    {'name': self.format_value(row['total_gst']), 'no_format_name': row['total_gst']},
                    {'name': self.format_value(row['gross_paid']), 'no_format_name': row['gross_paid']},
                    {'name': self.format_value(row['tax_withheld']), 'no_format_name': row['tax_withheld']},
                ],
            }]

        return lines

    def _get_reports_buttons(self, options):
        buttons = super(TaxReport, self)._get_reports_buttons(options)
        return buttons + [{'name': _('TPAR'), 'sequence': 3, 'action': 'print_txt', 'file_export_type': _('TPAR')}]

    def get_txt(self, options):
        sender_data = {
            'vat': self.get_vat_for_export(options),
            'name': self.env.company.name,
            'commercial_partner_name': self.env.company.name,
            'street': self.env.company.street,
            'street2': self.env.company.street2,
            'city': self.env.company.city,
            'state_name': self.env.company.state_id.name,
            'state_code': self.env.company.state_id.code,
            'zip': self.env.company.zip,
            'country_name': self.env.company.country_id.name,
            'phone': self.env.company.phone,
            'email': self.env.company.email,
        }
        self._validate_partner(sender_data)
        data = self._get_data(options, raise_warning=True)
        lines = [self._sender_data_record_1(options, sender_data), self._sender_data_record_2(sender_data), self._sender_data_record_3(sender_data)]
        lines += [self._payer_identity_data_record(options, sender_data), self._software_data_record()]
        lines += [self._payee_data_record(d) for d in data]
        lines += [self._file_total_data_record(len(lines) + 1)]
        for line in lines:
            if len(line) != 996:
                raise UserError(_('There was an error while writing the file (line length not 996).'
                                  '\nPlease contact the support.\n\n%s') % line)
        return ''.join(lines)

    def _sender_data_record_1(self, options, data):
        return "%03d%-14s%-11s%-1s%-8s%-1s%-1s%-1s%-10s%-946s" % (
            996,                                                                     # 6.1  M
            'IDENTREGISTER1',                                                        # 6.2  M
            int(data['vat']),                                                        # 6.3  M
            RUN_TYPE,                                                                # 6.4  M
            fields.Date.to_date(options['date']['date_to']).strftime('%d%m%Y'),      # 6.5  M
            'P',                                                                     # 6.6  M
            'C',                                                                     # 6.7  M
            'M',                                                                     # 6.8  M
            'FPAIVV02.0',                                                            # 6.9  M
            '',                                                                      # 6.10 S
        )

    def _sender_data_record_2(self, data):
        return "%03d%-14s%-200s%-38s%-15s%-15s%-16s%-695s" % (
            996,                                                                     # 6.1  M
            'IDENTREGISTER2',                                                        # 6.11 M
            data['name'],                                                            # 6.12 M
            data['commercial_partner_name'],                                         # 6.13 M
            data['phone'] or '',                                                     # 6.14 M
            '',                                                                      # 6.15 O
            '',                                                                      # 6.16 O
            '',                                                                      # 6.10 S
        )

    def _sender_data_record_3(self, data):
        return "%03d%-14s%-38s%-38s%-27s%-3s%-4s%-20s%-38s%-38s%-27s%-3s%-4s%-20s%-76s%-643s" % (
            996,                                                                     # 6.1  M
            'IDENTREGISTER3',                                                        # 6.17 M
            data['street'],                                                          # 6.18 M
            data['street2'] or '',                                                   # 6.18 O
            data['city'],                                                            # 6.19 M
            data['state_code'],                                                      # 6.20 M
            data['zip'],                                                             # 6.21 M
            data['country_name'],                                                    # 6.22 O
            '',                                                                      # 6.23 O
            '',                                                                      # 6.23 O
            '',                                                                      # 6.24 O
            '',                                                                      # 6.25 O
            '0000',                                                                  # 6.26 O
            '',                                                                      # 6.27 O
            data['email'],                                                           # 6.28 O
            '',                                                                      # 6.10 S
        )

    def _payer_identity_data_record(self, options, data):
        return "%03d%-8s%011d%03d%-4s%-200s%-200s%-38s%-38s%-27s%-3s%-4s%-20s%-38s%-15s%-15s%-76s%-293s" % (
            996,                                                                     # 6.1  M
            'IDENTITY',                                                              # 6.29 M
            int(data['vat']),                                                        # 6.30 M
            0,                                                                       # 6.31 C
            fields.Date.to_date(options['date']['date_to']).strftime('%Y'),          # 6.32 M
            data['name'],                                                            # 6.33 M
            data['commercial_partner_name'],                                         # 6.34 O
            data['street'],                                                          # 6.35 M
            data['street2'] or '',                                                   # 6.35 O
            data['city'],                                                            # 6.36 M
            data['state_code'],                                                      # 6.37 M
            data['zip'],                                                             # 6.38 M
            data['country_name'],                                                    # 6.39 O
            data['name'],                                                            # 6.40 O
            data['phone'] or '',                                                     # 6.41 O
            '',                                                                      # 6.42 O
            data['email'],                                                           # 6.43 O
            '',                                                                      # 6.10 S
        )

    def _software_data_record(self):
        return "%03d%-8s%-80s%-905s" % (
            996,                                                                     # 6.1  M
            'SOFTWARE',                                                              # 6.44 M
            'COMMERCIAL Andre William, Odoo %s' % version,                           # 6.45 M
            '',                                                                      # 6.10 S
        )

    def _payee_data_record(self, data):
        self._validate_partner(data, without_abn=bool(data['tax_withheld']))
        return "%03d%-6s%011d%-30s%-15s%-15s%-200s%-200s%-38s%-38s%-27s%-3s%-4s%-20s%-15s%-6s%-9s%011d%011d%011d%-1s%08d%-200s%-76s%-1s%-1s%-36s" % (
            996,                                                                     # 6.1  M
            'DPAIVS',                                                                # 6.46 M
            int(data['vat']),                                                        # 6.47 M
            '',                                                                      # 6.48 C
            '',                                                                      # 6.49 C
            '',                                                                      # 6.50 O
            data['name'],                                                            # 6.51 M
            '',                                                                      # 6.52 O
            data['street'],                                                          # 6.53 M
            data['street2'] or '',                                                   # 6.53 O
            data['city'],                                                            # 6.54 M
            data['state_code'],                                                      # 6.55 M
            data['zip'],                                                             # 6.56 M
            data['country_name'],                                                    # 6.57 O
            data['phone'] or '',                                                     # 6.58 O
            ''.zfill(6),                                                             # 6.59 O
            ''.zfill(9),                                                             # 6.60 O
            data['gross_paid'],                                                      # 6.61 M
            data['tax_withheld'],                                                   # 6.62 M
            data['total_gst'],                                                       # 6.63 M
            'P',                                                                     # 6.64 M  # TODO G for Grant, P for payment
            0,                                                                       # 6.65 C
            '',                                                                      # 6.66 C
            data['email'],                                                           # 6.67 O
            'Y',                                                                     # 6.68 M  # TODO Y or N depending if "a Statement by a supplier has been provided"
            'O',                                                                     # 6.69 M
            '',                                                                      # 6.10 S
        )

    def _file_total_data_record(self, n):
        return "%03d%-10s%08d%-975s" % (
            996,                                                                     # 6.1  M
            'FILE-TOTAL',                                                            # 6.44 M
            n,                                                                       # 6.45 M
            '',                                                                      # 6.10 S
        )

    def _validate_partner(self, data, without_abn=False):
        errors = []
        if not data['street']:
            errors += [_('The street is not set')]
        if len(data['street'] or '') > 38 or len(data['street2'] or '') > 38:
            errors += [_('Maxmimum street length is 38')]
        if not data['city']:
            errors += [_('The city is not set')]
        if not data['zip']:
            errors += [_('The postcode is not set')]
        if data['zip'] and (not (0 <= int(data['zip']) <= 9999) or (len(data['zip']) != 4)):
            errors += [_('The postcode is not valid')]
        if not data['state_name']:
            errors += [_('The state is not set')]
        if data['state_code'] not in VALID_STATES:
            errors += [_('The state is not valid')]
        if data['state_code'] == 'OTH' and data['zip'] != '9999':
            errors += [_('The postalcode must be 9999 because it is in overseas addresses')]
        if len(data.get('phone') or '') > 15:
            errors += [_('The phone number is not valid (max 15 char)')]

        data['vat'] = (data['vat'] or '0').replace(' ', '')
        if not without_abn:
            errors += self._validate_abn(data['vat'])

        if errors:
            raise UserError('\n'.join(errors + ['', _('While processing %s') % data['name']]))

        data['email'] = data['email'] or ''

    def _validate_abn(self, abn):
        if not abn:
            return [_('The Australian Business Number is not set')]
        try:
            int(abn.replace(' ', ''))  # quick check independant from stdnum
            if is_valid_abn and not is_valid_abn(abn):
                raise ValueError()
        except ValueError:
            return [_('The Australian Business Number is not valid')]
        return []

    def open_invoices(self, options, params=None):
        active_id = int(params.get('id'))
        partner = self.env['res.partner'].browse(active_id)
        tags = self.env.ref('l10n_au.service_tag') + self.env.ref('l10n_au.tax_withheld_tag')
        return {
            'name': _('TPAR invoices of %s') % partner.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('commercial_partner_id', '=', partner.id), ('line_ids.tax_tag_ids', 'in', tags.ids)],
        }
