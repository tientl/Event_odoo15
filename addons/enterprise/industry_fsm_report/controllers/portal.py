# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers import portal

import binascii


class CustomerPortal(portal.CustomerPortal):
    @http.route(['/my/task/<int:task_id>/worksheet',
                 '/my/task/<int:task_id>/worksheet/<string:source>'], type='http', auth="public", website=True)
    def portal_my_worksheet(self, task_id, access_token=None, source=False, report_type=None, download=False, message=False, **kw):

        try:
            task_sudo = self._document_check_access('project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=task_sudo, report_type=report_type, report_ref='industry_fsm_report.task_custom_report', download=download)

        worksheet_map = {}
        if task_sudo.worksheet_template_id:
            x_model = task_sudo.worksheet_template_id.model_id.model
            worksheet = request.env[x_model].sudo().search([('x_project_task_id', '=', task_sudo.id)], limit=1, order="create_date DESC")  # take the last one
            worksheet_map[task_sudo.id] = worksheet

        return request.render("industry_fsm_report.portal_my_worksheet", {'worksheet_map': worksheet_map, 'task': task_sudo, 'message': message, 'source': source})


    @http.route(['/my/task/<int:task_id>/worksheet/sign/<string:source>'], type='json', auth="public", website=True)
    def portal_worksheet_sign(self, task_id, access_token=None, source=False, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            task_sudo = self._document_check_access('project.task', task_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid Task.')}

        if not task_sudo.has_to_be_signed():
            return {'error': _('The worksheet is not in a state requiring customer signature.')}
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            task_sudo.write({
                'worksheet_signature': signature,
                'worksheet_signed_by': name,
            })

        except (TypeError, binascii.Error):
            return {'error': _('Invalid signature data.')}

        pdf = request.env.ref('industry_fsm_report.task_custom_report').with_user(SUPERUSER_ID)._render_qweb_pdf([task_sudo.id])[0]
        task_sudo.message_post(body=_('The worksheet has been signed'), attachments=[('%s.pdf' % task_sudo.name, pdf)])

        query_string = '&message=sign_ok'
        return {
            'force_refresh': True,
            'redirect_url': task_sudo.get_portal_url(suffix='/worksheet/%s' % source, query_string=query_string),
        }
