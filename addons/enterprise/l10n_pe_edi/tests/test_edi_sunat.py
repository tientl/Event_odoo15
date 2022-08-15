# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import TestPeEdiCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiSunat(TestPeEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_pe.pe_chart_template', edi_format_ref='l10n_pe_edi.edi_pe_ubl_2_1'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.company_data['company'].l10n_pe_edi_provider = 'sunat'

    def test_10_invoice_edi_flow(self):
        move = self._create_invoice()
        move.action_post()

        # Send
        self._action_process_edi_web_services(move)
        generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
        self.assertTrue(generated_files)
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Cancel step 1
        move.l10n_pe_edi_cancel_reason = 'abc'
        move.button_cancel_posted_moves()
        self.assertFalse(move.l10n_pe_edi_cancel_cdr_number)
        self._action_process_edi_web_services(move)
        self.assertTrue(move.l10n_pe_edi_cancel_cdr_number)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])

        # Cancel step 2
        self._action_process_edi_web_services(move)
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])

    def test_20_refund_edi_flow(self):
        move = self._create_refund()
        (move.reversed_entry_id + move).action_post()

        # Send
        self._action_process_edi_web_services((move.reversed_entry_id + move))
        generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
        self.assertTrue(generated_files)
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Cancel step 1
        move.l10n_pe_edi_cancel_reason = 'abc'
        move.button_cancel_posted_moves()
        self.assertFalse(move.l10n_pe_edi_cancel_cdr_number)
        self._action_process_edi_web_services(move)
        self.assertTrue(move.l10n_pe_edi_cancel_cdr_number)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])

        # Cancel step 2
        self._action_process_edi_web_services(move)
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])

    def test_30_debit_note_edi_flow(self):
        move = self._create_debit_note()
        (move.debit_origin_id + move).action_post()

        # Send
        self._action_process_edi_web_services((move.debit_origin_id + move))
        generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
        self.assertTrue(generated_files)
        self.assertRecordValues(move, [{'edi_state': 'sent'}])

        # Cancel step 1
        move.l10n_pe_edi_cancel_reason = 'abc'
        move.button_cancel_posted_moves()
        self.assertFalse(move.l10n_pe_edi_cancel_cdr_number)
        self._action_process_edi_web_services(move)
        self.assertTrue(move.l10n_pe_edi_cancel_cdr_number)
        self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])

        # Cancel step 2
        self._action_process_edi_web_services(move)
        self.assertRecordValues(move, [{'edi_state': 'cancelled'}])
