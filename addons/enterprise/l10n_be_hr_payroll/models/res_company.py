# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    onss_company_id = fields.Char(string="ONSS Company ID", help="10-digit code given by ONSS")
    onss_registration_number = fields.Char(string="ONSS Registration Number", help="9-digit code given by ONSS")
    dmfa_employer_class = fields.Char(string="DMFA Employer Class", help="3-digit code given by ONSS")
    dmfa_location_unit_ids = fields.One2many('l10n_be.dmfa.location.unit', 'company_id', string="Work address DMFA codes")
    l10n_be_company_number = fields.Char('Company Number')
    l10n_be_revenue_code = fields.Char('Revenue Code')
    l10n_be_ffe_employer_type = fields.Selection([
        ('commercial', 'Employers with industrial or commercial purposes'),
        ('non_commercial', 'Employers without industrial or commercial purposes'),
    ], default='commercial')

    @api.constrains('l10n_be_company_number')
    def _check_l10n_be_company_number(self):
        for company in self.filtered(lambda c: c.l10n_be_company_number):
            number = company.l10n_be_company_number
            if not number.isdecimal() or len(number) != 10 or (not number.startswith('0') and not number.startswith('1')):
                raise ValidationError(_("The company number should contain digits only, starts with a '0' or a '1' and be 10 characters long."))

    def _create_resource_calendar(self):
        """
        Override to set the default calendar to
        38 hours/week for Belgian companies
        """
        be_companies = self.filtered(lambda c: c.country_id.code == "BE" and not c.resource_calendar_id)
        for company in be_companies:
            company.resource_calendar_id = self.env['resource.calendar'].create({
                'name': _('Standard 38 hours/week'),
                'company_id': company.id,
                'hours_per_day': 7.6,
                'full_time_required_hours': 38.0,
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
                ],
            }).id
        super(ResCompany, self - be_companies)._create_resource_calendar()

    def _get_ffe_contribution_rate(self, worker_count):
        # Fond de fermeture d'entreprise
        # https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/special_contributions/other_specialcontributions/basiccontributions_closingcompanyfunds.html
        self.ensure_one()
        if self.l10n_be_ffe_employer_type == 'commercial':
            if worker_count < 20:
                rate = 0.0007
            else:
                rate = 0.0013
        else:
            rate = 0.0002
        return rate
