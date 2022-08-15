# -*- coding: utf-8 -*-

from odoo import models, fields

class Mod303Wizard(models.TransientModel):
    _inherit = 'l10n_es_reports.mod303.wizard'

    casilla_78 = fields.Monetary(string="[78] Cuotas a compensar de periodos anteriores aplicadas en este periodo", default=0)
    casilla_110 = fields.Monetary(string="[110] Cuotas a compensar pendientes de periodos anteriores", default=0)
