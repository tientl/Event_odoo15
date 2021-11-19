# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta


class IntrastatReport(models.AbstractModel):
    _inherit = 'account.intrastat.report'

    def _get_reports_buttons(self, options):
        res = super(IntrastatReport, self)._get_reports_buttons(options)
        if self._get_report_country_code(options) == "BE":
            res += [{'name': _('XML'), 'sequence': 3, 'action': 'print_xml', 'file_export_type': _('XML')}]
        return res

    @api.model
    def get_xml(self, options):
        ''' Create the xml export.

        :param options: The report options.
        :return: The xml export file content.
        '''
        date_from, date_to, journal_ids, incl_arrivals, incl_dispatches, extended, with_vat = self._decode_options(options)
        date_1 = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
        date_2 = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
        a_day = timedelta(days=1)
        if date_1.day != 1 or (date_2 - date_1) > timedelta(days=30) or date_1.month == (date_2 + a_day).month:
            raise UserError(_('Wrong date range selected. The intrastat declaration export has to be done monthly.'))
        date = date_1.strftime('%Y-%m')

        company = self.env.company
        if not company.company_registry:
            error_msg = _('Missing company registry information on the company')
            action_error = {
                'name': _('company %s', company.name),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'res.company',
                'views': [[False, 'form']],
                'target': 'new',
                'res_id': company.id,
            }
            raise RedirectWarning(error_msg, action_error, _('Add company registry'))

        # create in_vals corresponding to invoices with cash-in
        in_vals = []
        if incl_arrivals:
            query, params = self._prepare_query(
                date_from, date_to, journal_ids=journal_ids, invoice_types=('in_invoice', 'out_refund'), with_vat=with_vat)
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()
            in_vals = self._fill_missing_values(query_res)

        # create out_vals corresponding to invoices with cash-out
        out_vals = []
        if incl_dispatches:
            query, params = self._prepare_query(
                date_from, date_to, journal_ids=journal_ids, invoice_types=('out_invoice', 'in_refund'), with_vat=with_vat)
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()
            out_vals = self._fill_missing_values(query_res)

        return self.env.ref('l10n_be_intrastat.intrastat_report_export_xml')._render({
            'company': company,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'extended': extended,
            'date': date,
            '_get_reception_code': self._get_reception_code,
            '_get_reception_form': self._get_reception_form,
            '_get_expedition_code': self._get_expedition_code,
            '_get_expedition_form': self._get_expedition_form,
        })

    def _get_reception_code(self, extended):
        return 'EX19E' if extended else 'EX19S'

    def _get_reception_form(self, extended):
        return 'EXF19E' if extended else 'EXF19S'

    def _get_expedition_code(self, extended):
        return 'INTRASTAT_X_E' if extended else 'INTRASTAT_X_S'

    def _get_expedition_form(self, extended):
        return 'INTRASTAT_X_EF' if extended else 'INTRASTAT_X_SF'
