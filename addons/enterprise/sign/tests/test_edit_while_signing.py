# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .test_common import TestSignCommon
from odoo import http
from odoo.tests.common import HttpCase

class TestEditModeWhileSigning(HttpCase, TestSignCommon):
    def setUp(self):
        super().setUp()
        self.authenticate(self.test_user.login, self.test_user.login)

    def _build_jsonrpc_payload(self, params):
        """
        Helper to properly build jsonrpc payload
        """
        if not getattr(self, 'session', None):
            # We need to create a session (public if no login & passwd)
            # before generating a csrf token
            self.authenticate('', '')
        params['csrf_token'] = http.WebRequest.csrf_token(self)
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": None
        }

    def _build_url(self, route):
        return self.base_url() + route

    # test cases for edit while signing
    def test_sign_without_new_items(self):
        sign_request = self.single_role_sign_request
        sign_request_id = sign_request.id
        # sign it
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values}

        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))

        # check sign was succesful
        self.assertTrue(sign_result.json()['result'])
        # check template is the same
        self.assertEqual(sign_request.template_id.id, self.template.id)
        # check sign items are the same
        self.assertEqual(
            self.template.sign_item_ids.mapped('id'),
            sign_request.template_id.sign_item_ids.mapped('id')
        )
        self.assertEqual(sign_request.state, 'signed')

    def test_sign_with_new_items(self):
        sign_request = self.single_role_sign_request
        sign_request_id = sign_request.id

        # sign it
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_values['-1'] = 'aaaaa'
        new_sign_items = self.create_new_sign_items_object(sign_request_item.role_id.id)

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values, 'new_sign_items': new_sign_items}
        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))

        # check sign was succesful
        self.assertTrue(sign_result.json()['result'])
        # check template is different
        self.assertNotEqual(sign_request.template_id.id, self.template.id)
        # check sign items are different
        self.assertNotEqual(
            self.template.sign_item_ids.mapped('id'),
            sign_request.template_id.sign_item_ids.mapped('id')
        )
        # check count of items is equal to last template + items
        self.assertEqual(len(sign_request.template_id.sign_item_ids), 2)
        self.assertEqual(sign_request.state, 'signed')

    def test_sign_with_new_items_with_wrong_type_fails(self):
        sign_request = self.single_role_sign_request
        sign_request_id = sign_request.id

        # sign it
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_values['-1'] = 'aaaaa'
        new_sign_items = self.create_new_sign_items_object(sign_request_item.role_id.id)
        new_sign_items['-1']['type_id'] = self.env.ref('sign.sign_item_type_email').id

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values, 'new_sign_items': new_sign_items}
        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))

        self.assertFalse(sign_result.json()['result'])
        self.assertEqual(sign_request.template_id.id, self.template.id)
        self.assertEqual(len(sign_request.template_id.sign_item_ids), 1)
        self.assertEqual(sign_request.state, 'sent')

    def test_add_new_items_as_first_signer_in_multi_role_document(self):
        sign_request = self.multi_role_sign_request
        sign_request_id = sign_request.id

        # sign it
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_values['-1'] = 'aaaaa'
        new_sign_items = self.create_new_sign_items_object(sign_request_item.role_id.id)

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values, 'new_sign_items': new_sign_items}

        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))
        self.assertTrue(sign_result.json()['result'])

        # sign last request_item
        sign_request_item = sign_request.request_item_ids[1]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values}
        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))

        self.assertTrue(sign_result.json()['result'])
        self.assertEqual(len(sign_request.template_id.sign_item_ids), 3)
        self.assertEqual(sign_request.state, 'signed')

    def test_add_new_items_as_second_signer_in_multi_role_document_fails(self):
        sign_request = self.multi_role_sign_request
        sign_request_id = sign_request.id

        # sign it
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values}

        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))
        self.assertTrue(sign_result.json()['result'])

        # sign last request_item
        sign_request_item = sign_request.request_item_ids[1]
        sign_values = self.create_sign_values(sign_request.template_id.sign_item_ids, sign_request_item.role_id.id)
        sign_values['-1'] = 'aaaaa'
        new_sign_items = self.create_new_sign_items_object(sign_request_item.role_id.id)

        sign_request.request_item_ids.invalidate_cache()
        url = "/sign/sign/%s/%s" % (sign_request_id, sign_request_item.access_token)
        data = {'signature': sign_values, 'new_sign_items': new_sign_items}

        sign_result = self.opener.post(self._build_url(url), json=self._build_jsonrpc_payload(data))

        self.assertFalse(sign_result.json()['result'])
        self.assertEqual(sign_request.state, 'sent')
