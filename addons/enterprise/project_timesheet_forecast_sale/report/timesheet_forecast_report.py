# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools, fields, models

from psycopg2 import sql

class TimesheetForecastReport(models.Model):
    _inherit = "project.timesheet.forecast.report.analysis"

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            SELECT
                d::date AS entry_date,
                F.employee_id AS employee_id,
                F.task_id AS task_id,
                F.project_id AS project_id,
                F.user_id AS user_id,
                0.0 AS effective_hours,
                F.allocated_hours / NULLIF(F.working_days_count, 0) AS planned_hours,
                F.allocated_hours / NULLIF(F.working_days_count, 0) AS difference,
                'forecast' AS line_type,
                F.id AS id,
                SOL.id AS sale_line_id,
                SOL.order_id AS sale_order_id
            FROM generate_series(
                (SELECT min(start_datetime) FROM planning_slot)::date,
                (SELECT max(end_datetime) FROM planning_slot)::date,
                '1 day'::interval
            ) d
                LEFT JOIN planning_slot F ON d::date >= F.start_datetime::date AND d::date <= F.end_datetime::date
                LEFT JOIN hr_employee E ON F.employee_id = E.id
                LEFT JOIN resource_resource R ON E.resource_id = R.id
                LEFT JOIN sale_order_line SOL ON SOL.id = F.order_line_id
            WHERE
                EXTRACT(ISODOW FROM d.date) IN (
                    SELECT A.dayofweek::integer+1 FROM resource_calendar_attendance A WHERE A.calendar_id = R.calendar_id
                )
        ) UNION (
            SELECT
                A.date AS entry_date,
                E.id AS employee_id,
                A.task_id AS task_id,
                A.project_id AS project_id,
                A.user_id AS user_id,
                A.unit_amount / UOM.factor * HOUR_UOM.factor AS effective_hours,
                0.0 AS planned_hours,
                - A.unit_amount / UOM.factor * HOUR_UOM.factor AS difference,
                'timesheet' AS line_type,
                -A.id AS id,
                A.so_line AS sale_line_id,
                A.order_id AS sale_order_id
            FROM account_analytic_line A
                LEFT JOIN hr_employee E ON A.employee_id = E.id
                LEFT JOIN uom_uom UOM ON A.product_uom_id = UOM.id,
                (
                    SELECT
                        U.factor
                    FROM uom_uom U
                    WHERE U.id = %s
                ) HOUR_UOM
            WHERE A.project_id IS NOT NULL
                AND A.employee_id = E.id
        """ % (self.env.ref('uom.product_uom_hour').id,)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            ))
