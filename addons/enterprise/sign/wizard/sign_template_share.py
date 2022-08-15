# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SignTemplateShare(models.TransientModel):
    _name = 'sign.template.share'
    _description = 'Sign Share Template'

    @api.model
    def default_get(self, fields):
        res = super(SignTemplateShare, self).default_get(fields)
        if 'url' in fields:
            template = self.env['sign.template'].browse(res.get('template_id'))
            invalid_selections = template.sign_item_ids.filtered(lambda item: item.type_id.item_type == 'selection' and not item.option_ids)
            if invalid_selections:
                raise UserError(_("One or more selection items have no associated options"))
            if template.responsible_count > 1:
                res['url'] = False
            else:
                if not template.share_link:
                    template.share_link = str(uuid.uuid4())
                res['url'] = "%s/sign/%s" % (template.get_base_url(), template.share_link)
        return res

    template_id = fields.Many2one(
        'sign.template', required=True, ondelete='cascade',
        default=lambda s: s.env.context.get("active_id", None),
    )
    url = fields.Char(string="Link to Share")
    user_id = fields.Many2one('res.users', related='template_id.user_id')
    is_one_responsible = fields.Boolean()

    def open(self):
        return {
            'name': _('Sign'),
            'type': 'ir.actions.act_url',
            'url': '/sign/%s' % (self.template_id.share_link),
        }
