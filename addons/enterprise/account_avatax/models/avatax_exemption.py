from odoo import models, fields, api
from odoo.osv import expression


class AvataxExemption(models.Model):
    _name = 'avatax.exemption'
    _description = "Avatax Partner Exemption Codes"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Char()
    valid_country_ids = fields.Many2many('res.country')
    company_id = fields.Many2one('res.company', required=True)

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
        return self._name_search_fields(name, ['name', 'code'], args, operator, limit, name_get_uid)

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '[%s] %s' % (record.code, record.name)))
        return res
