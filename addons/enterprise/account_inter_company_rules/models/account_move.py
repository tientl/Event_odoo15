# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    auto_generated = fields.Boolean(string='Auto Generated Document', copy=False, default=False)
    auto_invoice_id = fields.Many2one('account.move', string='Source Invoice', readonly=True, copy=False)

    def _post(self, soft=True):
        # OVERRIDE to generate cross invoice based on company rules.
        invoices_map = {}
        posted = super()._post(soft)
        for invoice in posted.filtered(lambda move: move.is_invoice()):
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if company and company.rule_type == 'invoice_and_refund' and not invoice.auto_generated:
                invoices_map.setdefault(company, self.env['account.move'])
                invoices_map[company] += invoice
        for company, invoices in invoices_map.items():
            context = dict(self.env.context, default_company_id=company.id)
            context.pop('default_journal_id', None)
            invoices.with_user(company.intercompany_user_id).with_context(context).with_company(company)._inter_company_create_invoices()
        return posted

    def _inter_company_create_invoices(self):
        ''' Create cross company invoices.
        :return:        The newly created invoices.
        '''

        # Prepare invoice values.
        invoices_vals_per_type = {}
        inverse_types = {
            'in_invoice': 'out_invoice',
            'in_refund': 'out_refund',
            'out_invoice': 'in_invoice',
            'out_refund': 'in_refund',
        }
        for inv in self:
            invoice_vals = inv._inter_company_prepare_invoice_data(inverse_types[inv.move_type])
            invoice_vals['invoice_line_ids'] = []
            for line in inv.invoice_line_ids:
                invoice_vals['invoice_line_ids'].append((0, 0, line._inter_company_prepare_invoice_line_data()))

            inv_new = inv.with_context(default_move_type=invoice_vals['move_type']).new(invoice_vals)
            for line in inv_new.invoice_line_ids.filtered(lambda l: not l.display_type):
                # We need to adapt the taxes following the fiscal position, but we must keep the
                # price unit.
                price_unit = line.price_unit
                line.tax_ids = line._get_computed_taxes()
                line._set_price_and_tax_after_fpos()
                line.price_unit = price_unit

            invoice_vals = inv_new._convert_to_write(inv_new._cache)
            invoice_vals.pop('line_ids', None)
            invoice_vals['origin_invoice'] = inv

            invoices_vals_per_type.setdefault(invoice_vals['move_type'], [])
            invoices_vals_per_type[invoice_vals['move_type']].append(invoice_vals)

        # Create invoices.
        moves = self.env['account.move']
        for invoice_type, invoices_vals in invoices_vals_per_type.items():
            for invoice in invoices_vals:
                origin_invoice = invoice['origin_invoice']
                invoice.pop('origin_invoice')
                msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=origin_invoice.name, company=origin_invoice.company_id.name)
                am = self.with_context(default_type=invoice_type).create(invoice)
                am.message_post(body=msg)
                moves += am
        return moves

    def _inter_company_prepare_invoice_data(self, invoice_type):
        ''' Get values to create the invoice.
        /!\ Doesn't care about lines, see '_inter_company_prepare_invoice_line_data'.
        :return: Python dictionary of values.
        '''
        self.ensure_one()
        # We need the fiscal position in the company (already in context) we are creating the
        # invoice, not the fiscal position of the current invoice (self.company)
        delivery_partner_id = self.company_id.partner_id.address_get(['delivery'])['delivery']
        fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(
            self.company_id.partner_id.id, delivery_id=delivery_partner_id
        )
        return {
            'move_type': invoice_type,
            'ref': self.ref,
            'partner_id': self.company_id.partner_id.id,
            'currency_id': self.currency_id.id,
            'auto_generated': True,
            'auto_invoice_id': self.id,
            'invoice_date': self.invoice_date,
            'payment_reference': self.payment_reference,
            'invoice_origin': _('%s Invoice: %s') % (self.company_id.name, self.name),
            'fiscal_position_id': fiscal_position_id,
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _inter_company_prepare_invoice_line_data(self):
        ''' Get values to create the invoice line.
        :return: Python dictionary of values.
        '''
        self.ensure_one()

        vals = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'quantity': self.quantity,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'analytic_account_id': not self.analytic_account_id.company_id and self.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.filtered(lambda r: not r.company_id).ids)],
        }
        # Ensure no account will be set at creation
        if self.display_type:
            vals['account_id'] = False

        # Set company of analytic account to false to avoid inconsistencies in company record rules
        company = self.env['res.company']._find_company_from_partner(self.move_id.partner_id.id)
        analytic_company = self.analytic_account_id.company_id
        if company and analytic_company and company.rule_type == 'invoice_and_refund' and company != analytic_company:
            self.analytic_account_id.company_id = False
        return vals
