# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from odoo import api, SUPERUSER_ID


def _website_helpdesk_slides_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    teams = env['helpdesk.team'].search([('use_website_helpdesk_slides', '=', True), ('elearning_id', '=', False)])
    elearnings_by_name = teams._create_elearnings_batch([{'name': team.name} for team in teams])
    for team in teams:
        team.elearning_id = elearnings_by_name.get(team.name)
