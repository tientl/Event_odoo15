# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.account_reports.tests.test_general_ledger_report import TestAccountReportsCommon
from odoo.addons.l10n_mx_edi.models.account_move import AccountMove
from odoo.addons.l10n_mx_edi_40.tests.common import TestMxEdiCommon

@tagged('post_install', 'post_install_l10n', '-at_install')
class AccountEdiXmlPolizasWizard(TestMxEdiCommon, TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        """ Set up the test class for its own tests """
        super().setUpClass()

    @classmethod
    def _get_id(cls, name, company_no=1):
        """ Syntactic sugar method to simplify access to default accounts/journals """
        company_data = cls.company_data if company_no == 1 else cls.company_data_2
        return company_data['default_%s' % name].id

    def _get_xml_data(self, date_from, date_to, company=None):
        """ Fire the export wizard and get the generated XML and metadata (year, month, filename) """
        wizard = self.env['l10n_mx_xml_polizas.xml_polizas_wizard'].create({
            "export_type": 'AF',
            "order_number": "ABC6987654/99",
        })

        options = self._init_options(self.env['account.general.ledger'], date_from, date_to)
        wizard = wizard.with_context(l10n_mx_xml_polizas_generation_options=options)
        if company:
            wizard = wizard.with_company(company)
        return wizard._get_xml_data()

    def _assert_export_equal(self, year, month, filename, expected_xml, actual_data):
        """ Compare that the given export output file corresponds to what is expected """
        actual_xml_tree = self.get_xml_tree_from_string(actual_data['content'])
        expected_xml_tree = self.get_xml_tree_from_string(expected_xml.encode())
        self.assertEqual(actual_data['year'], "%04d" % year)
        self.assertEqual(actual_data['month'], "%02d" % month)
        self.assertEqual(actual_data['filename'], filename)
        self.assertXmlTreeEqual(actual_xml_tree, expected_xml_tree)

    def test_xml_edi_polizas_simple(self):
        """ Test XML Polizas is exported with CompNal info """

        def _fake_cfdi_values(self):
            '''Fill the invoice fields from the cfdi values.
            '''
            for move in self:
                move.l10n_mx_edi_cfdi_uuid = "AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA"
                move.l10n_mx_edi_cfdi_supplier_rfc = "EKU9003173C9"
                move.l10n_mx_edi_cfdi_customer_rfc = "XEXX010101000"
                move.l10n_mx_edi_cfdi_amount = 10.0

        invoice_a = self.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.company_data['currency'].id,
            'invoice_incoterm_id': self.env.ref('account.incoterm_FCA').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, (self.tax_16 + self.tax_10_negative).ids)],
            })],
        })

        with freeze_time(self.frozen_today):
            invoice_a.action_post()
        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="EKU9003173C9">
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Customer Invoices" NumUnIdenPol="INV/2017/00002">
                    <PLZ:Transaccion Concepto="Customer Invoices - INV/2017/00002" DesCta="Clientes nacionales" NumCta="105.01.01" Haber="0.00" Debe="8480.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="8480.0"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - product_mx" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="8000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-8000.0"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - tax_10_negative" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="800.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="800.0"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - tax_16" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="1280.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-1280.0"></PLZ:CompNal>
                    </PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>
            """

        with patch.object(AccountMove, '_compute_cfdi_values', _fake_cfdi_values):
            exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='EKU9003173C9201701PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_edi_polizas_multicurrency(self):
        """ Test XML Polizas is exported with CompNal info (multicurrency data)"""
        cur_eur = self.env.ref('base.EUR')
        cur_eur.active = True
        self.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': 0.05,
            'currency_id': cur_eur.id,
            'company_id': self.env.company.id,
        })

        self.env['res.currency.rate'].create({
            'name': '2017-01-02',
            'rate': 0.055,
            'currency_id': cur_eur.id,
            'company_id': self.env.company.id,
        })

        invoice = self.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': cur_eur.id,
            'invoice_incoterm_id': self.env.ref('account.incoterm_FCA').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'tax_ids': [(6, 0, (self.tax_16 + self.tax_10_negative).ids)],
            })],
        })

        def _fake_cfdi_values(self):
            for move in self:
                move.l10n_mx_edi_cfdi_uuid = "AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA"
                move.l10n_mx_edi_cfdi_supplier_rfc = "EKU9003173C9"
                move.l10n_mx_edi_cfdi_customer_rfc = "XEXX010101000"
                move.l10n_mx_edi_cfdi_amount = 10.0

        with freeze_time(self.frozen_today):
            invoice.action_post()
            with patch.object(AccountMove, '_compute_cfdi_values', _fake_cfdi_values):
                self.env['account.payment.register']\
                    .with_context(active_model='account.move', active_ids=invoice.ids)\
                    .create({
                        'currency_id': self.company_data['currency'].id,
                        'amount': 1820.0,
                        'payment_date': '2017-01-02',
                    })\
                    ._create_payments()

        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo" xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd" Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="EKU9003173C9">
                <PLZ:Poliza Fecha="2017-01-02" Concepto="Bank" NumUnIdenPol="BNK1/2017/01/0002">
                    <PLZ:Transaccion Concepto="Bank - Customer Payment $ 1,820.00 - partner_a - 01/02/2017" DesCta="Outstanding Receipts" NumCta="102.01.02" Haber="0.00" Debe="1820.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="1820.0"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Bank - Customer Payment $ 1,820.00 - partner_a - 01/02/2017" DesCta="Clientes nacionales" NumCta="105.01.01" Haber="1820.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-1820.0"></PLZ:CompNal>
                    </PLZ:Transaccion>
                </PLZ:Poliza>
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Customer Invoices" NumUnIdenPol="INV/2017/00002">
                    <PLZ:Transaccion Concepto="Customer Invoices - INV/2017/00002" DesCta="Clientes nacionales" NumCta="105.01.01" Haber="0.00" Debe="106000.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="5300.0" Moneda="EUR" TipCamb="20.00000"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - product_mx" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="100000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-5000.0" Moneda="EUR" TipCamb="20.00000"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - tax_10_negative" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="10000.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="500.0" Moneda="EUR" TipCamb="20.00000"></PLZ:CompNal>
                    </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - tax_16" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="16000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-800.0" Moneda="EUR" TipCamb="20.00000"></PLZ:CompNal>
                    </PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>
        """
        with patch.object(AccountMove, '_compute_cfdi_values', _fake_cfdi_values):
            exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='EKU9003173C9201701PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)
