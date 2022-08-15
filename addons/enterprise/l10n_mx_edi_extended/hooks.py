# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os.path import join, dirname, realpath
from odoo import api, SUPERUSER_ID
import csv


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    mx_country = env["res.country"].search([("code", "=", "MX")])

    # ==== Load l10n_mx_edi.res.locality ====

    if not env['l10n_mx_edi.res.locality'].search_count([]):
        csv_path = join(dirname(realpath(__file__)), 'data', 'l10n_mx_edi.res.locality.csv')
        tariff_fraction_vals_list = []
        with open(csv_path, 'r') as csv_file:
            for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['code', 'name', 'state_xml_id']):
                state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
                tariff_fraction_vals_list.append({
                    'code': row['code'],
                    'name': row['name'],
                    'state_id': state.id if state else False,
                    'country_id': mx_country.id,
                })

        localities = env['l10n_mx_edi.res.locality'].create(tariff_fraction_vals_list)

        if localities:
            cr.execute('''
               INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
                   SELECT 
                        'res_locality_mx_' || lower(res_country_state.code) || '_' || l10n_mx_edi_res_locality.code,
                        l10n_mx_edi_res_locality.id,
                        'l10n_mx_edi_extended',
                        'l10n_mx_edi.res.locality',
                        TRUE
                   FROM l10n_mx_edi_res_locality
                   JOIN res_country_state ON res_country_state.id = l10n_mx_edi_res_locality.state_id
                   WHERE l10n_mx_edi_res_locality.id IN %s
            ''', [tuple(localities.ids)])

    # ==== Load l10n_mx_edi.tariff.fraction ====

    if not env['l10n_mx_edi.tariff.fraction'].search_count([]):
        csv_path = join(dirname(realpath(__file__)), 'data', 'l10n_mx_edi.tariff.fraction.csv')
        tariff_fraction_vals_list = []
        with open(csv_path, 'r') as csv_file:
            for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['code', 'name', 'uom_code']):
                tariff_fraction_vals_list.append(row)

        tariff_fractions = env['l10n_mx_edi.tariff.fraction'].create(tariff_fraction_vals_list)

        if tariff_fractions:
            cr.execute('''
               INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
                   SELECT 
                        'tariff_fraction_' || l10n_mx_edi_tariff_fraction.code,
                        l10n_mx_edi_tariff_fraction.id,
                        'l10n_mx_edi_extended',
                        'l10n_mx_edi.tariff.fraction',
                        TRUE
                   FROM l10n_mx_edi_tariff_fraction
                   WHERE l10n_mx_edi_tariff_fraction.id IN %s
            ''', [tuple(tariff_fractions.ids)])


def uninstall_hook(cr, registry):
    cr.execute("DELETE FROM ir_model_data WHERE model='l10n_mx_edi.tariff.fraction';")
