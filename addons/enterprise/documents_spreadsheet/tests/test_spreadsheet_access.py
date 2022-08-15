# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .common import SpreadsheetTestCommon

from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.exceptions import AccessError

@tagged("post_install", "-at_install")
class SpreadsheetAccessTest(SpreadsheetTestCommon):

    @classmethod
    def setUpClass(cls):
        super(SpreadsheetAccessTest, cls).setUpClass()

        group = cls.env["res.groups"].create({"name": "test group"})
        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "ir.model")]).id,
            'group_id': group.id,
            'perm_read': True,
        })
        cls.tech_user = cls.env['res.users'].create({
                'name': 'I can use read ir.model!',
                'login': 'irModelDude',
                'password': 'irModelDude',
                'groups_id': [
                    (6, 0, [cls.env.ref('base.group_user').id, group.id])
                ],
            })
        cls.portal_user = new_test_user(
            cls.env, login="portalDude", groups="base.group_portal"
        )

    def test_name_get_access_01(self):
        IrModel = self.env['ir.model']
        SpreadsheetIrModel = IrModel.with_user(self.spreadsheet_user)
        ir_model_records = IrModel.search_read(
                domain=[('model', 'in', ['res.partner', "ir.model.fields"])],
                fields=["id"],
            )
        ir_model_record_ids = [rec['id'] for rec in ir_model_records]
        ir_model_res_partner_id, ir_model_ir_model_fields_id = ir_model_record_ids

        self.assertIsInstance(
            SpreadsheetIrModel.browse(ir_model_res_partner_id).name_get(),
            list,
            "Spreadsheet user can access ir.model of 'res.partner'"
        )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot access ir.model of 'ir.model.fields'"):
            SpreadsheetIrModel.browse(ir_model_ir_model_fields_id).name_get()

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot access ir.model of ir.model.fields'"):
            SpreadsheetIrModel.browse(ir_model_record_ids).name_get()


        with self.assertRaises(
            AccessError, msg="portal user cannot read ir.model related to accessible model 'res.partner'"
        ):
            IrModel.with_user(self.portal_user).browse(ir_model_res_partner_id).name_get()

        self.assertIsInstance(
            IrModel.with_user(self.tech_user).browse(ir_model_ir_model_fields_id).name_get(),
            list,
            "Technical user can access ir.model of 'ir.model.fields'"
        )


    def test_name_search_access_02(self):
        IrModel = self.env['ir.model']
        SpreadsheetIrModel = IrModel.with_user(self.spreadsheet_user)

        self.assertIsInstance(
            SpreadsheetIrModel.name_search(name="res.p", args=[("model", "in", ["res.partner"])]),
            list,
            "allow read on allowed domain"
        )

        self.assertIsInstance(
            SpreadsheetIrModel.name_search(name="res.p", args=[("model", "=", "res.partner")]),
            list,
            "allow read on allowed domain"
        )

        self.assertIsInstance(
            SpreadsheetIrModel.name_search(name="res.p", args=[
                ("model", "in", ["res.partner"]),
                ("model", "in", ["res.partner.bank"])
            ]),
            list,
            "allow read on multiple allowed domains"
        )

        with self.assertRaises(
            AccessError, msg="portal user cannot read on valid domain"
        ):
            IrModel.with_user(self.portal_user)\
                .name_search(name="res.p", args=[("model", "in", ["res.partner"])])

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on forbidden models"
        ):
            SpreadsheetIrModel.name_search(name="%", args=[])

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on forbidden models (bis)"
        ):
            SpreadsheetIrModel.name_search(name="%", args=["!", ("model", "=", "res.partner.bank")])

        self.assertIsInstance(
            IrModel.with_user(self.tech_user).name_search(name="%", args=[]),
            list,
            "tech user allowed to red on any domain"
        )

    def test_search_read_access_03(self):
        IrModel = self.env['ir.model']
        SpreadsheetIrModel = IrModel.with_user(self.spreadsheet_user)

        # Valid Domain
        self.assertIsInstance(
            SpreadsheetIrModel.search_read(
                domain=[("model", "in", ["res.partner"])],
                fields=["name", "id", "model"]
            ),
            list,
            "allow read on allowed domain and fields"
        )

        self.assertIsInstance(
            SpreadsheetIrModel.search_read(
                domain=[("model", "=", "res.partner")],
                fields=["name", "id", "model"]
            ),
            list,
            "allow read on allowed domain"
        )

        self.assertIsInstance(
            SpreadsheetIrModel.search_read(domain=[
                ("model", "in", ["res.partner"]),
                ("model", "in", ["res.partner.bank"])
            ], fields=["name", "id", "model"]),
            list,
            "allow read on multiple allowed domains"
        )

        with self.assertRaises(
            AccessError, msg="portal user cannot read on valid domain and valid fields"
        ):
            IrModel.with_user(self.portal_user).search_read(
                domain=[("model", "in", ["res.partner"])],
                fields=["name", "id", "model"]
            )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on valid domain and invalid fields"
        ):
            SpreadsheetIrModel.search_read(
                domain=[("model", "in", ["res.partner"])],
                fields=["name", "id", "model", "state"]
            )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on valid domain and empty"
        ):
            SpreadsheetIrModel.search_read(
                domain=[("model", "in", ["res.partner"])],
                fields=None
            )

        #Invalid Domain
        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on invalid domain and valid fields"
        ):
            SpreadsheetIrModel.search_read(
                domain=[("model", "in", ["ir.model.fields"])],
                fields=["name", "id", "model"]
            )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on invalid domain and valid fields"
        ):
            SpreadsheetIrModel.search_read(
                domain=[("model", "=", "ir.model.fields")],
                fields=["name", "id", "model"]
            )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on invalid domain and invalid fields"
        ):
            SpreadsheetIrModel.search_read(
                domain=[("model", "in", ["ir.model.fields"])],
                fields=["name", "id", "model", "state"]
            )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on valid domain and empty fields"
        ):
            SpreadsheetIrModel.search_read(
                domain=[("model", "in", ["ir.model.fields"])],
                fields=None
            )

        with self.assertRaises(
            AccessError, msg="spreadsheet user cannot read on forbidden models "
        ):
            SpreadsheetIrModel.search_read(
                domain=[],
                fields=["name", "id", "model"]
            )

        self.assertIsInstance(
            IrModel.with_user(self.tech_user).search_read(
                domain=[],
                fields=["state"]
            ),
            list,
            "Technical user can read with any domain or static fields"
        )
