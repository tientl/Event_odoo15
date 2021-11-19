# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, tools, SUPERUSER_ID
import csv


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    mx_country = env["res.country"].search([("code", "=", "MX")])

    res_city_vals_list = []
    with tools.file_open("l10n_mx_edi/data/res.city.csv", "r") as csv_file:
        for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['l10n_mx_edi_code', 'name', 'state_xml_id']):
            state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
            res_city_vals_list.append({
                'l10n_mx_edi_code': row['l10n_mx_edi_code'],
                'name': row['name'],
                'state_id': state.id if state else False,
                'country_id': mx_country.id,
            })

    cities = env['res.city'].create(res_city_vals_list)

    if cities:
        cr.execute('''
           INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
               SELECT 
                    'res_city_mx_' || lower(res_country_state.code) || '_' || res_city.l10n_mx_edi_code,
                    res_city.id,
                    'l10n_mx_edi',
                    'res.city',
                    TRUE
               FROM res_city
               JOIN res_country_state ON res_country_state.id = res_city.state_id
               WHERE res_city.id IN %s
        ''', [tuple(cities.ids)])

    # UNSPSC category codes can be used in Mexico.
    product_unspsc = env['product.unspsc.code'].search([('active', '=', False), ('code', '=ilike', '%00')])
    product_unspsc.active = True
