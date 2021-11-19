# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta
from collections import defaultdict, namedtuple


class AccountMove(models.Model):
    _inherit = 'account.move'

    asset_id = fields.Many2one('account.asset', string='Asset', index=True, ondelete='cascade', copy=False, domain="[('company_id', '=', company_id)]")
    asset_asset_type = fields.Selection(related='asset_id.asset_type')
    asset_remaining_value = fields.Monetary(string='Depreciable Value', copy=False)
    asset_depreciated_value = fields.Monetary(string='Cumulative Depreciation', copy=False)
    asset_manually_modified = fields.Boolean(help='This is a technical field stating that a depreciation line has been manually modified. It is used to recompute the depreciation table of an asset/deferred revenue.', copy=False)
    asset_value_change = fields.Boolean(help='This is a technical field set to true when this move is the result of the changing of value of an asset')

    asset_ids = fields.One2many('account.asset', string='Assets', compute="_compute_asset_ids")
    asset_ids_display_name = fields.Char(compute="_compute_asset_ids")  # just a button label. That's to avoid a plethora of different buttons defined in xml
    asset_id_display_name = fields.Char(compute="_compute_asset_ids")   # just a button label. That's to avoid a plethora of different buttons defined in xml
    number_asset_ids = fields.Integer(compute="_compute_asset_ids")
    draft_asset_ids = fields.Boolean(compute="_compute_asset_ids")

    # reversed_entry_id is set on the reversal move but there is no way of knowing is a move has been reversed without this
    reversal_move_id = fields.One2many('account.move', 'reversed_entry_id')

    @api.onchange('amount_total')
    def _onchange_amount(self):
        self.asset_manually_modified = True

    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft)

        # log the post of a depreciation
        posted._log_depreciation_asset()

        # look for any asset to create, in case we just posted a bill on an account
        # configured to automatically create assets
        posted._auto_create_asset()
        # check if we are reversing a move and delete assets of original move if it's the case
        posted._delete_reversed_entry_assets()
        return posted

    def _reverse_moves(self, default_values_list=None, cancel=False):
        for move in self:
            # Report the value of this move to the next draft move or create a new one
            if move.asset_id:
                # Recompute the status of the asset for all depreciations posted after the reversed entry
                for later_posted in move.asset_id.depreciation_move_ids.filtered(lambda m: m.date >= move.date and m.state == 'posted'):
                    later_posted.asset_depreciated_value -= move.amount_total
                    later_posted.asset_remaining_value += move.amount_total
                first_draft = min(move.asset_id.depreciation_move_ids.filtered(lambda m: m.state == 'draft'), key=lambda m: m.date, default=None)
                if first_draft:
                    # If there is a draft, simply move/add the depreciation amount here
                    # The depreciated and remaining values don't need to change
                    first_draft.amount_total += move.amount_total
                else:
                    # If there was no draft move left, create one
                    last_date = max(move.asset_id.depreciation_move_ids.mapped('date'))
                    method_period = move.asset_id.method_period

                    self.create(self._prepare_move_for_asset_depreciation({
                        'asset_id': move.asset_id,
                        'move_ref': _('Report of reversal for {name}').format(name=move.asset_id.name),
                        'amount': move.amount_total,
                        'date': last_date + (relativedelta(months=1) if method_period == "1" else relativedelta(years=1)),
                        'asset_depreciated_value': move.amount_total + max(move.asset_id.depreciation_move_ids.mapped('asset_depreciated_value')),
                        'asset_remaining_value': 0,
                    }))

                msg = _('Depreciation entry %s reversed (%s)') % (move.name, formatLang(self.env, move.amount_total, currency_obj=move.company_id.currency_id))
                move.asset_id.message_post(body=msg)

        return super(AccountMove, self)._reverse_moves(default_values_list, cancel)

    def button_cancel(self):
        # OVERRIDE
        res = super(AccountMove, self).button_cancel()
        self.env['account.asset'].sudo().search([('original_move_line_ids.move_id', 'in', self.ids)]).write({'active': False})
        return res

    def button_draft(self):
        for move in self:
            if any(asset_id.state != 'draft' for asset_id in move.asset_ids):
                raise UserError(_('You cannot reset to draft an entry having a posted deferred revenue/expense'))
        return super(AccountMove, self).button_draft()

    def _log_depreciation_asset(self):
        for move in self.filtered(lambda m: m.asset_id):
            asset = move.asset_id
            msg = _('Depreciation entry %s posted (%s)') % (move.name, formatLang(self.env, move.amount_total, currency_obj=move.company_id.currency_id))
            asset.message_post(body=msg)

    def _auto_create_asset(self):
        create_list = []
        invoice_list = []
        auto_validate = []
        for move in self:
            if not move.is_invoice():
                continue

            for move_line in move.line_ids.filtered(lambda line: not (move.move_type in ('out_invoice', 'out_refund') and line.account_id.user_type_id.internal_group == 'asset')):
                if (
                    move_line.account_id
                    and (move_line.account_id.can_create_asset)
                    and move_line.account_id.create_asset != "no"
                    and not move.reversed_entry_id
                    and not (move_line.currency_id or move.currency_id).is_zero(move_line.price_total)
                    and not move_line.asset_ids
                    and move_line.price_total > 0
                ):
                    if not move_line.name:
                        raise UserError(_('Journal Items of {account} should have a label in order to generate an asset').format(account=move_line.account_id.display_name))
                    if move_line.account_id.multiple_assets_per_line:
                        # decimal quantities are not supported, quantities are rounded to the lower int
                        units_quantity = max(1, int(move_line.quantity))
                    else:
                        units_quantity = 1
                    vals = {
                        'name': move_line.name,
                        'company_id': move_line.company_id.id,
                        'currency_id': move_line.company_currency_id.id,
                        'account_analytic_id': move_line.analytic_account_id.id,
                        'analytic_tag_ids': [(6, False, move_line.analytic_tag_ids.ids)],
                        'original_move_line_ids': [(6, False, move_line.ids)],
                        'state': 'draft',
                    }
                    model_id = move_line.account_id.asset_model
                    if model_id:
                        vals.update({
                            'model_id': model_id.id,
                        })
                    auto_validate.extend([move_line.account_id.create_asset == 'validate'] * units_quantity)
                    invoice_list.extend([move] * units_quantity)
                    create_list.extend([vals] * units_quantity)

        assets = self.env['account.asset'].create(create_list)
        for asset, vals, invoice, validate in zip(assets, create_list, invoice_list, auto_validate):
            if 'model_id' in vals:
                asset._onchange_model_id()
                if validate:
                    asset.validate()
            if invoice:
                asset_name = {
                    'purchase': _('Asset'),
                    'sale': _('Deferred revenue'),
                    'expense': _('Deferred expense'),
                }[asset.asset_type]
                msg = _('%s created from invoice') % (asset_name)
                msg += ': <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>' % (invoice.id, invoice.name)
                asset.message_post(body=msg)
        return assets

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        missing_fields = set(['asset_id', 'move_ref', 'amount', 'asset_remaining_value', 'asset_depreciated_value']) - set(vals)
        if missing_fields:
            raise UserError(_('Some fields are missing {}').format(', '.join(missing_fields)))
        asset = vals['asset_id']
        account_analytic_id = asset.account_analytic_id
        analytic_tag_ids = asset.analytic_tag_ids
        depreciation_date = vals.get('date', fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount_currency = vals['amount']
        amount = current_currency._convert(amount_currency, company_currency, asset.company_id, depreciation_date)
        # Keep the partner on the original invoice if there is only one
        partner = asset.original_move_line_ids.mapped('partner_id')
        partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
        if asset.original_move_line_ids and asset.original_move_line_ids[0].move_id.move_type in ['in_refund', 'out_refund']:
            amount = -amount
            amount_currency = -amount_currency
        move_line_1 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_id.id,
            'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
            'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
            'currency_id': current_currency.id,
            'amount_currency': -amount_currency,
        }
        move_line_2 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_expense_id.id,
            'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_account_id': account_analytic_id.id if asset.asset_type in ('purchase', 'expense') else False,
            'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in ('purchase', 'expense') else False,
            'currency_id': current_currency.id,
            'amount_currency': amount_currency,
        }
        move_vals = {
            'ref': vals['move_ref'],
            'partner_id': partner.id,
            'date': depreciation_date,
            'journal_id': asset.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            'asset_id': asset.id,
            'asset_remaining_value': vals['asset_remaining_value'],
            'asset_depreciated_value': vals['asset_depreciated_value'],
            'amount_total': amount,
            'name': '/',
            'asset_value_change': vals.get('asset_value_change', False),
            'move_type': 'entry',
            'currency_id': current_currency.id,
        }
        return move_vals

    def _get_depreciation(self):
        asset = self.asset_id
        if asset:
            account = asset.account_depreciation_expense_id if asset.asset_type == 'sale' else asset.account_depreciation_id
            field = 'debit' if asset.asset_type == 'sale' else 'credit'
            asset_depreciation = sum(
                self.line_ids.filtered(lambda l: l.account_id == account).mapped(field)
            )
            # Special case of closing entry
            if any(
                (line.account_id, line[field]) == (asset.account_asset_id, asset.original_value)
                for line in self.line_ids
            ):
                rfield = 'debit' if asset.asset_type != 'sale' else 'credit'
                asset_depreciation = (
                    asset.original_value
                    - asset.salvage_value
                    - sum(
                        self.line_ids.filtered(lambda l: l.account_id == account).mapped(rfield)
                    )
                )
        else:
            asset_depreciation = 0
        return asset_depreciation

    @api.depends('line_ids.asset_ids')
    def _compute_asset_ids(self):
        for record in self:
            record.asset_ids = record.mapped('line_ids.asset_ids')
            record.number_asset_ids = len(record.asset_ids)
            if record.number_asset_ids:
                asset_type = {
                    'sale': _('Deferred Revenue(s)'),
                    'purchase': _('Asset(s)'),
                    'expense': _('Deferred Expense(s)')
                }
                record.asset_ids_display_name = '%s %s' % (len(record.asset_ids), asset_type.get(record.asset_ids[0].asset_type))
            else:
                record.asset_ids_display_name = ''
            record.asset_id_display_name = {'sale': _('Revenue'), 'purchase': _('Asset'), 'expense': _('Expense')}.get(record.asset_id.asset_type)
            record.draft_asset_ids = bool(record.asset_ids.filtered(lambda x: x.state == "draft"))

    @api.model
    def create_asset_move(self, vals):
        move_vals = self._prepare_move_for_asset_depreciation(vals)
        return self.env['account.move'].create(move_vals)

    def open_asset_view(self):
        ret = {
            'name': _('Asset'),
            'view_mode': 'form',
            'res_model': 'account.asset',
            'view_id': [v[0] for v in self.env['account.asset']._get_views(self.asset_asset_type) if v[1] == 'form'][0],
            'type': 'ir.actions.act_window',
            'res_id': self.asset_id.id,
            'context': dict(self._context, create=False),
        }
        if self.asset_asset_type == 'sale':
            ret['name'] = _('Deferred Revenue')
        elif self.asset_asset_type == 'expense':
            ret['name'] = _('Deferred Expense')
        return ret

    def action_open_asset_ids(self):
        ret = {
            'name': _('Assets'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.asset',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.asset_ids.ids)],
            'views': self.env['account.asset']._get_views(self.asset_ids[0].asset_type),
        }
        if self.asset_ids[0].asset_type == 'sale':
            ret['name'] = _('Deferred Revenues')
        elif self.asset_ids[0].asset_type == 'expense':
            ret['name'] = _('Deferred Expenses')
        return ret

    def _delete_reversed_entry_assets(self):
        ReverseKey = namedtuple('ReverseKey', ['product_id', 'price_unit', 'quantity'])

        def build_key(line):
            return ReverseKey(**{k: line[k] for k in ReverseKey._fields})

        for move in self.filtered(lambda m: m.reversed_entry_id):
            reversed_products = move.invoice_line_ids.mapped(build_key)
            # handle single asset per line by checking match on product_id, price_unit and quantity
            for line in move.reversed_entry_id.line_ids.filtered(lambda l: (
                l.asset_ids
                and not l.account_id.multiple_assets_per_line
                and build_key(l) in reversed_products
            )):
                try:
                    index = reversed_products.index(build_key(line))
                except ValueError:
                    continue

                for asset in line.asset_ids:
                    if asset.state == 'draft' or all(state == 'draft' for state in asset.depreciation_move_ids.mapped('state')):
                        asset.state = 'draft'
                        asset.unlink()
                del reversed_products[index]

            # handle multiple assets per line by counting the remaining reversed quantities
            rp_count = defaultdict(float)
            for rp in reversed_products:
                rp_count[(rp.product_id.id, rp.price_unit)] += rp.quantity

            for line in move.reversed_entry_id.line_ids.filtered(lambda l: (
                l.asset_ids
                and l.account_id.multiple_assets_per_line
                and rp_count.get((l.product_id.id, l.price_unit))
            )):
                for asset in line.asset_ids:
                    if (
                        rp_count[(line.product_id.id, line.price_unit)] > 0
                        and (asset.state == 'draft' or all(
                            state == 'draft'
                            for state in asset.depreciation_move_ids.mapped('state')
                        ))
                    ):
                        asset.state = 'draft'
                        asset.unlink()
                        rp_count[(line.product_id.id, line.price_unit)] -= 1


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_ids = fields.Many2many('account.asset', 'asset_move_line_rel', 'line_id', 'asset_id', string='Asset Linked', help="Asset created from this Journal Item", copy=False)

    def _turn_as_asset(self, asset_type, view_name, view):
        ctx = self.env.context.copy()
        ctx.update({
            'default_original_move_line_ids': [(6, False, self.env.context['active_ids'])],
            'default_company_id': self.company_id.id,
            'asset_type': asset_type,
        })
        if any(line.move_id.state == 'draft' for line in self):
            raise UserError(_("All the lines should be posted"))
        if any(account != self[0].account_id for account in self.mapped('account_id')):
            raise UserError(_("All the lines should be from the same account"))
        return {
            "name": view_name,
            "type": "ir.actions.act_window",
            "res_model": "account.asset",
            "views": [[view.id, "form"]],
            "target": "current",
            "context": ctx,
        }

    def turn_as_asset(self):
        return self._turn_as_asset('purchase', _("Turn as an asset"), self.env.ref("account_asset.view_account_asset_form"))

    def turn_as_deferred(self):
        balance = sum(aml.debit - aml.credit for aml in self)
        if balance > 0:
            return self._turn_as_asset('expense', _("Turn as a deferred expense"), self.env.ref('account_asset.view_account_asset_expense_form'))
        else:
            return self._turn_as_asset('sale', _("Turn as a deferred revenue"), self.env.ref('account_asset.view_account_asset_revenue_form'))
