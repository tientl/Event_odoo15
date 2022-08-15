# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class HrRecruitmentReport(models.Model):
    _name = "hr.recruitment.report"
    _description = "Recruitment Analysis Report"
    _auto = False
    _rec_name = 'create_date'
    _order = 'create_date desc'

    count = fields.Integer('# New Applicant', group_operator="sum", readonly=True)
    refused = fields.Integer('# Refused', group_operator="sum", readonly=True)
    hired = fields.Integer('# Hired', group_operator="sum", readonly=True)

    create_date = fields.Date('Start Date', readonly=True)
    date_closed = fields.Date('End Date', readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', readonly=True)

    name = fields.Char('Applicant Name', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    medium_id = fields.Many2one('utm.medium', readonly=True)
    process_duration = fields.Integer('Process Duration', group_operator="avg", readonly=True)
    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', string='Refuse Reason', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)

    def _query(self, fields='', from_clause=''):
        select_ = """
                a.id as id,
                1 as count,
                a.create_date,
                a.date_closed,
                a.stage_id,
                a.company_id,
                a.job_id,
                a.refuse_reason_id,
                a.medium_id,
                CASE WHEN a.partner_name IS NOT NULL THEN a.partner_name ELSE a.name END as name,
                CASE WHEN a.active IS FALSE THEN 1 ELSE 0 END as refused,
                CASE WHEN a.date_closed IS NOT NULL THEN 1 ELSE 0 END as hired,
                CASE WHEN a.date_closed IS NOT NULL THEN date_part('day', a.date_closed - a.create_date) ELSE NULL END as process_duration
                %s
        """ % fields

        from_ = """
                hr_applicant a
                %s
        """ % from_clause

        return '(SELECT %s FROM %s)' % (select_, from_)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
