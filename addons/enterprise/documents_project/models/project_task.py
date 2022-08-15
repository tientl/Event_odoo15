# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'documents.mixin']

    def unlink(self):
        # unlink documents.document directly so mail.activity.mixin().unlink is called
        self.env['documents.document'].sudo().search([('attachment_id', 'in', self.attachment_ids.ids)]).unlink()
        return super(ProjectTask, self).unlink()

    def _get_document_tags(self):
        return self.company_id.project_tags

    def _get_document_folder(self):
        return self.company_id.project_folder

    def _check_create_documents(self):
        return self.company_id.documents_project_settings and super()._check_create_documents()
