from odoo import fields, models


class EventAddress(models.Model):
    _name = 'event.address'
    _description = 'Event Address'

    name = fields.Char(string='Tên địa điểm', required=True)
    address = fields.Char(string='Địa chỉ')
    phone = fields.Char(string='Số điện thoại')
    email = fields.Char(string='Email')