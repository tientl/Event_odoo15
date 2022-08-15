from odoo import models

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'account.avatax']

    def _action_confirm(self):
        self.button_update_avatax()
        return super()._action_confirm()

    def action_quotation_send(self):
        self.button_update_avatax()
        return super().action_quotation_send()

    def button_update_avatax(self):
        mapped_taxes, _ = self.filtered(lambda m: m.fiscal_position_id.is_avatax)._map_avatax(False)
        to_flush = self.env['sale.order.line']
        for line, detail in mapped_taxes.items():
            line.tax_id = detail['tax_ids']
            to_flush += line

        # Trigger field computation due to changing the tax id. Do
        # this here because we will manually change the taxes.
        to_flush.flush(['price_tax', 'price_subtotal', 'price_total'])

        for line, detail in mapped_taxes.items():
            line.price_tax = detail['tax_amount']
            line.price_subtotal = detail['total']
            line.price_total = detail['tax_amount'] + detail['total']

    def _get_avatax_invoice_lines(self):
        return [
            self._get_avatax_invoice_line(
                product=line.product_id,
                price_subtotal=line.price_subtotal,
                quantity=line.product_uom_qty,
                line_id='%s,%s' % (line._name, line.id),
            )
            for line in self.order_line.filtered(lambda l: not l.display_type)
        ]

    def _get_avatax_dates(self):
        return (self.date_order, self.date_order)

    def _get_avatax_document_type(self):
        return 'SalesOrder'

    def _get_avatax_description(self):
        return 'Sales Order'


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_tax_id(self):
        super(SaleOrderLine, self.filtered(lambda l: not l.order_id.fiscal_position_id.is_avatax))._compute_tax_id()
