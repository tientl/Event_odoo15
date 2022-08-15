# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    twitter_preview = fields.Html('Twitter Preview', compute='_compute_twitter_preview')
    display_twitter_preview = fields.Boolean('Display Twitter Preview', compute='_compute_display_twitter_preview')

    @api.depends('message', 'account_ids.media_id.media_type')
    def _compute_display_twitter_preview(self):
        for post in self:
            post.display_twitter_preview = post.message and ('twitter' in post.account_ids.media_id.mapped('media_type'))

    @api.depends(lambda self: ['message', 'image_ids'] + self._get_post_message_modifying_fields())
    def _compute_twitter_preview(self):
        for post in self:
            post.twitter_preview = self.env.ref('social_twitter.twitter_preview')._render({
                'message': post._prepare_post_content(
                    post.message,
                    'twitter',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'images': [
                    image.with_context(bin_size=False).datas
                    for image in post.image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
                ]
            })
