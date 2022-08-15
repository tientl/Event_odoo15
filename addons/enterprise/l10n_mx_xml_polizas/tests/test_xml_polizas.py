# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged
from odoo.addons.account_reports.tests.test_general_ledger_report import TestAccountReportsCommon

@tagged('post_install', 'post_install_l10n', '-at_install')
class AccountXmlPolizasWizard(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        """ Set up the test class for its own tests """
        super().setUpClass(chart_template_ref='l10n_mx.mx_coa')

        # Setup the company
        cls.company = cls.company_data['company']
        cls.company_2 = cls.company_data_2['company']
        cls.company.vat = 'AAAA611013AAA'
        cls.company_2.vat = 'P&G851223B24'
        cls.wizard = cls.env['l10n_mx_xml_polizas.xml_polizas_wizard'].create({
            "export_type": 'AF',
            "order_number": "ABC6987654/99",
        })

        # Create moves to check the export
        cls.moves_company_1 = cls.env['account.move'].create([{
                'move_type': 'entry',
                'date': date(2016, 1, 1),
                'journal_id': cls._get_id('journal_misc'),
                'line_ids': [
                    (0, 0, {'debit': 100.0, 'credit': 0.0, 'name': '2016_1_1', 'account_id': cls._get_id('account_payable')}),
                    (0, 0, {'debit': 200.0, 'credit': 0.0, 'name': '2016_1_2', 'account_id': cls._get_id('account_expense')}),
                    (0, 0, {'debit': 0.0, 'credit': 300.0, 'name': '2016_1_3', 'account_id': cls._get_id('account_revenue')}),
                ],
            }, {
                'move_type': 'entry',
                'date': date(2016, 6, 15),
                'journal_id': cls._get_id('journal_misc'),
                'line_ids': [
                    (0, 0, {'debit': 40.0, 'credit': 0.0, 'name': '2016_1b_1', 'account_id': cls._get_id('account_payable')}),
                    (0, 0, {'debit': 0.0, 'credit': 40.0, 'name': '2016_1b_1', 'account_id': cls._get_id('account_revenue')}),
                ],
            }, {
                'move_type': 'entry',
                'date': date(2017, 1, 1),
                'journal_id': cls._get_id('journal_misc'),
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'name': '2017_1_1', 'account_id': cls._get_id('account_receivable')}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0, 'name': '2017_1_2', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 3000.0, 'credit': 0.0, 'name': '2017_1_3', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 4000.0, 'credit': 0.0, 'name': '2017_1_4', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 5000.0, 'credit': 0.0, 'name': '2017_1_5', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 6000.0, 'credit': 0.0, 'name': '2017_1_6', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 0.0, 'credit': 6000.0, 'name': '2017_1_7', 'account_id': cls._get_id('account_expense')}),
                    (0, 0, {'debit': 0.0, 'credit': 7000.0, 'name': '2017_1_8', 'account_id': cls._get_id('account_expense')}),
                    (0, 0, {'debit': 0.0, 'credit': 8000.0, 'name': '2017_1_9', 'account_id': cls._get_id('account_expense')}),
                ],
            }
        ])
        cls.moves_company_1.action_post()

        cls.moves_company_2 = cls.env["account.move"].create([
            {
                'move_type': 'entry',
                'date': date(2016, 1, 1),
                'journal_id': cls._get_id('journal_misc', 2),
                'line_ids': [
                    (0, 0, {'debit': 100.0, 'credit': 0.0, 'name': '2016_2_1', 'account_id': cls._get_id('account_payable', 2)}),
                    (0, 0, {'debit': 0.0, 'credit': 100.0, 'name': '2016_2_2', 'account_id': cls._get_id('account_revenue', 2)}),
                ],
            }, {
                'move_type': 'entry',
                'date': date(2017, 6, 1),
                'journal_id': cls._get_id('journal_bank', 2),
                'line_ids': [
                    (0, 0, {'debit': 400.0, 'credit': 0.0, 'name': '2017_2_1', 'account_id': cls._get_id('account_expense', 2)}),
                    (0, 0, {'debit': 0.0, 'credit': 400.0, 'name': '2017_2_2', 'account_id': cls._get_id('account_revenue', 2)}),
                ],
            }
        ])
        cls.moves_company_2.action_post()

    @classmethod
    def _get_id(cls, name, company_no=1):
        """ Syntactic sugar method to simplify access to default accounts/journals """
        company_data = cls.company_data if company_no == 1 else cls.company_data_2
        return company_data['default_%s' % name].id

    def _get_xml_data(self, date_from, date_to, company=None):
        """ Fire the export wizard and get the generated XML and metadata (year, month, filename) """
        options = self._init_options(self.env['account.general.ledger'], date_from, date_to)
        wizard = self.wizard.with_context(l10n_mx_xml_polizas_generation_options=options)
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

    def test_xml_polizas_simple(self):
        """ Test a simple entry """
        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2017/01/0001">
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_1" DesCta="Clientes nacionales" NumCta="105.01.01" Haber="0.00" Debe="1000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_2" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="2000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_3" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="3000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_4" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="4000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_5" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="5000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_6" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="0.00" Debe="6000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_7" DesCta="Otros gastos generales" NumCta="601.84.01" Haber="6000.00" Debe="0.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_8" DesCta="Otros gastos generales" NumCta="601.84.01" Haber="7000.00" Debe="0.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_9" DesCta="Otros gastos generales" NumCta="601.84.01" Haber="8000.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='AAAA611013AAA201701PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_polizas_multicompany(self):
        """ For the same period, different move lines are exported for different companies"""
        date_from, date_to = date(2016, 1, 1), date(2016, 1, 31)

        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2016-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_1" DesCta="Proveedores nacionales" NumCta="201.01.01" Haber="0.00" Debe="100.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_2" DesCta="Otros gastos generales" NumCta="601.84.01" Haber="0.00" Debe="200.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_3" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="300.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        exported_file = self._get_xml_data(date_from, date_to)[0]
        self._assert_export_equal(year=2016, month=1, filename='AAAA611013AAA201601PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="01" RFC="P&amp;G851223B24">
                 <PLZ:Poliza Fecha="2016-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/01/0001">
                      <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_2_1" DesCta="Proveedores nacionales" NumCta="201.01.01" Haber="0.00" Debe="100.00"></PLZ:Transaccion>
                      <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_2_2" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="100.00" Debe="0.00"></PLZ:Transaccion>
                 </PLZ:Poliza>
            </PLZ:Polizas>"""
        exported_file = self._get_xml_data(date_from, date_to, company=self.company_2)[0]
        self._assert_export_equal(year=2016, month=1, filename='P&G851223B24201601PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_polizas_split_by_date(self):
        """ Test that the moves are split by date into different files """
        exported_files = self._get_xml_data(date(2016, 1, 1), date(2016, 12, 31))
        expected_xml_jan = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2016-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_1" DesCta="Proveedores nacionales" NumCta="201.01.01" Haber="0.00" Debe="100.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_2" DesCta="Otros gastos generales" NumCta="601.84.01" Haber="0.00" Debe="200.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_3" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="300.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        jan_filename = 'AAAA611013AAA201601PL.XML'
        exported_jan_file = next((x for x in exported_files if x['filename'] == jan_filename), None)
        self.assertIsNotNone(exported_jan_file)
        self._assert_export_equal(year=2016, month=1, filename=jan_filename,
                                  expected_xml=expected_xml_jan, actual_data=exported_jan_file)

        expected_xml_jun = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="06" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2016-06-15" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/06/0001">
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1b_1" DesCta="Proveedores nacionales" NumCta="201.01.01" Haber="0.00" Debe="40.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1b_1" DesCta="Ventas y/o servicios gravados a la tasa general" NumCta="401.01.01" Haber="40.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        jun_filename = 'AAAA611013AAA201606PL.XML'
        exported_jun_file = next((x for x in exported_files if x['filename'] == jun_filename), None)
        self.assertIsNotNone(exported_jun_file)
        self._assert_export_equal(year=2016, month=6, filename=jun_filename,
                                  expected_xml=expected_xml_jun, actual_data=exported_jun_file)
