# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controller
from . import models


def post_install_hook_ensure_team_forms(cr, registry):
    """ Ensure that a form template is generated for each helpdesk team using website helpdesk form.
        Two use cases :
            * After manual desinstall/reinstall of the module we have to regenerate form for concerned teams.
            * When the option is selected on a team for the first time, causing the module to be installed.
              In that case, the override on write/create that invokes the form generation does not apply yet
              and the team does not get its form generated.
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    teams = env['helpdesk.team'].search([('use_website_helpdesk_form', '=', True)])
    teams._ensure_submit_form_view()
