# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
from collections import defaultdict
from pytz import utc

from odoo import tools, models, fields, api, _
from odoo.addons.web_grid.models.models import END_OF, STEP_BY, START_OF
from odoo.addons.resource.models.resource import make_aware
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression


class AnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line', 'timer.mixin']
    # As this model has his own data merge, avoid to enable the generic data_merge on that model.
    _disable_data_merge = True

    employee_id = fields.Many2one(group_expand="_group_expand_employee_ids")

    # reset amount on copy
    amount = fields.Monetary(copy=False)
    validated = fields.Boolean("Validated line", group_operator="bool_and", store=True, copy=False)
    validated_status = fields.Selection([('draft', 'Draft'), ('validated', 'Validated')], required=True,
        compute='_compute_validated_status')
    user_can_validate = fields.Boolean(compute='_compute_can_validate',
        help="Whether or not the current user can validate/reset to draft the record.")
    is_timesheet = fields.Boolean(
        string="Timesheet Line", compute_sudo=True,
        compute='_compute_is_timesheet', search='_search_is_timesheet',
        help="Set if this analytic line represents a line of timesheet.")

    project_id = fields.Many2one(group_expand="_group_expand_project_ids")
    duration_unit_amount = fields.Float(related="unit_amount", readonly=True, string="Timesheet Init Amount")
    unit_amount_validate = fields.Float(related="unit_amount", readonly=True, string="Timesheet Unit Time")


    display_timer = fields.Boolean(
        compute='_compute_display_timer',
        help="Technical field used to display the timer if the encoding unit is 'Hours'.")
    can_edit = fields.Boolean(compute='_compute_can_edit')

    @api.depends('validated')
    @api.depends_context('uid')
    def _compute_can_edit(self):
        is_approver = self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')
        for line in self:
            line.can_edit = is_approver or not line.validated

    def _compute_display_timer(self):
        other_employee_lines = self.filtered(lambda l: l.employee_id not in self.env.user.employee_ids)
        validated_lines = self.filtered(lambda line: line.validated)
        (other_employee_lines + validated_lines).update({'display_timer': False})
        uom_hour = self.env.ref('uom.product_uom_hour')
        for analytic_line in self - validated_lines - other_employee_lines:
            analytic_line.display_timer = analytic_line.encoding_uom_id == uom_hour and \
                                          self.env.company.timesheet_encode_uom_id == uom_hour

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, range=None, readonly_field=None, orderby=None):
        """
            Override method to manage the group_expand in project_id and employee_id fields
        """
        if not orderby and row_fields:
            orderby = ','.join([r for r in row_fields])

        result = super(AnalyticLine, self).read_grid(row_fields, col_field, cell_field, domain, range, readonly_field, orderby)

        if not self.env.context.get('group_expand', False):
            return result

        res_rows = [row['values'] for row in result['rows']]

        # For the group_expand, we need to have some information :
        #   1) search in domain one rule with one of next conditions :
        #       -   project_id = value
        #       -   employee_id = value
        #   2) search in account.analytic.line if the user timesheeted
        #      in the past 7 days. We reuse the actual domain and
        #      modify it to enforce its validity concerning the dates,
        #      while keeping the restrictions about other fields.
        #      Example: Filter timesheet from my team this week:
        #      [['project_id', '!=', False],
        #       '|',
        #           ['employee_id.timesheet_manager_id', '=', 2],
        #           '|',
        #               ['employee_id.parent_id.user_id', '=', 2],
        #               '|',
        #                   ['project_id.user_id', '=', 2],
        #                   ['user_id', '=', 2]]
        #       '&',
        #           ['date', '>=', '2020-06-01'],
        #           ['date', '<=', '2020-06-07']

        #      Becomes:
        #      [('project_id', '!=', False),
        #       ('date', '>=', datetime.date(2020, 5, 28)),
        #       ('date', '<=', '2020-06-04'),
        #       ['project_id', '!=', False],
        #       '|',
        #           ['employee_id.timesheet_manager_id', '=', 2],
        #           '|',
        #              ['employee_id.parent_id.user_id', '=', 2],
        #              '|',
        #                  ['project_id.user_id', '=', 2],
        #                  ['user_id', '=', 2]]
        #       '&',
        #           ['date', '>=', '1-1-1970'],
        #           ['date', '<=', '1-1-2250']
        #   3) retrieve data and create correctly the grid and rows in result

        today = fields.Date.to_string(fields.Date.today())
        grid_anchor = self.env.context.get('grid_anchor', today)

        last_week = (fields.Datetime.from_string(grid_anchor) - timedelta(days=7)).date()
        domain_search = [
            ('project_id', '!=', False),
            '|',
                ('task_id.active', '=', True),
                ('task_id', '=', False),
            ('date', '>=', last_week),
            ('date', '<=', grid_anchor)
        ]

        domain_project_task = defaultdict(list)

        # check if project_id or employee_id is in domain
        # if not then group_expand return None
        apply_group_expand = False

        for rule in domain:
            if len(rule) == 3:
                name, operator, value = rule
                if name in ['project_id', 'employee_id', 'task_id']:
                    apply_group_expand = True
                elif name == 'date':
                    if operator == '=':
                        operator = '<='
                    value = '1-1-2250' if operator in ['<', '<='] else '1-1-1970'
                domain_search.append([name, operator, value])
                if name in ['project_id', 'task_id']:
                    if operator in ['=', '!='] and value:
                        domain_project_task[name].append(('id', operator, value))
                    elif operator in ['ilike', 'not ilike']:
                        domain_project_task[name].append(('name', operator, value))
            else:
                domain_search.append(rule)
        if not apply_group_expand:
            return result

        # step 2: search timesheets
        timesheets = self.search(domain_search)

        # step 3: retrieve data and create correctly the grid and rows in result
        seen = []  # use to not have duplicated rows
        rows = []
        def read_row_value(row_field, timesheet):
            field_name = row_field.split(':')[0]  # remove all groupby operator e.g. "date:quarter"
            return timesheets._fields[field_name].convert_to_read(timesheet[field_name], timesheet)
        for timesheet in timesheets:
            # check uniq project or task, or employee
            k = tuple(read_row_value(f, timesheet) for f in row_fields)
            if k not in seen:  # check if it's not a duplicated row
                record = {
                    row_field: read_row_value(row_field, timesheet)
                    for row_field in row_fields
                }
                seen.append(k)
                if not any(record == row for row in res_rows):
                    rows.append({'values': record, 'domain': [('id', '=', timesheet.id)]})

        def read_row_fake_value(row_field, project, task):
            if row_field == 'project_id':
                return (project or task.project_id).name_get()[0]
            elif row_field == 'task_id' and task:
                return task.name_get()[0]
            else:
                return False

        if 'project_id' in domain_project_task:
            project_ids = self.env['project.project'].search(domain_project_task['project_id'])
            for project_id in project_ids:
                k = tuple(read_row_fake_value(f, project_id, False) for f in row_fields)
                if k not in seen:  # check if it's not a duplicated row
                    record = {
                        row_field: read_row_fake_value(row_field, project_id, False)
                        for row_field in row_fields
                    }
                    seen.append(k)
                    if not any(record == row for row in res_rows):
                        rows.append({'values': record, 'domain': [('id', '=', -1)]})

        if 'task_id' in domain_project_task:
            task_ids = self.env['project.task'].search(domain_project_task['task_id'])
            for task_id in task_ids:
                k = tuple(read_row_fake_value(f, False, task_id) for f in row_fields)
                if k not in seen:  # check if it's not a duplicated row
                    record = {
                        row_field: read_row_fake_value(row_field, False, task_id)
                        for row_field in row_fields
                    }
                    seen.append(k)
                    if not any(record == row for row in res_rows):
                        rows.append({'values': record, 'domain': [('id', '=', -1)]})

        # _grid_make_empty_cell return a dict, in this dictionary,
        # we need to check if the cell is in the current date,
        # then, we add a key 'is_current' into this dictionary
        # to get the result of this checking.
        grid = [
            [{**self._grid_make_empty_cell(r['domain'], c['domain'], domain), 'is_current': c.get('is_current', False),
              'is_unavailable': c.get('is_unavailable', False)} for c in result['cols']]
            for r in rows]

        if len(rows) > 0:
            # update grid and rows in result
            if len(result['rows']) == 0 and len(result['grid']) == 0:
                result.update(rows=rows, grid=grid)
            else:
                result['rows'].extend(rows)
                result['grid'].extend(grid)

        return result

    def _grid_range_of(self, span, step, anchor, field):
        """
            Override to calculate the unavabilities of the company
        """
        res = super()._grid_range_of(span, step, anchor, field)
        unavailable_days = self._get_unavailable_dates(res.start, res.end)
        # Saving the list of unavailable days to use in method _grid_datetime_is_unavailable
        self.env.context = dict(self.env.context, unavailable_days=unavailable_days)
        return res

    def _get_unavailable_dates(self, start_date, end_date):
        """
        Returns the list of days when the current company is closed (we, or holidays)
        """
        start_dt = datetime(year=start_date.year, month=start_date.month, day=start_date.day)
        end_dt = datetime(year=end_date.year, month=end_date.month, day=end_date.day, hour=23, minute=59, second=59)
        # naive datetimes are made explicit in UTC
        from_datetime, dummy = make_aware(start_dt)
        to_datetime, dummy = make_aware(end_dt)
        # We need to display in grey the unavailable full days
        # We start by getting the availability intervals to avoid false positive with range outside the office hours
        items = self.env.company.resource_calendar_id._work_intervals_batch(from_datetime, to_datetime)[False]
        # get the dates where some work can be done in the interval. It returns a list of sets.
        available_dates = list(map(lambda item: {item[0].date(), item[1].date()}, items))
        # flatten the list of sets to get a simple list of dates and add it to the pile.
        avaibilities = [date for dates in available_dates for date in dates]
        unavailable_days = []
        cur_day = from_datetime
        while cur_day <= to_datetime:
            if not cur_day.date() in avaibilities:
                unavailable_days.append(cur_day.date())
            cur_day = cur_day + timedelta(days=1)
        return set(unavailable_days)


    def _grid_datetime_is_unavailable(self, field, span, step, column_dates):
        """
            :param column_dates: tuple of start/stop dates of a grid column, timezoned in UTC
        """
        unavailable_days = self.env.context.get('unavailable_days')
        if unavailable_days and column_dates in unavailable_days:
            return True

    @api.depends('project_id')
    def _compute_is_timesheet(self):
        for line in self:
            line.is_timesheet = bool(line.project_id)

    def _search_is_timesheet(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('project_id', '!=', False)]
        return [('project_id', '=', False)]

    @api.depends('validated')
    def _compute_validated_status(self):
        for line in self:
            if line.validated:
                line.validated_status = 'validated'
            else:
                line.validated_status = 'draft'

    @api.depends_context('uid')
    def _compute_can_validate(self):
        is_manager = self.user_has_groups('hr_timesheet.group_timesheet_manager')
        is_approver = self.user_has_groups('hr_timesheet.group_hr_timesheet_approver')
        for line in self:
            if is_manager or (is_approver and (
                line.employee_id.timesheet_manager_id.id == self.env.user.id or
                line.employee_id.parent_id.user_id.id == self.env.user.id or
                line.project_id.user_id.id == self.env.user.id or
                line.user_id == self.env.user.id)):
                line.user_can_validate = True
            else:
                line.user_can_validate = False

    def action_validate_timesheet(self):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': None,
                'type': None,  #types: success,warning,danger,info
                'sticky': False,  #True/False will display for few seconds if false
            },
        }
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            notification['params'].update({
                'title': _("You can only validate the timesheets of employees of whom you are the manager or the timesheet approver."),
                'type': 'danger'
            })
            return notification

        analytic_lines = self.filtered_domain(self._get_domain_for_validation_timesheets())
        if not analytic_lines:
            notification['params'].update({
                'title': _("You cannot validate the timesheets from employees that are not part of your team or there are no timesheets to validate."),
                'type': 'danger',
            })
            return notification

        running_analytic_lines = analytic_lines.filtered(lambda l: l.timer_start)
        if running_analytic_lines:
            running_analytic_lines.action_timer_stop()

        analytic_lines.sudo().write({'validated': True})
        if self.env.context.get('use_notification', True):
            notification['params'].update({
                'title': _("The timesheets have successfully been validated."),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            })
            return notification
        return True

    def action_invalidate_timesheet(self):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': None,
                'type': None,
                'sticky': False,
            },
        }
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            raise AccessError(_("You can only reset to draft the timesheets of employees of whom you are the manager or the timesheet approver."))
        #Use the same domain for validation but change validated = False to validated = True
        domain = self._get_domain_for_validation_timesheets(validated=True)
        analytic_lines = self.filtered_domain(domain)
        if not analytic_lines:
            notification['params'].update({
                'title': _('There are no timesheet entries to reset to draft or they have already been invoiced.'),
                'type': 'warning',
            })
            return notification

        analytic_lines.sudo().write({'validated': False})
        if self.env.context.get('use_notification', True):
            notification['params'].update({
                'title': _("The timesheets have successfully been reset to draft."),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            })
            return notification
        return True

    @api.model_create_multi
    def create(self, vals_list):
        analytic_lines = super(AnalyticLine, self).create(vals_list)

        # Check if the user has the correct access to create timesheets
        if not (self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') or self.env.su) and any(line.is_timesheet and line.user_id.id != self.env.user.id for line in analytic_lines):
            raise AccessError(_("You cannot access timesheets that are not yours."))
        return analytic_lines

    def write(self, vals):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            if 'validated' in vals:
                raise AccessError(_('You can only validate the timesheets of employees of whom you are the manager or the timesheet approver.'))
            elif self.filtered(lambda r: r.is_timesheet and r.validated):
                raise AccessError(_('Only a Timesheets Approver or Manager is allowed to modify a validated entry.'))

        return super(AnalyticLine, self).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manager(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') and self.filtered(
                lambda r: r.is_timesheet and r.validated):
            raise AccessError(_('You cannot delete a validated entry. Please, contact your manager or your timesheet approver.'))

    def unlink(self):
        res = super(AnalyticLine, self).unlink()
        self.env['timer.timer'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids)
        ]).unlink()
        return res

    @api.model
    def _apply_timesheet_label(self, view_arch, view_type='form'):
        doc = etree.XML(view_arch)
        encoding_uom = self.env.company.timesheet_encode_uom_id
        # Here, we select only the unit_amount field having no string set to give priority to
        # custom inheretied view stored in database. Even if normally, no xpath can be done on
        # 'string' attribute.
        for node in doc.xpath("//field[@name='unit_amount'][@widget='timesheet_uom' or @widget='timesheet_uom_timer'][not(@string)]"):
            if view_type == 'grid':
                node.set('string', encoding_uom.name)
            else:
                node.set('string', _('%s Spent') % (re.sub(r'[\(\)]', '', encoding_uom.name or '')))
        return etree.tostring(doc, encoding='unicode')

    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        if column_field != 'date' or cell_field != 'unit_amount':
            raise ValueError(
                "{} can only adjust unit_amount (got {}) by date (got {})".format(
                    self._name,
                    cell_field,
                    column_field,
                ))

        additionnal_domain = self._get_adjust_grid_domain(column_value)
        domain = expression.AND([row_domain, additionnal_domain])
        line = self.search(domain)

        day = column_value.split('/')[0]
        if len(line) > 1:  # copy the last line as adjustment
            line[0].copy({
                'name': _('Timesheet Adjustment'),
                column_field: day,
                cell_field: change
            })
        elif len(line) == 1:  # update existing line
            line.write({
                cell_field: line[cell_field] + change
            })
        else:  # create new one
            self.search(row_domain, limit=1).copy({
                'name': _('Timesheet Adjustment'),
                column_field: day,
                cell_field: change,
            })
        return False

    def _get_adjust_grid_domain(self, column_value):
        # span is always daily and value is an iso range
        day = column_value.split('/')[0]
        return [('date', '=', day)]

    def _group_expand_project_ids(self, projects, domain, order):
        """ Group expand by project_ids in grid view

            This group expand allow to add some record grouped by project,
            where the current user (= the current employee) has been
            timesheeted in the past 7 days.
            
            We keep the actual domain and modify it to enforce its validity
            concerning the dates, while keeping the restrictions about other
            fields.
            Example: Filter timesheet from my team this week:
            [['project_id', '!=', False],
             '|',
                 ['employee_id.timesheet_manager_id', '=', 2],
                 '|',
                     ['employee_id.parent_id.user_id', '=', 2],
                     '|',
                         ['project_id.user_id', '=', 2],
                         ['user_id', '=', 2]]
             '&',
                 ['date', '>=', '2020-06-01'],
                 ['date', '<=', '2020-06-07']

            Becomes:
            [('project_id', '!=', False),
             ('date', '>=', datetime.date(2020, 5, 28)),
             ('date', '<=', '2020-06-04'),
             ['project_id', '!=', False],
             '|',
                 ['employee_id.timesheet_manager_id', '=', 2],
                 '|',
                    ['employee_id.parent_id.user_id', '=', 2],
                    '|',
                        ['project_id.user_id', '=', 2],
                        ['user_id', '=', 2]]
             '&',
                 ['date', '>=', '1-1-1970'],
                 ['date', '<=', '1-1-2250']
        """

        today = fields.Date.to_string(fields.Date.today())
        grid_anchor = self.env.context.get('grid_anchor', today)
        last_week = (fields.Datetime.from_string(grid_anchor) - timedelta(days=7)).date()
        domain_search = []

        # We force the date rules to be always met
        for rule in domain:
            if len(rule) == 3 and rule[0] == 'date':
                name, operator, _rule = rule
                if operator == '=':
                    operator = '<='
                domain_search.append((name, operator, '1-1-2250' if operator in ['<', '<='] else '1-1-1970'))
            else:
                domain_search.append(rule)

        domain_search = expression.AND([[('date', '>=', last_week), ('date', '<=', grid_anchor)], domain_search])
        return self.search(domain_search).project_id

    def _group_expand_employee_ids(self, employees, domain, order):
        """ Group expand by employee_ids in grid view

            This group expand allow to add some record by employee, where
            the employee has been timesheeted in a task of a project in the
            past 7 days.

            Example: Filter timesheet from my team this week:
            [['project_id', '!=', False],
             '|',
                 ['employee_id.timesheet_manager_id', '=', 2],
                 '|',
                     ['employee_id.parent_id.user_id', '=', 2],
                     '|',
                         ['project_id.user_id', '=', 2],
                         ['user_id', '=', 2]]
             '&',
                 ['date', '>=', '2020-06-01'],
                 ['date', '<=', '2020-06-07']

            Becomes:
            [('project_id', '!=', False),
             ('date', '>=', datetime.date(2020, 5, 28)),
             ('date', '<=', '2020-06-04'),
             ['project_id', '!=', False],
             '|',
                 ['employee_id.timesheet_manager_id', '=', 2],
                 '|',
                    ['employee_id.parent_id.user_id', '=', 2],
                    '|',
                        ['project_id.user_id', '=', 2],
                        ['user_id', '=', 2]]
             '&',
                 ['date', '>=', '1-1-1970'],
                 ['date', '<=', '1-1-2250']
        """
        today = fields.Date.to_string(fields.Date.today())
        grid_anchor = self.env.context.get('grid_anchor', today)
        last_week = (fields.Datetime.from_string(grid_anchor) - timedelta(days=7)).date()
        domain_search = []

        for rule in domain:
            if len(rule) == 3 and rule[0] == 'date':
                name, operator, _rule = rule
                if operator == '=':
                    operator = '<='
                domain_search.append((name, operator, '1-1-2250' if operator in ['<', '<='] else '1-1-1970'))
            else:
                domain_search.append(rule)
        domain_search = expression.AND([
            [('project_id', '!=', False),
             ('date', '>=', last_week),
             ('date', '<=', grid_anchor)
            ], domain_search])

        group_order = self.env['hr.employee']._order
        if order == group_order:
            order = 'employee_id'
        elif order == tools.reverse_order(group_order):
            order = 'employee_id desc'
        else:
            order = None
        return self.search(domain_search, order=order).employee_id

    # ----------------------------------------------------
    # Timer Methods
    # ----------------------------------------------------

    def action_timer_start(self):
        """ Action start the timer of current timesheet

            * Override method of hr_timesheet module.
        """
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if not self.user_timer_id.timer_start and self.display_timer:
            super(AnalyticLine, self).action_timer_start()

    def _get_last_timesheet_domain(self):
        self.ensure_one()
        return [
            ('id', '!=', self.id),
            ('user_id', '=', self.env.user.id),
            ('project_id', '=', self.project_id.id),
            ('task_id', '=', self.task_id.id),
            ('date', '=', fields.Date.today()),
        ]

    def _add_timesheet_time(self, minutes_spent, try_to_match=False):
        if self.unit_amount == 0 and not minutes_spent:
            # Check if unit_amount equals 0,
            # if yes, then remove the timesheet
            self.unlink()
            return
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
        minutes_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding)
        amount = self.unit_amount + minutes_spent * 60 / 3600
        if not try_to_match or self.name != '/':
            self.write({'unit_amount': amount})
            return

        domain = self._get_last_timesheet_domain()
        last_timesheet_id = self.search(domain, limit=1)
        # If the last timesheet of the day for this project and task has no description,
        # we match both together.
        if last_timesheet_id.name == '/' and not last_timesheet_id.validated:
            last_timesheet_id.unit_amount += amount
            self.unlink()
        else:
            self.write({'unit_amount': amount})

    def action_timer_stop(self, try_to_match=False):
        """ Action stop the timer of the current timesheet
            try_to_match: if true, we try to match with another timesheet which corresponds to the following criteria:
            1. Neither of them has a description
            2. The last one is not validated
            3. Match user, project task, and must be the same day.

            * Override method of hr_timesheet module.
        """
        if self.env.user == self.sudo().user_id:
            # sudo as we can have a timesheet related to a company other than the current one.
            self = self.sudo()
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if self.user_timer_id.timer_start and self.display_timer:
            minutes_spent = super(AnalyticLine, self).action_timer_stop()
            self._add_timesheet_time(minutes_spent, try_to_match)

    def action_timer_unlink(self):
        """ Action unlink the timer of the current timesheet
        """
        if self.env.user == self.sudo().user_id:
            # sudo as we can have a timesheet related to a company other than the current one.
            self = self.sudo()
        self.user_timer_id.unlink()
        if not self.unit_amount:
            self.unlink()

    def _action_interrupt_user_timers(self):
        self.action_timer_stop()

    @api.model
    def get_running_timer(self):
        timer = self.env['timer.timer'].search([
            ('user_id', '=', self.env.user.id),
            ('timer_start', '!=', False),
            ('timer_pause', '=', False),
            ('res_model', '=', self._name),
        ], limit=1)
        if not timer:
            return {}

        # sudo as we can have a timesheet related to a company other than the current one.
        timesheet = self.sudo().browse(timer.res_id)

        running_seconds = (fields.Datetime.now() - timer.timer_start).total_seconds() + timesheet.unit_amount * 3600
        values = {
            'id': timer.res_id,
            'start': running_seconds,
            'project_id': timesheet.project_id.id,
            'task_id': timesheet.task_id.id,
            'description': timesheet.name,
        }
        if timesheet.project_id.company_id not in self.env.companies:
            values.update({
                'readonly': True,
                'project_name': timesheet.project_id.name,
                'task_name': timesheet.task_id.name or '',
            })
        return values

    @api.model
    def get_timer_data(self):
        last_timesheet_ids = self.search([('user_id', '=', self.env.user.id)], limit=5)
        favorite_project = False
        if len(last_timesheet_ids) == 5 and len(last_timesheet_ids.project_id) == 1:
            favorite_project = last_timesheet_ids.project_id.id
        return {
            'step_timer': int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 15)),
            'favorite_project': favorite_project
        }

    @api.model
    def get_rounded_time(self, timer):
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
        rounded_minutes = self._timer_rounding(timer, minimum_duration, rounding)
        return rounded_minutes / 60

    def action_add_time_to_timesheet(self, project, task, seconds):
        if self:
            task = False if not task else task
            if self.task_id.id == task and self.project_id.id == project:
                self.unit_amount += seconds / 3600
                return self.id
        timesheet_id = self.create({
            'project_id': project,
            'task_id': task,
            'unit_amount': seconds / 3600
        })
        return timesheet_id.id

    def action_add_time_to_timer(self, time):
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if not self.user_id.employee_ids:
            raise UserError(_('An employee must be linked to your user to record time.'))
        timer = self.user_timer_id
        if not timer:
            self.action_timer_start()
            timer = self.user_timer_id
        timer.timer_start = min(timer.timer_start - timedelta(0, time), fields.Datetime.now())

    def change_description(self, description):
        if not self.exists():
            return
        if True in self.mapped('validated'):
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        self.write({'name': description})

    def action_change_project_task(self, new_project_id, new_task_id):
        if self.validated:
            raise UserError(_('You cannot use the timer on validated timesheets.'))
        if not self.unit_amount:
            self.write({
                'project_id': new_project_id,
                'task_id': new_task_id,
            })
            return self.id

        new_timesheet = self.create({
            'name': self.name,
            'project_id': new_project_id,
            'task_id': new_task_id,
        })
        self.user_timer_id.res_id = new_timesheet
        return new_timesheet.id

    def _action_open_to_validate_timesheet_view(self, type_view='week'):
        context = {
            'search_default_nonvalidated': True,
            'search_default_my_team_timesheet': True,
            'group_expand': True,
        }
        if (type_view == 'week'):
            context['grid_anchor'] = fields.Date.today() - relativedelta(weeks=1)
        elif type_view == 'month':
            context['grid_range'] = 'month'
            context['grid_anchor'] = fields.Date.today() - relativedelta(months=1)

        name = _('Timesheets to Validate')
        action = self.env["ir.actions.actions"]._for_xml_id("hr_timesheet.act_hr_timesheet_report")
        # The purpose of this view is only to store the view order that can be edited with studio without impacting
        # `act_hr_timesheet_report`. Because `act_hr_timesheet_report` may contain more view_types than the action we will return,
        # editing with studio in the to validate view can cause the loss of some views in `act_hr_timesheet_report`.
        action_validate_id = self.env.ref('timesheet_grid.timesheet_grid_to_validate_action', raise_if_not_found=False)
        if action_validate_id:
            action_validate = action_validate_id.sudo().read(['id', 'views'])[0]
        else:
            action_validate = {'id': action['id']}
        #We want the pivot view to group by week and not by month in weekly mode
        if type_view == 'week':
            pivot_view_id = self.env.ref('timesheet_grid.timesheet_grid_pivot_view_weekly_validate').id
        else:
            pivot_view_id = self.env.ref('hr_timesheet.view_hr_timesheet_line_pivot').id
        # 'views' contain an array of (id, view_name) in the order they will be displayed on screen.
        view_order = [view[1] for view in action_validate.get('views', [])]
        views = [
            [self.env.ref('hr_timesheet.timesheet_view_tree_user').id, 'tree'],
            [self.env.ref('timesheet_grid.timesheet_view_grid_by_employee_validation').id, 'grid'],
            [self.env.ref('timesheet_grid.timesheet_view_form').id, 'form'],
            [pivot_view_id, 'pivot'],
            [self.env.ref('hr_timesheet.view_hr_timesheet_line_graph_all').id, 'graph'],
            [self.env.ref('hr_timesheet.view_kanban_account_analytic_line').id, 'kanban'],
        ]
        views.sort(key=lambda v: view_order.index(v[1]) if v[1] in view_order else 10000)
        action.update({
            'id': action_validate['id'],
            "name": name,
            "display_name": name,
            "views": views,
            "view_mode": 'grid,tree,pivot,graph,kanban',
            "domain": [('is_timesheet', '=', True)],
            "search_view_id": [self.env.ref('timesheet_grid.timesheet_view_search').id, 'search'],
            "context": context,
            "help": '<p class="o_view_nocontent_smiling_face">No timesheets to validate</p>' +
                '<p>Check that your employees correctly filled in their timesheets and that their time is billable</p>',
        })
        return action

    def _get_domain_for_validation_timesheets(self, validated=False):
        """ Get the domain to check if the user can validate/invalidate which timesheets

            2 access rights give access to validate timesheets:

            1. Approver: in this access right, the user can't validate all timesheets,
            he can validate the timesheets where he is the manager or timesheet responsible of the
            employee who is assigned to this timesheets or the user is the owner of the project.
            Furthermore, the user can validate his own timesheets.

            2. Manager (Administrator): with this access right, the user can validate all timesheets.
        """
        domain = [('validated', '=', validated)]

        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            return expression.AND([domain, ['|', ('employee_id.timesheet_manager_id', '=', self.env.user.id),
                      '|', ('employee_id.parent_id.user_id', '=', self.env.user.id),
                      '|', ('project_id.user_id', '=', self.env.user.id), ('user_id', '=', self.env.user.id)]])
        return domain

    def _get_timesheets_to_merge(self):
        return self.filtered(lambda l: l.is_timesheet and not l.validated)

    def action_merge_timesheets(self):
        to_merge = self._get_timesheets_to_merge()

        if len(to_merge) <= 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('There are no timesheet entries to merge.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'name': _('Merge Timesheet Entries'),
            'view_mode': 'form',
            'res_model': 'hr_timesheet.merge.wizard',
            'views': [(self.env.ref('timesheet_grid.timesheet_merge_wizard_view_form').id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': dict(self.env.context, active_ids=to_merge.ids),
        }

    def action_timer_increase(self):
        min_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        self.update({'unit_amount': self.unit_amount + (min_duration / 60)})

    def action_timer_decrease(self):
        min_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        duration = self.unit_amount - (min_duration / 60)
        self.update({'unit_amount': duration if duration > 0 else 0 })
