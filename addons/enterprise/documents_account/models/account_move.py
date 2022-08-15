# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    document_request_line_id = fields.Many2one('account.move.line', string='Reconciliation Journal Entry Line')

    def _get_request_document_actions(self):
        actions = []
        view_id = self.env.ref('documents.documents_request_form_view').id
        for record in self:
            for line in record.line_ids:
                reconcile_model = line.reconcile_model_id
                if reconcile_model and reconcile_model.activity_type_id:
                    activity = reconcile_model.activity_type_id
                    if activity and activity.category == 'upload_file':
                        actions.append({
                            'type': 'ir.actions.act_window',
                            'res_model': 'documents.request_wizard',
                            'name': _("Request Document for %s", line.name),
                            'view_id': view_id,
                            'views': [(view_id, 'form')],
                            'target': 'new',
                            'view_mode': 'form',
                            'context': {'default_res_model': 'account.move.line',
                                        'default_res_id': line.id,
                                        'default_name': line.name,
                                        'default_activity_type_id': activity.id}
                        })
        return actions

    def _get_domain_matching_suspense_moves(self):
        # OVERRIDE to handle the document requests in the suspense accounts domain.
        domain = super(AccountMove, self)._get_domain_matching_suspense_moves()
        return expression.OR([
            domain,
            [('id', '=', self.document_request_line_id.id)]
        ])

    def write(self, vals):
        main_attachment_id = vals.get('message_main_attachment_id')
        new_documents = [False for move in self]
        journals_changed = [('journal_id' in vals  and move.journal_id.id != vals['journal_id']) for move in self]
        for i, move in enumerate(self):
            if main_attachment_id and not move.env.context.get('no_document') and move.move_type != 'entry':
                previous_attachment_id = move.message_main_attachment_id.id
                document = False
                if previous_attachment_id:
                    document = move.env['documents.document'].sudo().search([('attachment_id', '=', previous_attachment_id)], limit=1)
                if document:
                    document.attachment_id = main_attachment_id
                else:
                    new_documents[i] = True
        res = super().write(vals)
        for new_document, journal_changed, move in zip(new_documents, journals_changed, self):
            if (new_document or journal_changed) and move.message_main_attachment_id:
                move._update_or_create_document(move.message_main_attachment_id.id)
        return res

    def _update_or_create_document(self, attachment_id):
        if self.company_id.documents_account_settings:
            setting = self.env['documents.account.folder.setting'].sudo().search(
                [('journal_id', '=', self.journal_id.id),
                 ('company_id', '=', self.company_id.id)], limit=1)
            if setting:
                values = {
                    'folder_id': setting.folder_id.id,
                    'partner_id': self.partner_id.id,
                    'owner_id': self.create_uid.id,
                    'tag_ids': [(4, tag.id) for tag in setting.tag_ids],
                }
                Documents = self.env['documents.document'].with_context(default_type='empty').sudo()
                doc = Documents.search([('attachment_id', '=', attachment_id)], limit=1)
                if doc:
                    doc.write(values)
                else:
                    # backward compatibility with documents that may be not
                    # registered as attachments yet
                    values.update({'attachment_id': attachment_id})
                    doc.create(values)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    reconciliation_invoice_id = fields.One2many('account.move', 'document_request_line_id')
