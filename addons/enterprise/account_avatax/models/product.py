# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression


class ProductAvataxCategory(models.Model):
    _name = 'product.avatax.category'
    _description = "Avatax Product Category"
    _rec_name = 'code'

    code = fields.Char(required=True)
    description = fields.Char(required=True)

    def _name_search_fields(self, name, fields, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Helper for the `_name_search` to search the name in multiple fields

        :param name (str): see `name_search`
        :param fields (list<str>): the names of the fields that can contain the name
                                   searched for. Could be relational fields.
        :param args (list): see `name_search`
        :param operator (str): see `name_search`
        :param limit (int): see `name_search`
        :param access_rights_uid (int): see `_name_search`
        :return (list<int>): the ids of records matching the name search
        """
        aggregator = expression.AND if operator in expression.NEGATIVE_TERM_OPERATORS else expression.OR
        domain = aggregator([[(field_name, operator, name)] for field_name in fields])
        return self._search(
            expression.AND([domain, args]),
            limit=limit,
            access_rights_uid=name_get_uid,
        )

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        return self._name_search_fields(name, ['description', 'code'], args, operator, limit, name_get_uid)

    def name_get(self):
        res = []
        for category in self:
            res.append((category.id, _('[%s] %s') % (category.code, category.description[0:50])))
        return res


class ProductCategory(models.Model):
    _inherit = 'product.category'

    avatax_category_id = fields.Many2one(
        'product.avatax.category',
        help="https://taxcode.avatax.avalara.com/",
    )

    def _get_avatax_category_id(self):
        categ = self
        while categ and not categ.avatax_category_id:
            categ = categ.parent_id
        return categ.avatax_category_id


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    avatax_category_id = fields.Many2one(
        'product.avatax.category',
        help="https://taxcode.avatax.avalara.com/",
    )

    def _get_avatax_category_id(self):
        return self.avatax_category_id or self.categ_id._get_avatax_category_id()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    avatax_category_id = fields.Many2one(
        'product.avatax.category',
        help="https://taxcode.avatax.avalara.com/",
    )

    def _get_avatax_category_id(self):
        return self.avatax_category_id or self.product_tmpl_id._get_avatax_category_id()
