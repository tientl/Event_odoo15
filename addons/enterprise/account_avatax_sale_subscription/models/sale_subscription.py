# coding: utf-8
from collections import defaultdict

from odoo import api, fields, models


class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _inherit = ["sale.subscription", "account.avatax"]

    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        compute='_compute_fiscal_position_id',
        inverse='_set_fiscal_position_id',
        help='Technical field required by the account.avatax mixin.'
    )

    @api.depends('company_id', 'partner_id', 'partner_id.property_account_position_id', 'partner_id.country_id', 'partner_id.state_id', 'partner_id.zip')
    def _compute_fiscal_position_id(self):
        """ Sets the fiscal position required for the account.avatax mixin. """
        for sub in self:
            fpos = self.env['account.fiscal.position'].with_company(sub.company_id).get_fiscal_position(sub.partner_id.id)
            sub.fiscal_position_id = fpos

    # This dummy inverse makes the field writeable which is necessary for the _check_address constraint:
    # method sale.subscription._check_address: @constrains parameter 'fiscal_position_id' is not writeable
    def _set_fiscal_position_id(self):
        pass

    def button_update_avatax(self):
        mapped_taxes, _ = self.filtered(lambda sub: sub.fiscal_position_id.is_avatax)._map_avatax(False)

        sub_to_totals = defaultdict(lambda: defaultdict(int))

        for line, detail in mapped_taxes.items():
            totals = sub_to_totals[line.analytic_account_id]
            totals['recurring_total'] += detail['total']
            totals['recurring_tax'] += detail['tax_amount']
            totals['recurring_total_incl'] += detail['tax_amount'] + detail['total']

        for sub, vals in sub_to_totals.items():
            sub.write(vals)

    def _do_payment(self, payment_token, invoice):
        if invoice._send_to_avatax():
            invoice.button_update_avatax()
        return super()._do_payment(payment_token, invoice)

    def _get_avatax_ship_to_partner(self):
        return self.partner_shipping_id or super()._get_avatax_ship_to_partner()

    def _get_avatax_invoice_lines(self):
        return [
            self._get_avatax_invoice_line(
                product=line.product_id,
                price_subtotal=line.price_subtotal,
                quantity=line.quantity,
                line_id='%s,%s' % (line._name, line.id),
            )
            for line in self.recurring_invoice_line_ids
        ]

    def _get_avatax_dates(self):
        today = fields.Date.context_today(self)
        return today, today

    def _get_avatax_document_type(self):
        return 'SalesOrder'

    def _get_avatax_description(self):
        return 'Subscription'

    def _recurring_create_invoice(self, automatic=False, batch_size=20):
        invoices = super()._recurring_create_invoice(automatic, batch_size)
        # Already compute taxes for unvalidated documents as they can already be paid
        invoices.filtered(lambda m: m.state == 'draft').button_update_avatax()
        return invoices
