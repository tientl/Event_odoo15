# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, models, _

class L10nBeIndividualAccountWizard(models.TransientModel):
    _inherit = 'l10n_be.individual.account.wizard'

    @api.model
    def _payroll_documents_enabled(self):
        company = self.env.company
        return company.documents_payroll_folder_id and company.documents_hr_settings

    def _post_process_files(self, files):
        super()._post_process_files(files)
        if not self._payroll_documents_enabled():
            return
        self.env['documents.document'].create([{
            'owner_id': employee.user_id.id,
            'datas': base64.encodebytes(data),
            'name': filename,
            'folder_id': employee.company_id.documents_payroll_folder_id.id,
            'res_model': 'hr.payslip',  # Security Restriction to payroll managers
        } for employee, filename, data in files])

    def print_report(self):
        self.ensure_one()
        if not self._payroll_documents_enabled():
            return super().print_report()
        pdf_files = self._generate_files(self.env.company)
        template = self.env.ref('documents_l10n_be_hr_payroll.mail_template_individual_account', raise_if_not_found=False)
        if template:
            for employee, dummy, dummy in pdf_files:
                template.send_mail(employee.id, notif_layout='mail.mail_notification_light')

        if pdf_files:
            dummy, dummy = self._process_files(pdf_files, default_filename=_('Individual Accounts PDF') + '- %s.zip' % self.year, post_process=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _('The individual account sheets have been posted in the employee portal.'),
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'message': _('There is no individual account to post for this period.'),
            }
        }
