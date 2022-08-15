# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class BelgiumSalesReportTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass('l10n_be.l10nbe_chart_template')

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        l_tax = self.env['account.tax'].search([('name', '=', '0% EU M.'), ('company_id', '=', self.company_data['company'].id)])[0]
        t_tax = self.env['account.tax'].search([('name', '=', '0% EU T.'), ('company_id', '=', self.company_data['company'].id)])[0]
        s_tax = self.env['account.tax'].search([('name', '=', '0% EU S.'), ('company_id', '=', self.company_data['company'].id)])[0]
        self._create_invoices([
            (self.partner_a, l_tax, 300),
            (self.partner_a, l_tax, 300),
            (self.partner_a, t_tax, 500),
            (self.partner_b, t_tax, 500),
            (self.partner_a, s_tax, 700),
            (self.partner_b, s_tax, 700),
        ])
        report = self.env['account.sales.report']
        options = report._get_options(None)
        self.assertEqual(report._get_report_country_code(options), 'BE', "The country chosen for EC Sales list should be Belgium")
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Partner                country code,            VAT Number,              Tax         Amount
            [   0,                     1,                       2,                       3,          4],
            [
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'L (46L)',  '600.00 €'),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'T (46T)',  '500.00 €'),
                (self.partner_b.name,  self.partner_b.vat[:2],  self.partner_b.vat[2:],  'T (46T)',  '500.00 €'),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'S (44)',   '700.00 €'),
                (self.partner_b.name,  self.partner_b.vat[:2],  self.partner_b.vat[2:],  'S (44)',   '700.00 €'),
            ],
        )

        expected_xml = '''
        <ns2:IntraConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/IntraConsignment" IntraListingsNbr="1">
            <ns2:IntraListing SequenceNumber="1" ClientsNbr="5" DeclarantReference="___ignore___" AmountSum="3000.00">
                <ns2:Declarant>
                    <VATNumber>0477472701</VATNumber>
                    <Name>company_1_data</Name>
                    <Street></Street>
                    <PostCode></PostCode>
                    <City></City>
                    <CountryCode>BE</CountryCode>
                    <EmailAddress>jsmith@mail.com</EmailAddress>
                    <Phone>+32475123456</Phone>
                </ns2:Declarant>
                <ns2:Period>
                    <ns2:Month>12</ns2:Month>
                    <ns2:Year>2019</ns2:Year>
                </ns2:Period>
                <ns2:IntraClient SequenceNumber="1">
                    <ns2:CompanyVATNumber issuedBy="AA">123456789</ns2:CompanyVATNumber>
                    <ns2:Code>L</ns2:Code>
                    <ns2:Amount>600.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="2">
                    <ns2:CompanyVATNumber issuedBy="AA">123456789</ns2:CompanyVATNumber>
                    <ns2:Code>T</ns2:Code>
                    <ns2:Amount>500.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="3">
                    <ns2:CompanyVATNumber issuedBy="BB">123456789</ns2:CompanyVATNumber>
                    <ns2:Code>T</ns2:Code>
                    <ns2:Amount>500.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="4">
                    <ns2:CompanyVATNumber issuedBy="AA">123456789</ns2:CompanyVATNumber>
                    <ns2:Code>S</ns2:Code>
                    <ns2:Amount>700.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="5">
                    <ns2:CompanyVATNumber issuedBy="BB">123456789</ns2:CompanyVATNumber>
                    <ns2:Code>S</ns2:Code>
                    <ns2:Amount>700.00</ns2:Amount>
                </ns2:IntraClient>
                </ns2:IntraListing>
            </ns2:IntraConsignment>
                '''
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(report.get_xml(options)),
            self.get_xml_tree_from_string(expected_xml)
        )
