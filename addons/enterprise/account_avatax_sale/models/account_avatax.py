# -*- coding: utf-8 -*-
from odoo import models


class AccountAvatax(models.AbstractModel):
    _inherit = 'account.avatax'

    def _get_avatax_ship_to_partner(self):
        return self.partner_shipping_id or super()._get_avatax_ship_to_partner()
