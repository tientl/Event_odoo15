# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    tag_ids = fields.Many2many('documents.tag')
    folder_id = fields.Many2one('documents.folder',
                                help="By defining a folder, the upload activities will generate a document")
    default_user_id = fields.Many2one('res.users', string="Default User")


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _prepare_next_activity_values(self):
        vals = super()._prepare_next_activity_values()
        current_activity_type = self.activity_type_id
        next_activity_type = current_activity_type.triggered_next_type_id

        if current_activity_type.category == 'upload_file' and self.res_model == 'documents.document' and next_activity_type.category == 'upload_file':
            existing_document = self.env['documents.document'].search([('request_activity_id', '=', self.id)], limit=1)
            if 'summary' not in vals:
                vals['summary'] = self.summary or _('Upload file request')
            new_doc_request = self.env['documents.document'].create({
                'owner_id': next_activity_type.default_user_id.id,
                'folder_id': next_activity_type.folder_id.id if next_activity_type.folder_id else existing_document.folder_id.id,
                'tag_ids': [(6, 0, next_activity_type.tag_ids.ids)],
                'name': vals['summary'],
            })
            vals['res_id'] = new_doc_request.id
        return vals

    def _action_done(self, feedback=False, attachment_ids=None):
        if attachment_ids:
            for record in self:
                document = self.env['documents.document'].search([('request_activity_id', '=', record.id)], limit=1)
                if document and not document.attachment_id:
                    self.env['documents.document'].search([('attachment_id', '=', attachment_ids[0])]).unlink()
                    if not feedback:
                        feedback = _("Document Request: %s Uploaded by: %s") % (document.name, self.env.user.name)
                    document.write({'attachment_id': attachment_ids[0], 'request_activity_id': False})

        return super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        doc_vals = []
        for activity in activities:
            activity_type = activity.activity_type_id
            if activity_type.category == 'upload_file' and activity.res_model != 'documents.document' and activity_type.folder_id:
                doc_vals.append({
                    'res_model': activity.res_model,
                    'res_id': activity.res_id,
                    'owner_id': activity_type.default_user_id.id,
                    'folder_id': activity_type.folder_id.id,
                    'tag_ids': [(6, 0, activity_type.tag_ids.ids)],
                    'name': activity.summary or activity.res_name or 'upload file request',
                    'request_activity_id': activity.id,
                })
            elif activity_type.category == 'upload_file' and activity.res_model == 'documents.document':
                existing_doc_req = self.env['documents.document'].browse(activity.res_id)
                if not existing_doc_req.request_activity_id:
                    existing_doc_req.write({'request_activity_id': activity.id})

        if doc_vals:
            self.env['documents.document'].create(doc_vals)
        return activities
