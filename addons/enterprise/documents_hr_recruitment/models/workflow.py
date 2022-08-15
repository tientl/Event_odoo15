# -*- coding: utf-8 -*-
from odoo import fields, models


class WorkflowActionRuleApplicant(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('hr.applicant', "Applicant")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleApplicant, self).create_record(documents=documents)
        if self.create_model == 'hr.applicant':
            new_obj = self.env[self.create_model].create({'name': "New Application from Documents", 'user_id': False})
            for document in documents:
                this_document = document
                if (document.res_model or document.res_id) and document.res_model != 'documents.document':
                    this_document = document.copy()
                    attachment_id_copy = document.attachment_id.with_context(no_document=True).copy()
                    this_document.write({'attachment_id': attachment_id_copy.id})

                this_document.attachment_id.with_context(no_document=True).write({
                    'res_model': self.create_model,
                    'res_id': new_obj.id
                })
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.create_model,
                'res_id': new_obj.id,
                'name': "new %s from %s" % (self.create_model, new_obj.name),
                'view_mode': 'form',
                'views': [(False, "form")],
                'context': self._context,
            }
        return rv
