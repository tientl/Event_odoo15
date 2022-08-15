# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):
    _inherit = 'account.move'

    intrastat_transport_mode_id = fields.Many2one('account.intrastat.code', string='Intrastat Transport Mode',
        readonly=True, states={'draft': [('readonly', False)]}, domain="[('type', '=', 'transport')]")
    intrastat_country_id = fields.Many2one('res.country',
        string='Intrastat Country',
        help='Intrastat country, arrival for sales, dispatch for purchases',
        compute='_compute_intrastat_country_id',
        readonly=False,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
        store=True,
        domain=[('intrastat', '=', True)])

    def _get_invoice_intrastat_country_id(self):
        ''' Hook allowing to retrieve the intrastat country depending of installed modules.
        :return: A res.country record's id.
        '''
        self.ensure_one()
        return self.partner_id.country_id.id

    @api.depends('partner_id')
    def _compute_intrastat_country_id(self):
        for move in self:
            if move.partner_id.country_id.intrastat:
                move.intrastat_country_id = move._get_invoice_intrastat_country_id()
            else:
                move.intrastat_country_id = False

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "intrastat_product_origin_country_id"):
            create_column(self.env.cr, "account_move_line", "intrastat_product_origin_country_id", "int4")
        return super()._auto_init()

    intrastat_transaction_id = fields.Many2one('account.intrastat.code', string='Intrastat', domain="[('type', '=', 'transaction')]")
    intrastat_product_origin_country_id = fields.Many2one('res.country', string='Product Country', compute='_compute_origin_country', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_origin_country(self):
        for line in self:
            line.intrastat_product_origin_country_id = line.product_id.product_tmpl_id.intrastat_origin_country_id
