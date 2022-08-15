# -*- coding: utf-8 -*-

from odoo import models, fields

class Mod303BOEWizard(models.TransientModel):
    _inherit = 'l10n_es_reports.aeat.boe.mod303.export.wizard'

    using_sii = fields.Boolean(string="Using SII Voluntarily", default=False)
    exempted_from_mod_390 = fields.Boolean(string="Exempted From Modelo 390", default=False)
    exempted_from_mod_390_available = fields.Boolean(compute='_compute_show_exempted_from_mod_390', help="Technical field used to only make exempted_from_mod_390 avilable in the last period (12 or 4T)")

    def _compute_show_exempted_from_mod_390(self):
        report = self.env.ref('l10n_es_reports.mod_303')
        options = self.env.context.get('l10n_es_reports_report_options', {})
        period = report._get_mod_period_and_year(options)[0]
        for record in self:
            record.exempted_from_mod_390_available = period in ('12', '4T')

    def _get_using_sii_2021_value(self):
        # Overridden to handle new fields from 2021
        return 1 if self.using_sii else 2

    def _get_exonerated_from_mod_390_2021_value(self, period):
        # Overridden to handle new fields from 2021
        if period in ('12', '4T'):
            return 1 if self.exempted_from_mod_390 else 2
        return 0
