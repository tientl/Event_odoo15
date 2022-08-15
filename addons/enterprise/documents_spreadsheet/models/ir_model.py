# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.exceptions import AccessError

ALLOWED_FIELDS = set(["id", "name", "model"])

class IrModel(models.Model):
    _inherit = "ir.model"
    """
        This class allows non-Admin 'Documents' users to read some specific information out of ir.model.
        For functional purpose, a spreadsheet containing a pivot is bound to make calls to ir.model to
        fetch various information such as the *business name* of the model linked to the pivot.

        Furthermore, we use several widgets to apply filters to the data, which will also read out of ir.model
        We use the fields FieldMany2One, FieldMany2ManyTags and the widget web.ModelFieldSelector.

        All these calls are strictly reading the fields *id*,*name*(the business name) and *model* through
        the following methods:
         - name_get,
         - name_search,
         - search_read.

        This overrides the reading access rights on the above-mentioned method as long as:
         - the request comes from a user that can access the documents.document model
         - the request is limited to the fields or ALLOWED_FIELDS
         - the user has access to the model or the ir.model it tries to read
    """

    @api.model
    def _check_documents_access(self):
        # Make sure to reject portal users
        return self.env["documents.document"].check_access_rights("read", raise_exception=False)\
            and self.env.user.has_group('base.group_user')

    @api.model
    def _check_comodel_access(self, models):
        return all(model in self.env
                    and self.env[model].check_access_rights("read", raise_exception=False) for model in models)

    def name_get(self):
        try:
            return super().name_get()
        except AccessError:
            if self._check_documents_access():
                res = self.sudo().name_get()
                if self._check_comodel_access(self.sudo().mapped('model')):
                    return res
            raise

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        try:
            return super()._name_search(name, args, operator, limit)
        except AccessError:
            if self._check_documents_access():
                res = self.sudo()._name_search(name, args, operator, limit, name_get_uid)
                if self._check_comodel_access(self.sudo().browse(res).mapped('model')):
                    return res
            raise

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        try:
            return super().search_read(domain, fields, offset, limit, order)
        except AccessError:
            are_fields_allowed = fields and ALLOWED_FIELDS.issuperset(fields)
            if are_fields_allowed and self._check_documents_access():
                res = self.sudo().search_read(domain, fields, offset, limit, order)
                models = self.sudo().browse([record["id"] for record in res]).mapped('model')
                if self._check_comodel_access(models):
                    return res
            raise
