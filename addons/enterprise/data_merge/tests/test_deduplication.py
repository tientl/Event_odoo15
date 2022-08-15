# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import test_common

class TestDeduplication(test_common.TestCommon):
    def test_deduplication_exact(self):
        self._create_rule('x_name', 'exact')

        self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model', x_name='titi')
        self._create_record('x_dm_test_model', x_name='tutu')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        self._create_record('x_dm_test_model', x_name='toto')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 2, '2 records should have been found')

    def test_deduplication_accent(self):
        self._create_rule('x_name', 'accent')

        self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model', x_name='titi')
        self._create_record('x_dm_test_model', x_name='tutu')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        self._create_record('x_dm_test_model', x_name='tùtù')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 2, '2 records should have been found')

    def test_deduplication_multiple(self):
        self._create_rule('x_name', 'exact')
        self._create_rule('x_email', 'exact')

        self._create_record('x_dm_test_model', x_name='toto', x_email='toto@example.com')
        self._create_record('x_dm_test_model', x_name='bob', x_email='bob@example.com')
        self._create_record('x_dm_test_model', x_name='alfred', x_email='alfred@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 0, '0 record should have been found')

        self._create_record('x_dm_test_model', x_name='toto', x_email='real_toto@example.com')
        self._create_record('x_dm_test_model', x_name='titi', x_email='bob@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 4, '4 records should have been found')

        self.DMGroup.search([('model_id', '=', self.MyModel.id)]).unlink()

        self._create_record('x_dm_test_model', x_name='titi', x_email='real_toto@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 5, '5 records should have been found')
        self.assertEqual(self.DMGroup.search_count([('model_id', '=', self.MyModel.id)]), 1, '1 group should have been created')

        self.DMGroup.search([('model_id', '=', self.MyModel.id)]).unlink()

        self._create_record('x_dm_test_model', x_name='robert', x_email='alfred@example.com')
        self._create_record('x_dm_test_model', x_name='jacky', x_email='jacky@example.com')
        self.MyModel.find_duplicates()
        self.MyModel._compute_records_to_merge_count()

        self.assertEqual(self.MyModel.records_to_merge_count, 7, '7 records should have been found')
        self.assertEqual(self.DMGroup.search_count([('model_id', '=', self.MyModel.id)]), 2, '2 groups should have been created')

    def test_record_references(self):
        self._create_rule('x_name', 'exact')

        rec = self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model_ref', x_name='ref toto', x_test_id=rec.id)
        self._create_record('x_dm_test_model', x_name='toto')
        self.MyModel.find_duplicates()

        records = self.env['data_merge.record'].search([('res_id', '=', rec.id), ('model_id', '=', self.MyModel.id)])

        self.assertEqual(len(records), 1, "Should have found 1 record")

        ref = records[0]._get_references().get(records[0].id)

        self.assertEqual(len(ref), 1, "The record should have 1 reference")
        self.assertEqual(ref[0][0], 1, "The record should have 1 referencing record")
        self.assertEqual(ref[0][1], 'Test Model Ref', "Model should be Test Model Ref")

    def test_record_active(self):
        self._create_rule('x_name', 'exact')
        rec = self._create_record('x_dm_test_model', x_name='toto')
        self._create_record('x_dm_test_model', x_name='toto')
        self.MyModel.find_duplicates()

        records = self.env['data_merge.record'].search([('res_id', '=', rec.id), ('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(records), 1, "Should have found 1 record")

        record = records[0]
        self.assertEqual(record._original_records(), rec, "Both records should be equal")
        self.assertTrue(record.active, "The record should be active")
        self.assertFalse(record.is_discarded, "Should not be discarded")
        self.assertFalse(record.is_deleted, "Should not be deleted")

        rec.unlink()
        record._compute_active()
        self.assertFalse(record.active, "Record should be inactive")
        self.assertTrue(record.is_deleted, "The record should be deleted")
