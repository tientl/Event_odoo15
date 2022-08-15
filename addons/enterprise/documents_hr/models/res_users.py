# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    document_ids = fields.One2many('documents.document', 'owner_id')
    document_count = fields.Integer('Documents', compute='_compute_document_count')

    @api.depends('document_ids')
    def _compute_document_count(self):
        for user in self:
            user.document_count = len(user.document_ids)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['document_count']

