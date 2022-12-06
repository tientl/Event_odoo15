
from odoo import api, models


class EventTemplateTicket(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, vals):
        picture_public = {'public': True}
        vals.update(picture_public)
        return super().create(vals)
