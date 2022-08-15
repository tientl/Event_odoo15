# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import common
from odoo.addons.social_facebook.models.social_account import SocialAccountFacebook
from odoo.addons.social_linkedin.models.social_account import SocialAccountLinkedin
from odoo.addons.social_twitter.models.social_account import SocialAccountTwitter
from odoo.addons.social_youtube.models.social_account import SocialAccountYoutube


class SocialTestFullCase(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(SocialTestFullCase, cls).setUpClass()
        media_refs = [
            'social_facebook.social_media_facebook',
            'social_twitter.social_media_twitter',
            'social_linkedin.social_media_linkedin',
            'social_push_notifications.social_media_push_notifications',
            'social_youtube.social_media_youtube',
        ]

        with patch.object(SocialAccountFacebook, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountTwitter, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountLinkedin, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountYoutube, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountFacebook, '_create_default_stream_facebook', lambda *args, **kwargs: None), \
             patch.object(SocialAccountTwitter, '_create_default_stream_twitter', lambda *args, **kwargs: None), \
             patch.object(SocialAccountLinkedin, '_create_default_stream_linkedin', lambda *args, **kwargs: None), \
             patch.object(SocialAccountYoutube, '_create_default_stream_youtube', lambda *args, **kwargs: None):
            # create one account for every media type
            cls.accounts = cls.env['social.account'].create([{
                'media_id': cls.env.ref(media_ref).id,
                'name': 'Account'
            } for media_ref in media_refs])
