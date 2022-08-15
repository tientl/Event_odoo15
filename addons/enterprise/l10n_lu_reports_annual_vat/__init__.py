# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

def _post_init_hook(cr, registry):
    map_company_id_to_ids(cr, registry)

def map_company_id_to_ids(cr, registry):
    cr.execute("""
        INSERT INTO l10n_lu_yearly_tax_report_manual_res_company_rel (
            l10n_lu_yearly_tax_report_manual_id,
            res_company_id
        )
        SELECT
            id,
            company_id
        FROM l10n_lu_yearly_tax_report_manual;
    """)
