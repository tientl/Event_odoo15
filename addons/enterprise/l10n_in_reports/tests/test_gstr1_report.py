# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
import logging
from odoo.tools.misc import NON_BREAKING_SPACE


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.maxDiff = None
        cls.company_data["company"].write({
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
            })
        cls.partner_a.write({
            "vat": "24BBBFF5679L8ZR",
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street2",
            "city": "city2",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
            })
        cls.product_a.write({"l10n_in_hsn_code": "01111"})
        cls.invoice = cls.init_invoice(
            "out_invoice",
            post=True,
            products=cls.product_a,
            taxes=cls.company_data["default_tax_sale"]
        )

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # TODO: default_account_tax_sale is not set when default_tax is group of tax
        # so when this method is called it's raise error so by overwrite this and stop call supper.
        return cls.env["account.tax"]

    def test_gstr1_b2b_summary(self):
        report = self.env["l10n.in.report.account"]
        options = self._init_options(report, fields.Date.from_string("2019-01-01"), fields.Date.from_string("2019-12-31"))
        lines = report._get_lines(options)
        # For B2B Invoice - 4A, AB, 4C, 6B, 6C
        expected = [
            {"name": 1, "class": ""},
            {"name": f"₹{NON_BREAKING_SPACE}25.00", "class": "number"},
            {"name": f"₹{NON_BREAKING_SPACE}25.00", "class": "number"},
            {"name": f"₹{NON_BREAKING_SPACE}0.00", "class": "number"},
            {"name": f"₹{NON_BREAKING_SPACE}0.00", "class": "number"}
            ]
        self.assertListEqual(expected, lines[0]['columns'], "Wrong values for Indian GSTR-1 B2B summary report.")

    def test_gstr1_b2b_detailed_report(self):
        report = self.env["l10n.in.report.account"]
        options = self._init_options(report, fields.Date.from_string("2019-01-01"), fields.Date.from_string("2019-12-31"))
        options.update({'gst_section': 'b2b'})
        lines = report._get_lines(options)
        expected = [{'id': min(self.invoice.line_ids.filtered(lambda l: l.tax_line_id).ids),
            'caret_options': 'account.move',
            'name': 'INV/2019/00001',
            'class': 'o_account_reports_level2',
            'style': 'font-weight: normal;',
            'level': 1,
            'colspan': 0,
            'columns': [
                {'name': '24BBBFF5679L8ZR', 'class': ''}, # GSTIN(partner_vat)
                {'name': 'partner_a', 'class': ''}, # Partner name
                {'name': '01-JAN-2019', 'class': ''}, # Invoice date in DD-MMM-YYYY
                {'name': '24-Gujarat', 'class': ''},# place of supply
                {'name': 'N', 'class': ''}, # IS Reverse Charge
                {'name': 'Regular', 'class': ''}, # Invoice Type
                {'name': '', 'class': 'print_only'}, # E-Commerce GSTIN
                {'name': 5.0, 'class': ''}, # Tax rate
                {'name': 1050.0, 'class': 'number'}, # Invoice Value
                {'name': 1000.0, 'class': 'number'}, # Taxable Value
                {'name': 0.0, 'class': 'number'} # Cess tax Amount
            ],
        }]
        self.assertListEqual(expected, lines, "Wrong values for Indian GSTR-1 B2B detailed report.")
