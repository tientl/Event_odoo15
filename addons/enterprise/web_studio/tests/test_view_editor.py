import odoo
from odoo import api
from odoo.tools import DotDict
from odoo.http import _request_stack
from odoo.tests.common import TransactionCase
from odoo.addons.web_studio.controllers.main import WebStudioController
from copy import deepcopy
from lxml import etree

class TestStudioController(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env = api.Environment(self.cr, odoo.SUPERUSER_ID, {'load_all_views': True})
        _request_stack.push(self)
        self.session = DotDict({'debug': False})
        self.studio_controller = WebStudioController()

    def tearDown(self):
        super().tearDown()
        _request_stack.pop()

    def _transform_arch_for_assert(self, arch_string):
        parser = etree.XMLParser(remove_blank_text=True)
        arch_string = etree.fromstring(arch_string, parser=parser)
        return etree.tostring(arch_string, pretty_print=True, encoding='unicode')

    def assertViewArchEqual(self, original, expected):
        if original:
            original = self._transform_arch_for_assert(original)
        if expected:
            expected = self._transform_arch_for_assert(expected)
        self.assertEqual(original, expected)


class TestEditView(TestStudioController):

    def edit_view(self, base_view, studio_arch="", operations=None):
        _ops = None
        if isinstance(operations, list):
            _ops = []
            for op in operations:
                _ops.append(deepcopy(op))  # the edit view controller may alter objects in place
        if studio_arch == "":
            studio_arch = "<data/>"
        return self.studio_controller.edit_view(base_view.id, studio_arch, _ops)

    def test_edit_view_binary_and_attribute(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="display_name" />
                </form>"""
        })

        add_binary_op = {
            'type': 'add',
            'target': {'tag': 'field',
                       'attrs': {'name': 'display_name'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 1}]},
            'position': 'after',
            'node': {'tag': 'field',
                     'attrs': {},
                     'field_description': {'type': 'binary',
                                           'field_description': 'New File',
                                           'name': 'x_studio_binary_field_WocAO',
                                           'model_name': 'res.partner'}}
        }

        self.edit_view(base_view, operations=[add_binary_op])
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name"/>
                <field filename="x_studio_binary_field_WocAO_filename" name="x_studio_binary_field_WocAO"/>
                <field invisible="1" name="x_studio_binary_field_WocAO_filename"/>
              </form>
            """
        )

        add_widget_op = {
            'type': 'attributes',
            'target': {'tag': 'field',
                       'attrs': {'name': 'x_studio_binary_field_WocAO'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 2}]},
            'position': 'attributes',
            'node': {'tag': 'field',
                     'attrs': {'filename': 'x_studio_binary_field_WocAO_filename',
                               'name': 'x_studio_binary_field_WocAO',
                               'modifiers': {},
                               'id': 'x_studio_binary_field_WocAO'},
                     'children': [],
                     'has_label': True},
            'new_attrs': {'widget': 'pdf_viewer', 'options': ''}
        }

        ops = [
            add_binary_op,
            add_widget_op
        ]
        self.edit_view(base_view, operations=ops)
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name"/>
                <field filename="x_studio_binary_field_WocAO_filename" name="x_studio_binary_field_WocAO" widget="pdf_viewer"/>
                <field invisible="1" name="x_studio_binary_field_WocAO_filename"/>
              </form>
            """
        )

    def test_edit_view_binary_and_attribute_then_remove_binary(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'TestForm',
            'type': 'form',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="display_name" />
                </form>"""
        })

        add_binary_op = {
            'type': 'add',
            'target': {'tag': 'field',
                       'attrs': {'name': 'display_name'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 1}]},
            'position': 'after',
            'node': {'tag': 'field',
                     'attrs': {},
                     'field_description': {'type': 'binary',
                                           'field_description': 'New File',
                                           'name': 'x_studio_binary_field_WocAO',
                                           'model_name': 'res.partner'}}
        }

        self.edit_view(base_view, operations=[add_binary_op])

        add_widget_op = {
            'type': 'attributes',
            'target': {'tag': 'field',
                       'attrs': {'name': 'x_studio_binary_field_WocAO'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 2}]},
            'position': 'attributes',
            'node': {'tag': 'field',
                     'attrs': {'filename': 'x_studio_binary_field_WocAO_filename',
                               'name': 'x_studio_binary_field_WocAO',
                               'modifiers': {},
                               'id': 'x_studio_binary_field_WocAO'},
                     'children': [],
                     'has_label': True},
            'new_attrs': {'widget': 'pdf_viewer', 'options': ''}
        }

        ops = [
            add_binary_op,
            add_widget_op
        ]
        self.edit_view(base_view, operations=ops)

        remove_binary_op = {
            'type': 'remove',
            'target': {'tag': 'field',
                       'attrs': {'name': 'x_studio_binary_field_WocAO'},
                       'xpath_info': [{'tag': 'form', 'indice': 1},
                                      {'tag': 'field', 'indice': 2}]},
        }
        self.edit_view(base_view, operations=ops + [remove_binary_op])
        # The filename field is still present in the view
        # this is not intentional rather, it is way easier to leave this invisible field there
        self.assertViewArchEqual(
            base_view.get_combined_arch(),
            """
              <form>
                <field name="display_name"/>
                <field invisible="1" name="x_studio_binary_field_WocAO_filename"/>
              </form>
            """
        )
