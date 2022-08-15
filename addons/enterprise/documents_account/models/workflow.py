# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from odoo.tests.common import Form


class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('account.move.in_invoice', "Vendor bill"),
                                                   ('account.move.out_invoice', 'Customer invoice'),
                                                   ('account.move.in_refund', 'Vendor Credit Note'),
                                                   ('account.move.out_refund', "Credit note")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleAccount, self).create_record(documents=documents)
        if self.create_model.startswith('account.move'):
            invoice_type = self.create_model.split('.')[2]
            journal = self.env['account.move'].with_context(default_move_type=invoice_type)._get_default_journal()
            new_obj = None
            invoice_ids = []
            for document in documents:
                create_values = {
                    'default_move_type': invoice_type,
                    'default_journal_id': journal.id,
                }
                if document.res_model == 'account.move.line' and document.res_id:
                    create_values.update(default_document_request_line_id=document.res_id)

                if self.partner_id:
                    if invoice_type in ['in_invoice', 'in_refund']:
                        payment_term_id = self.partner_id.property_supplier_payment_term_id.id
                    elif invoice_type in ['out_invoice', 'out_refund']:
                        payment_term_id = self.partner_id.property_payment_term_id.id
                    create_values.update(
                        default_partner_id=self.partner_id.id,
                        default_invoice_payment_term_id=payment_term_id
                    )
                elif document.partner_id:
                    if invoice_type in ['in_invoice', 'in_refund']:
                        payment_term_id = document.partner_id.property_supplier_payment_term_id.id
                    elif invoice_type in ['out_invoice', 'out_refund']:
                        payment_term_id = document.partner_id.property_payment_term_id.id
                    create_values.update(
                        default_partner_id=document.partner_id.id,
                        default_invoice_payment_term_id=payment_term_id
                    )

                if document.res_model == 'account.move' and document.res_id:
                    invoice_ids.append(document.res_id)
                else:
                    with Form(self.env['account.move'].with_context(create_values)) as invoice_form:
                        # ignore view required fields (it will fail on create for really required field)
                        for modifiers in invoice_form._view['modifiers'].values():
                            modifiers.pop("required", None)
                        new_obj = invoice_form.save()

                    body = "<p>created from Documents app</p>"
                    # the 'no_document' key in the context indicates that this ir_attachment has already a
                    # documents.document and a new document shouldn't be automatically generated.
                    # message_post ignores attachment that are not on mail.compose message, so we link the attachment explicitly afterwards
                    new_obj.with_context(default_journal_id=journal.id, default_move_type=invoice_type).message_post(body=body)
                    document.attachment_id.with_context(no_document=True).write({
                        'res_model': 'account.move',
                        'res_id': new_obj.id,
                    })
                    document.attachment_id.register_as_main_attachment()  # needs to be called explicitly since we bypassed the standard attachment creation mechanism
                    invoice_ids.append(new_obj.id)

            context = dict(self._context, default_move_type=invoice_type, default_journal_id=journal.id)
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'name': "Invoices",
                'view_id': False,
                'view_mode': 'tree',
                'views': [(False, "list"), (False, "form")],
                'domain': [('id', 'in', invoice_ids)],
                'context': context,
            }
            if len(invoice_ids) == 1:
                record = new_obj or self.env['account.move'].browse(invoice_ids[0])
                view_id = record.get_formview_id() if record else False
                action.update({
                    'view_mode': 'form',
                    'views': [(view_id, "form")],
                    'res_id': invoice_ids[0],
                    'view_id': view_id,
                })
            return action
        return rv
