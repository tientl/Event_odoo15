# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import is_html_empty


class WebsiteHelpdesk(http.Controller):

    def get_helpdesk_team_data(self, team, search=None):
        return {'team': team}

    @http.route(['/helpdesk', '/helpdesk/<model("helpdesk.team"):team>'], type='http', auth="public", website=True, sitemap=True)
    def website_helpdesk_teams(self, team=None, **kwargs):
        search = kwargs.get('search')
        # For breadcrumb index: get all team
        teams = request.env['helpdesk.team'].search(['|', '|', ('use_website_helpdesk_form', '=', True), ('use_website_helpdesk_forum', '=', True), ('use_website_helpdesk_slides', '=', True)], order="id asc")
        if not request.env.user.has_group('helpdesk.group_helpdesk_manager'):
            teams = teams.filtered(lambda team: team.website_published)
        if not teams:
            return request.render("website_helpdesk.not_published_any_team")
        result = self.get_helpdesk_team_data(team or teams[0], search=search)
        # For breadcrumb index: get all team
        result['teams'] = teams
        result['is_html_empty'] = is_html_empty
        return request.render("website_helpdesk.team", result)
