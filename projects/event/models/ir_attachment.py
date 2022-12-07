
from odoo import api, models


class EventTemplateTicket(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, vals):
        access_token = {'access_token': self._generate_access_token()}
        vals.update(access_token)
        return super().create(vals)
