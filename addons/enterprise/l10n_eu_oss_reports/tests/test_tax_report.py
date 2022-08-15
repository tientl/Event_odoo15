# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class OSSTaxReportTest(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)

        cls.env.company.country_id = cls.env.ref('base.be')
        cls.env.company.vat = 'BE0477472701'

        tax_21 = cls.env['account.tax'].create({
            'name': "tax_21",
            'amount_type': 'percent',
            'amount': 21.0,
            'country_id': cls.env.ref('base.be').id
        })

        cls.env.company._map_eu_taxes()

        cls.product_1 = cls.env['product.product'].create({
            'name': 'product_1',
            'lst_price': 1000.0,
            'taxes_id': [Command.set(tax_21.ids)],
        })

        cls.partner_be = cls.env['res.partner'].create({
            'name': 'Partner BE',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.partner_fr = cls.env['res.partner'].create({
            'name': 'Partner FR',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.partner_lu = cls.env['res.partner'].create({
            'name': 'Partner LU',
            'country_id': cls.env.ref('base.lu').id,
        })

        cls.init_invoice('out_invoice', partner=cls.partner_be, products=cls.product_1, invoice_date=fields.Date.from_string('2021-04-01'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_fr, products=cls.product_1, invoice_date=fields.Date.from_string('2021-05-23'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_lu, products=cls.product_1, invoice_date=fields.Date.from_string('2021-06-12'), post=True)

    def test_tax_report_oss(self):
        """ Test tax report's content for 'domestic' foreign VAT fiscal position option.
        """
        report = self.env['account.generic.tax.report']
        options = self._init_options(
            report, fields.Date.from_string('2021-04-01'), fields.Date.from_string('2021-06-30'),
            {'tax_report': 'generic_oss_no_import'}
        )

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                        Net               Tax
            [   0,                            1,                2],
            [
                ("Sales",                    '',              370),
                ("France",                   '',              200),
                ("20.0% FR VAT (20.0%)",   1000,              200),
                ("Luxembourg",               '',              170),
                ("17.0% LU VAT (17.0%)",   1000,              170),
            ],
        )

    def test_generate_oss_xml_be(self):
        report = self.env['account.generic.tax.report']
        options = self._init_options(
            report, fields.Date.from_string('2021-04-01'), fields.Date.from_string('2021-06-30'),
            {'tax_report': 'generic_oss_no_import'}
        )

        expected_xml = """
            <ns0:OSSConsignment
              xmlns:ns2="urn:minfin.fgov.be:oss:common"
              xmlns:ns1="http://www.minfin.fgov.be/InputCommon"
              xmlns:ns0="http://www.minfin.fgov.be/OSSDeclaration"
              OSSDeclarationNbr="1">
              <ns0:OSSDeclaration SequenceNumber="1">
                <ns0:Trader_ID>
                  <ns2:VATNumber issuedBy="BE">0477472701</ns2:VATNumber>
                </ns0:Trader_ID>
                <ns0:Period>
                  <ns2:Year>2021</ns2:Year>
                  <ns2:Quarter>2</ns2:Quarter>
                </ns0:Period>
                <ns0:OSSDeclarationInfo SequenceNumber="1">
                  <ns2:MemberStateOfConsumption>FR</ns2:MemberStateOfConsumption>
                  <ns2:OSSDeclarationRows SequenceNumber="1">
                    <ns2:SupplyType>GOODS</ns2:SupplyType>
                    <ns2:FixedEstablishment>
                        <ns2:VATIdentificationNumber issuedBy="BE">0477472701</ns2:VATIdentificationNumber>
                    </ns2:FixedEstablishment>
                    <ns2:VatRateType>20.0</ns2:VatRateType>
                    <ns2:VatAmount currency="USD">200.0</ns2:VatAmount>
                    <ns2:TaxableAmount currency="USD">1000.0</ns2:TaxableAmount>
                  </ns2:OSSDeclarationRows>
                  <ns2:CorrectionsInfo>
                  </ns2:CorrectionsInfo>
                </ns0:OSSDeclarationInfo>
                <ns0:OSSDeclarationInfo SequenceNumber="2">
                  <ns2:MemberStateOfConsumption>LU</ns2:MemberStateOfConsumption>
                  <ns2:OSSDeclarationRows SequenceNumber="1">
                    <ns2:SupplyType>GOODS</ns2:SupplyType>
                    <ns2:FixedEstablishment>
                        <ns2:VATIdentificationNumber issuedBy="BE">0477472701</ns2:VATIdentificationNumber>
                    </ns2:FixedEstablishment>
                    <ns2:VatRateType>17.0</ns2:VatRateType>
                    <ns2:VatAmount currency="USD">170.0</ns2:VatAmount>
                    <ns2:TaxableAmount currency="USD">1000.0</ns2:TaxableAmount>
                  </ns2:OSSDeclarationRows>
                  <ns2:CorrectionsInfo>
                  </ns2:CorrectionsInfo>
                </ns0:OSSDeclarationInfo>
              </ns0:OSSDeclaration>
            </ns0:OSSConsignment>
        """

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(report.get_xml(options)),
            self.get_xml_tree_from_string(expected_xml)
        )
