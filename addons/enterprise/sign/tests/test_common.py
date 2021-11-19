# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import _
from odoo.tools import file_open
from odoo.tests.common import TransactionCase, new_test_user
from odoo.addons.sign.models.sign_log import SignLog

class TestSignCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with file_open('sign/static/demo/sample_contract.pdf', "rb") as f:
            pdf_content = f.read()

        cls.test_user = new_test_user(cls.env, "test_user_1", email="test_user_1@nowhere.com", password="test_user_1", tz="UTC")

        cls.attachment = cls.env['ir.attachment'].create({
            'type': 'binary',
            'raw': pdf_content,
            'name': 'test_employee_contract.pdf',
        })
        cls.template = cls.env['sign.template'].create({
            'attachment_id': cls.attachment.id,
            'sign_item_ids': [(6, 0, [])],
        })
        cls.env['sign.item'].create([
            {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'name': 'employee_id.name',
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.273,
                'posY': 0.158,
                'template_id': cls.template.id,
                'width': 0.150,
                'height': 0.015,
            },
        ])

        cls.template_multi_role = cls.env['sign.template'].create({
            'attachment_id': cls.attachment.id,
            'sign_item_ids': [(6, 0, [])],
        })
        cls.env['sign.item'].create([
            {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'name': 'customer_id.name',
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_customer').id,
                'page': 1,
                'posX': 0.273,
                'posY': 0.158,
                'template_id': cls.template_multi_role.id,
                'width': 0.150,
                'height': 0.015,
            },
        ])
        cls.env['sign.item'].create([
            {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'name': 'employee_id.name',
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.373,
                'posY': 0.258,
                'template_id': cls.template_multi_role.id,
                'width': 0.150,
                'height': 0.015,
            },
        ])

        cls.template_without_sign_items = cls.env['sign.template'].create({
            'attachment_id': cls.attachment.id,
            'sign_item_ids': [(6, 0, [])]
        })

        cls.company_id = cls.env['res.company'].create({
            'name': 'My Belgian Company - TEST',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.partner_id = cls.env['res.partner'].create({
            'name': 'Laurie Poiret',
            'street': '58 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543210',
            'email': 'laurie.poiret.a@example.com',
            'company_id': cls.company_id.id,
        })

        cls.partner_2_id = cls.env['res.partner'].create({
            'name': 'Laurie Poirot',
            'street': '58 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543210',
            'email': 'laurie.poirot.a@example.com',
            'email_normalized': 'laurie.poirot.a@example.com',
            'company_id': cls.company_id.id,
        })

        cls.single_role_sign_request = cls.create_sign_request(cls, cls.template, [cls.partner_id.id])
        cls.multi_role_sign_request = cls.create_sign_request(cls, cls.template_multi_role, [cls.partner_id.id, cls.partner_2_id.id])
        cls.default_role_sign_request = cls.create_sign_request(cls, cls.template_without_sign_items, [cls.partner_id.id])

    @patch.object(SignLog, "_create_log")
    def create_sign_request(self, template, partners, _create_log=None):
        data = {
            'template_id': template.id,
            'signer_id': partners[0],
            'filename': template.display_name,
            'subject': _("Signature Request - %s", (template.attachment_id.name or '')),
        }
        roles = template.mapped('sign_item_ids.responsible_id')

        signer_ids = [(0, 0, {
            'role_id': role.id,
            'partner_id': partners[index],
        }) for index, role in enumerate(roles)]
        data['signer_ids'] = [(5, 0, 0)] + signer_ids
        data['signers_count'] = len(roles)

        sign_send_request = self.env['sign.send.request'].create(data)

        sign_request_id = sign_send_request.create_request()['id']
        sign_request = self.env['sign.request'].browse(sign_request_id)
        return sign_request

    def create_new_sign_items_object(self, role_id):
        return {
            '-1': {
                'type_id': self.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'option_ids': [],
                'responsible_id': role_id,
                'page': 1,
                'posX': 0.1,
                'posY': 0.2,
                'width': 0.15,
                'height': 0.15
            }
        }

    def create_sign_values(self, sign_item_ids, role_id):
        return {
            str(sign_id): 'a'
            for sign_id in sign_item_ids
            .filtered(lambda r: not r.responsible_id or r.responsible_id.id == role_id)
            .mapped('id')
        }
