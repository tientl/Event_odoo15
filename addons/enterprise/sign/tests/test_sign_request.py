# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .test_common import TestSignCommon
from unittest.mock import patch
from odoo.addons.sign.models.sign_log import SignLog


class TestSignRequest(TestSignCommon):
    @patch.object(SignLog, "_create_log")
    def test_sign_request_item_auto_resend(self, _create_log):
        sign_request = self.single_role_sign_request
        request_item_ids = sign_request.request_item_ids
        request_item = request_item_ids[0]
        token_a = request_item.access_token
        self.assertEqual(request_item.signer_email, "laurie.poiret.a@example.com", 'email address should be laurie.poiret.a@example.com')
        self.assertEqual(request_item.is_mail_sent, True, 'email should be sent')
        # resends the document
        request_item.resend_sign_access()
        self.assertEqual(request_item.access_token, token_a, "sign request item's access token should not be changed")
        # change the email address of the signer (laurie.poiret.b@example.com)
        self.partner_id.write({'email': 'laurie.poiret.b@example.com'})
        token_b = request_item.access_token
        self.assertEqual(request_item.signer_email, "laurie.poiret.b@example.com", 'email address should be laurie.poiret.b@example.com')
        self.assertNotEqual(token_b, token_a, "sign request item's access token should be changed")
        # sign the document
        request_item.write({'state': 'completed'})
        self.assertEqual(request_item.signer_email, "laurie.poiret.b@example.com", 'email address should be laurie.poiret.b@example.com')
        # change the email address of the signer (laurie.poiret.c@example.com)
        self.partner_id.write({'email': 'laurie.poiret.c@example.com'})
        token_c = request_item.access_token
        self.assertEqual(request_item.signer_email, "laurie.poiret.b@example.com", 'email address should be laurie.poiret.b@example.com')
        self.assertEqual(token_c, token_b, "sign request item's access token should be not changed after the document is signed by the signer")

    def test_templates_send_accesses(self):
        for sign_request in [self.default_role_sign_request, self.multi_role_sign_request, self.single_role_sign_request]:
            self.assertTrue(all(sign_request.request_item_ids.mapped('is_mail_sent')))
