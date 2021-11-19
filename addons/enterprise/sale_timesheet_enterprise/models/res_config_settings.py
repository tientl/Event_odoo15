# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

from odoo.addons.sale_timesheet_enterprise.models.sale import DEFAULT_INVOICED_TIMESHEET


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "All recorded timesheets"),
        ('approved', "Approved timesheets only"),
    ], default=DEFAULT_INVOICED_TIMESHEET, string="Timesheets Invoicing", config_parameter='sale.invoiced_timesheet')

    def set_values(self):
        """ Override set_values to recompute the qty_delivered for each sale.order.line
            where :
                -   the sale.order has the state to 'sale',
                -   the type of the product is a 'service',
                -   the service_policy in product has 'delivered_timesheet'.

            We need to recompute this field because when the invoiced_timesheet
            config changes, this field isn't recompute.
            When the qty_delivered field is recomputed, we need to update the
            qty_to_invoice and invoice status fields.
        """
        old_value = self.env["ir.config_parameter"].sudo().get_param("sale.invoiced_timesheet")
        if old_value and self.invoiced_timesheet != old_value:
            # recompute the qty_delivered in sale.order.line for sale.order
            # where his state is set to 'sale'.
            sale_orders = self.env['sale.order'].search([
                ('state', 'in', ['sale', 'done'])
            ])

            for so in sale_orders:
                sale_order_lines = so.order_line.filtered(
                    lambda sol: sol.invoice_status in ['no', 'to invoice'] and sol.product_id.type == 'service' and sol.product_id.service_type == 'timesheet'
                )

                if sale_order_lines:
                    # Too much write 3 * (n records)
                    # We could simplify and merge the 3 methods to have
                    # max 1 * (n records) writings in database.
                    sale_order_lines._compute_qty_delivered()
                    sale_order_lines._get_to_invoice_qty()
                    sale_order_lines._compute_invoice_status()
        return super(ResConfigSettings, self).set_values()
