# coding: utf-8

from odoo import fields, models, api
from odoo.osv import expression


class L10nMXEdiTariffFraction(models.Model):
    _name = 'l10n_mx_edi.tariff.fraction'
    _description = "Mexican EDI Tariff Fraction"

    code = fields.Char(
        help="Code defined in the SAT to this record.")
    name = fields.Char(
        help="Name defined in the SAT catalog to this record.")
    uom_code = fields.Char(
        help="UoM code related with this tariff fraction. This value is defined in the SAT catalog and will be "
             "assigned in the attribute 'UnidadAduana' in the merchandise.")
    active = fields.Boolean(
        help="If the tariff fraction has expired it could be disabled to do not allow select the record.", default=True)

    def name_get(self):
        # OVERRIDE
        return [(tariff.id, "%s %s" % (tariff.code, tariff.name or '')) for tariff in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # OVERRIDE
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
