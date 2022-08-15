# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime

from dateutil import relativedelta
from collections import defaultdict
from odoo import api, Command, fields, models, _
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.web.controllers.main import clean_action
from odoo.osv import expression


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _inherit = ['mail.alias.mixin', 'mail.thread', 'rating.parent.mixin']
    _description = "Helpdesk Team"
    _order = 'sequence,name'
    _rating_satisfaction_days = 30  # include only last 30 days to compute satisfaction

    _sql_constraints = [('not_portal_show_rating_if_not_use_rating',
                         'check (portal_show_rating = FALSE OR use_rating = TRUE)',
                         'Cannot show ratings in portal if not using them'), ]

    def _default_stage_ids(self):
        default_stage = self.env['helpdesk.stage'].search([('name', '=', _('New'))], limit=1)
        if not default_stage:
            default_stage = self.env['helpdesk.stage'].create({
                'name': _("New"),
                'sequence': 0,
                'template_id': self.env.ref('helpdesk.new_ticket_request_email_template', raise_if_not_found=False).id or None
            })
        return [(4, default_stage.id)]

    def _default_domain_member_ids(self):
        return [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)]

    name = fields.Char('Helpdesk Team', required=True, translate=True)
    description = fields.Html('About Team', translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    sequence = fields.Integer("Sequence", default=10)
    color = fields.Integer('Color Index', default=1)
    privacy = fields.Selection([
        ('user', 'All Users'),
        ('invite', 'Invited Users')],
        string="Users Assign", default="user")

    stage_ids = fields.Many2many(
        'helpdesk.stage', relation='team_stage_rel', string='Stages',
        default=_default_stage_ids,
        help="Stages the team will use. This team's tickets will only be able to be in these stages.")
    assign_method = fields.Selection([
        ('manual', 'Manual'),
        ('randomly', 'Random'),
        ('balanced', 'Balanced')], string='Assignment Method', default='manual',
        required=True, help='Automatic assignment method for new tickets:\n'
             '\tManually: manual\n'
             '\tRandomly: randomly but everyone gets the same amount\n'
             '\tBalanced: to the person with the least amount of open tickets')
    member_ids = fields.Many2many('res.users', string='Team Members', domain=lambda self: self._default_domain_member_ids(), default=lambda self: self.env.user, required=True)
    visibility_member_ids = fields.Many2many('res.users', 'helpdesk_visibility_team', string='Team Visibility', domain=lambda self: self._default_domain_member_ids(),
        help="Team Members to whom this team will be visible. Keep empty for everyone to see this team.")
    ticket_ids = fields.One2many('helpdesk.ticket', 'team_id', string='Tickets')

    use_alias = fields.Boolean('Email Alias', default=True)
    has_external_mail_server = fields.Boolean(compute='_compute_has_external_mail_server')
    allow_portal_ticket_closing = fields.Boolean('Closure by Customers', help="Allow customers to close their tickets")
    use_website_helpdesk_form = fields.Boolean('Website Form')
    use_website_helpdesk_livechat = fields.Boolean('Live Chat',
        help="In Channel: You can create a new ticket by typing /helpdesk [ticket title]. You can search ticket by typing /helpdesk_search [Keyword1],[Keyword2],.")
    use_website_helpdesk_forum = fields.Boolean('Community Forum')
    use_website_helpdesk_slides = fields.Boolean('Enable eLearning')
    use_helpdesk_timesheet = fields.Boolean(
        'Timesheets', compute='_compute_use_helpdesk_timesheet',
        store=True, readonly=False, help="This requires to have project module installed.")
    use_helpdesk_sale_timesheet = fields.Boolean(
        'Time Billing', compute='_compute_use_helpdesk_sale_timesheet', store=True,
        readonly=False, help="Reinvoice the time spent on ticket through tasks.")
    use_credit_notes = fields.Boolean('Refunds')
    use_coupons = fields.Boolean('Coupons')
    use_fsm = fields.Boolean('Field Service', help='Convert tickets into Field Service tasks')
    use_product_returns = fields.Boolean('Returns')
    use_product_repairs = fields.Boolean('Repairs')
    use_twitter = fields.Boolean('Twitter')
    use_rating = fields.Boolean('Customer Ratings')
    portal_show_rating = fields.Boolean(
        'Public Rating', compute='_compute_portal_show_rating', store=True,
        readonly=False)
    use_sla = fields.Boolean('SLA Policies')
    upcoming_sla_fail_tickets = fields.Integer(string='Upcoming SLA Fail Tickets', compute='_compute_upcoming_sla_fail_tickets')
    unassigned_tickets = fields.Integer(string='Unassigned Tickets', compute='_compute_unassigned_tickets')
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Hours',
        default=lambda self: self.env.company.resource_calendar_id, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Working hours used to determine the deadline of SLA Policies.")
    open_ticket_count = fields.Integer("# Open Tickets", compute='_compute_open_ticket_count')
    sla_policy_count = fields.Integer("# SLA Policy", compute='_compute_sla_policy_count')
    # auto close ticket
    auto_close_ticket = fields.Boolean('Automatic Closing')
    auto_close_day = fields.Integer('Inactive Period(days)',
        default=7,
        help="Period of inactivity after which tickets will be automatically closed.")
    from_stage_ids = fields.Many2many('helpdesk.stage', relation='team_stage_auto_close_from_rel',
        string='In Stages',
        domain="[('id', 'in', stage_ids)]",
        help="Inactive tickets in these stages will be automatically closed. Leave empty to take into account all the stages from the team.")
    to_stage_id = fields.Many2one('helpdesk.stage',
        string='Move to Stage',
        compute="_compute_assign_stage_id", readonly=False, store=True,
        domain="[('id', 'in', stage_ids)]",
        help="Stage to which inactive tickets will be automatically moved once the period of inactivity is reached.")
    display_alias_name = fields.Char(string='Alias email', compute='_compute_display_alias_name')

    @api.depends('auto_close_ticket', 'stage_ids')
    def _compute_assign_stage_id(self):
        stages_dict = {stage['id']: 1 if stage['is_close'] else 2 for stage in self.env['helpdesk.stage'].search_read([('id', 'in', self.stage_ids.ids), '|', ('is_close', '=', True), ('fold', '=', True)], ['id', 'is_close'])}
        for team in self:
            stage_ids = sorted([
                (val, stage_id) for stage_id, val in stages_dict.items() if stage_id in team.stage_ids.ids
            ])
            team.to_stage_id = stage_ids[0][1] if stage_ids else team.stage_ids.ids[-1]

    @api.depends('alias_name', 'alias_domain')
    def _compute_display_alias_name(self):
        for team in self:
            alias_name = ''
            if team.alias_name and team.alias_domain:
                alias_name = "%s@%s" % (team.alias_name, team.alias_domain)
            team.display_alias_name = alias_name

    def _compute_has_external_mail_server(self):
        self.has_external_mail_server = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_external_email_server')

    def _compute_upcoming_sla_fail_tickets(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('team_id', 'in', self.ids),
            ('sla_deadline', '!=', False),
            ('sla_deadline', '<=', fields.Datetime.to_string((datetime.date.today() + relativedelta.relativedelta(days=1)))),
        ], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.upcoming_sla_fail_tickets = mapped_data.get(team.id, 0)

    def _compute_unassigned_tickets(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([('user_id', '=', False), ('team_id', 'in', self.ids), ('stage_id.is_close', '!=', True)], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.unassigned_tickets = mapped_data.get(team.id, 0)

    def _compute_open_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('team_id', 'in', self.ids), ('stage_id.is_close', '=', False)
        ], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.open_ticket_count = mapped_data.get(team.id, 0)

    def _compute_sla_policy_count(self):
        sla_data = self.env['helpdesk.sla'].read_group([('team_id', 'in', self.ids)], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in sla_data)
        for team in self:
            team.sla_policy_count = mapped_data.get(team.id, 0)

    @api.depends('use_rating')
    def _compute_portal_show_rating(self):
        without_rating = self.filtered(lambda t: not t.use_rating)
        without_rating.update({'portal_show_rating': False})

    @api.onchange('use_alias', 'name')
    def _onchange_use_alias(self):
        if not self.use_alias:
            self.alias_name = False

    @api.depends('use_helpdesk_sale_timesheet')
    def _compute_use_helpdesk_timesheet(self):
        sale_timesheet = self.filtered('use_helpdesk_sale_timesheet')
        sale_timesheet.update({'use_helpdesk_timesheet': True})

    @api.depends('use_helpdesk_timesheet')
    def _compute_use_helpdesk_sale_timesheet(self):
        without_timesheet = self.filtered(lambda t: not t.use_helpdesk_timesheet)
        without_timesheet.update({'use_helpdesk_sale_timesheet': False})

    # ------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(HelpdeskTeam, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        teams.sudo()._check_sla_group()
        teams.sudo()._check_modules_to_install()
        if teams.filtered(lambda x: x.auto_close_ticket):
            teams._update_cron()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return teams

    def write(self, vals):
        if 'privacy' in vals and vals['privacy'] == 'user':
            vals['visibility_member_ids'] = [Command.clear()]
        result = super(HelpdeskTeam, self).write(vals)
        if 'active' in vals:
            self.with_context(active_test=False).mapped('ticket_ids').write({'active': vals['active']})
        if 'use_sla' in vals:
            self.sudo()._check_sla_group()
        self.sudo()._check_modules_to_install()
        if 'auto_close_ticket' in vals:
            self._update_cron()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return result

    def unlink(self):
        stages = self.mapped('stage_ids').filtered(lambda stage: stage.team_ids <= self)  # remove stages that only belong to team in self
        stages.unlink()
        return super(HelpdeskTeam, self).unlink()

    @api.model
    def _update_cron(self):
        cron = self.env.ref('helpdesk.ir_cron_auto_close_ticket', raise_if_not_found=False)
        cron and cron.toggle(model=self._name, domain=[
            ('auto_close_ticket', '=', True),
            ('auto_close_day', '>', 0),
        ])

    def _check_sla_group(self):
        sla_teams = self.filtered_domain([('use_sla', '=', True)])
        non_sla_teams = self - sla_teams
        if sla_teams and not self.user_has_groups('helpdesk.group_use_sla'):
            self.env.ref('helpdesk.group_helpdesk_user').write({
                'implied_ids': [(4, self.env.ref('helpdesk.group_use_sla').id)]
            })
        if sla_teams:
            self.env['helpdesk.sla'].with_context(active_test=False).search([
                ('team_id', 'in', sla_teams.ids), ('active', '=', False),
            ]).write({'active': True})
        if non_sla_teams:
            self.env['helpdesk.sla'].search([('team_id', 'in', non_sla_teams.ids)]).write({'active': False})
            if not self.search([('use_sla', '=', True)], limit=1):
                self.env.ref('helpdesk.group_helpdesk_user').write({
                    'implied_ids': [(3, self.env.ref('helpdesk.group_use_sla').id)]
                })
                self.env.ref('helpdesk.group_use_sla').write({'users': [(5, 0, 0)]})

    @api.model
    def _get_field_modules(self):
        # mapping of field names to module names
        return {
            'use_website_helpdesk_form': 'website_helpdesk_form',
            'use_website_helpdesk_livechat': 'website_helpdesk_livechat',
            'use_website_helpdesk_forum': 'website_helpdesk_forum',
            'use_website_helpdesk_slides': 'website_helpdesk_slides',
            'use_helpdesk_timesheet': 'helpdesk_timesheet',
            'use_helpdesk_sale_timesheet': 'helpdesk_sale_timesheet',
            'use_credit_notes': 'helpdesk_account',
            'use_product_returns': 'helpdesk_stock',
            'use_product_repairs': 'helpdesk_repair',
            'use_coupons': 'helpdesk_sale_coupon',
            'use_fsm': 'helpdesk_fsm',
        }

    def _check_modules_to_install(self):
        # determine the modules to be installed
        expected = [
            mname
            for fname, mname in self._get_field_modules().items()
            if any(team[fname] for team in self)
        ]
        modules = self.env['ir.module.module']
        if expected:
            STATES = ('installed', 'to install', 'to upgrade')
            modules = modules.search([('name', 'in', expected)])
            modules = modules.filtered(lambda module: module.state not in STATES)

        if modules:
            modules.button_immediate_install()

        # just in case we want to do something if we install a module. (like a refresh ...)
        return bool(modules)

    # ------------------------------------------------------------
    # Mail Alias Mixin
    # ------------------------------------------------------------

    def _alias_get_creation_values(self):
        values = super(HelpdeskTeam, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('helpdesk.ticket').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['team_id'] = self.id
            if not self.alias_name:
                values['alias_name'] = self.name.replace(' ', '-')
        return values

    # ------------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------------

    @api.model
    def retrieve_dashboard(self):
        domain = [('user_id', '=', self.env.uid)]
        group_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        list_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        #TODO: remove SLA calculations if user_uses_sla is false.
        user_uses_sla = self.user_has_groups('helpdesk.group_use_sla') and\
            bool(self.env['helpdesk.team'].search([('use_sla', '=', True)], limit=1))

        if user_uses_sla:
            group_fields.insert(1, 'sla_deadline:year')
            group_fields.insert(2, 'sla_deadline:hour')
            group_fields.insert(3, 'sla_reached_late')
            list_fields.insert(1, 'sla_deadline')
            list_fields.insert(2, 'sla_reached_late')

        HelpdeskTicket = self.env['helpdesk.ticket']
        tickets = HelpdeskTicket.search_read(expression.AND([domain, [('stage_id.is_close', '=', False)]]), ['sla_deadline', 'open_hours', 'sla_reached_late', 'priority'])

        result = {
            'helpdesk_target_closed': self.env.user.helpdesk_target_closed,
            'helpdesk_target_rating': self.env.user.helpdesk_target_rating,
            'helpdesk_target_success': self.env.user.helpdesk_target_success,
            'today': {'count': 0, 'rating': 0, 'success': 0},
            '7days': {'count': 0, 'rating': 0, 'success': 0},
            'my_all': {'count': 0, 'hours': 0, 'failed': 0},
            'my_high': {'count': 0, 'hours': 0, 'failed': 0},
            'my_urgent': {'count': 0, 'hours': 0, 'failed': 0},
            'show_demo': not bool(HelpdeskTicket.search([], limit=1)),
            'rating_enable': False,
            'success_rate_enable': user_uses_sla
        }

        def _is_sla_failed(data):
            deadline = data.get('sla_deadline')
            sla_deadline = fields.Datetime.now() > deadline if deadline else False
            return sla_deadline or data.get('sla_reached_late')

        def add_to(ticket, key="my_all"):
            result[key]['count'] += 1
            result[key]['hours'] += ticket['open_hours']
            if _is_sla_failed(ticket):
                result[key]['failed'] += 1

        for ticket in tickets:
            add_to(ticket, 'my_all')
            if ticket['priority'] == '2':
                add_to(ticket, 'my_high')
            if ticket['priority'] == '3':
                add_to(ticket, 'my_urgent')

        dt = fields.Date.context_today(self)
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)], list_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['today']['count'] += ticket['__count']
            if not _is_sla_failed(ticket):
                result['today']['success'] += ticket['__count']

        dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)], list_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['7days']['count'] += ticket['__count']
            if not _is_sla_failed(ticket):
                result['7days']['success'] += ticket['__count']

        result['today']['success'] = fields.Float.round(result['today']['success'] * 100 / (result['today']['count'] or 1), 2)
        result['7days']['success'] = fields.Float.round(result['7days']['success'] * 100 / (result['7days']['count'] or 1), 2)
        result['my_all']['hours'] = fields.Float.round(result['my_all']['hours'] / (result['my_all']['count'] or 1), 2)
        result['my_high']['hours'] = fields.Float.round(result['my_high']['hours'] / (result['my_high']['count'] or 1), 2)
        result['my_urgent']['hours'] = fields.Float.round(result['my_urgent']['hours'] / (result['my_urgent']['count'] or 1), 2)

        if self.env['helpdesk.team'].search([('use_rating', '=', True)], limit=1):
            result['rating_enable'] = True
            # rating of today
            domain = [('user_id', '=', self.env.uid)]
            dt = fields.Date.today()
            tickets = self.env['helpdesk.ticket'].search(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)])
            activity = tickets.rating_get_grades()
            total_rating = self._compute_activity_avg(activity)
            total_activity_values = sum(activity.values())
            # In the 2 formula's below, we need to multiply at the end by (100 / MAX_SCORING)
            # where MAX_SCORING is defined in _compute_activity_avg as the value for a "great" rating.
            team_satisfaction = fields.Float.round((total_rating / total_activity_values if total_activity_values else 0), 2) * 20
            if team_satisfaction:
                result['today']['rating'] = team_satisfaction

            # rating of last 7 days (6 days + today)
            dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
            tickets = self.env['helpdesk.ticket'].search(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)])
            activity = tickets.rating_get_grades()
            total_rating = self._compute_activity_avg(activity)
            total_activity_values = sum(activity.values())
            team_satisfaction_7days = fields.Float.round((total_rating / total_activity_values if total_activity_values else 0), 2) * 20
            if team_satisfaction_7days:
                result['7days']['rating'] = team_satisfaction_7days
        return result

    def _action_view_rating(self, period=False, only_my_closed=False):
        """ return the action to see all the rating about the tickets of the Team
            :param period: either 'today' or 'seven_days' to include (or not) the tickets closed in this period
            :param only_my_closed: True will include only the ticket of the current user in a closed stage
        """
        domain = [('team_id', 'in', self.ids)]

        if period == 'seven_days':
            domain += [('close_date', '>=', fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6))))]
        elif period == 'today':
            domain += [('close_date', '>=', fields.Datetime.to_string(datetime.date.today()))]

        if only_my_closed:
            domain += [('user_id', '=', self._uid), ('stage_id.is_close', '=', True)]

        ticket_ids = self.env['helpdesk.ticket'].search(domain).ids
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.rating_rating_action_helpdesk")
        action = clean_action(action, self.env)
        action['domain'] = [('res_id', 'in', ticket_ids), ('rating', '!=', -1), ('res_model', '=', 'helpdesk.ticket'), ('consumed', '=', True)]
        return action

    def action_view_ticket(self):
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_team")
        action['display_name'] = self.name
        return action

    @api.model
    def action_view_rating_today(self):
        #  call this method of on click "Customer Rating" button on dashbord for today rating of teams tickets
        return self.search([('member_ids', 'in', self._uid)])._action_view_rating(period='today', only_my_closed=True)

    @api.model
    def action_view_rating_7days(self):
        #  call this method of on click "Customer Rating" button on dashbord for last 7days rating of teams tickets
        return self.search([('member_ids', 'in', self._uid)])._action_view_rating(period='seven_days', only_my_closed=True)

    def action_view_all_rating(self):
        """ return the action to see all the rating about the all sort of activity of the team (tickets) """
        return self._action_view_rating()

    def action_view_team_rating(self):
        self.ensure_one()
        action = self._action_view_rating()
        rating_ids = self.rating_ids.filtered(lambda x: x.rating >= 1 and x.consumed).ids
        if len(rating_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': rating_ids[0],
                'views': [(False, 'form')],
            })
        return action

    def action_view_open_ticket_view(self):
        action = self.action_view_ticket()
        action.update({
            'display_name': _("Tickets"),
            'domain': [('team_id', '=', self.id), ('stage_id.is_close', '=', False)],
        })
        return action

    def action_view_sla_policy(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_sla_action")
        if self.sla_policy_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.env['helpdesk.sla'].search([('team_id', '=', self.id)], limit=1).id,
                'views': [(False, 'form')],
            })
        action.update({
            'context': {'default_team_id': self.id},
            'domain': [('team_id', '=', self.id)],
        })
        return action

    @api.model
    def _compute_activity_avg(self, activity):
        # compute average base on all rating value
        # like: 5 great, 3 okey, 1 bad
        # great = 5, okey = 3, bad = 0
        # (5*5) + (2*3) + (1*0) = 60 / 8 (nuber of activity for rating)
        great = activity['great'] * 5.00
        okey = activity['okay'] * 3.00
        bad = activity['bad'] * 0.00
        return great + okey + bad

    def _determine_user_to_assign(self):
        """ Get a dict with the user (per team) that should be assign to the nearly created ticket according to the team policy
            :returns a mapping of team identifier with the "to assign" user (maybe an empty record).
            :rtype : dict (key=team_id, value=record of res.users)
        """
        result = dict.fromkeys(self.ids, self.env['res.users'])
        for team in self:
            member_ids = sorted(team.member_ids.ids)
            if team.assign_method == 'randomly':  # randomly means new tickets get uniformly distributed
                last_assigned_user = self.env['helpdesk.ticket'].search([('team_id', '=', team.id)], order='create_date desc, id desc', limit=1).user_id
                index = 0
                if last_assigned_user and last_assigned_user.id in member_ids:
                    previous_index = member_ids.index(last_assigned_user.id)
                    index = (previous_index + 1) % len(member_ids)
                result[team.id] = self.env['res.users'].browse(member_ids[index])
            elif team.assign_method == 'balanced':  # find the member with the least open ticket
                ticket_count_data = self.env['helpdesk.ticket'].read_group([('stage_id.is_close', '=', False), ('user_id', 'in', member_ids), ('team_id', '=', team.id)], ['user_id'], ['user_id'])
                open_ticket_per_user_map = dict.fromkeys(member_ids, 0)  # dict: user_id -> open ticket count
                open_ticket_per_user_map.update((item['user_id'][0], item['user_id_count']) for item in ticket_count_data)
                result[team.id] = self.env['res.users'].browse(min(open_ticket_per_user_map, key=open_ticket_per_user_map.get))
        return result

    def _determine_stage(self):
        """ Get a dict with the stage (per team) that should be set as first to a created ticket
            :returns a mapping of team identifier with the stage (maybe an empty record).
            :rtype : dict (key=team_id, value=record of helpdesk.stage)
        """
        result = dict.fromkeys(self.ids, self.env['helpdesk.stage'])
        for team in self:
            result[team.id] = self.env['helpdesk.stage'].search([('team_ids', 'in', team.id)], order='sequence', limit=1)
        return result

    def _get_closing_stage(self):
        """
            Return the first closing kanban stage or the last stage of the pipe if none
        """
        closed_stage = self.stage_ids.filtered(lambda stage: stage.is_close)
        if not closed_stage:
            closed_stage = self.stage_ids[-1]
        return closed_stage

    def _cron_auto_close_tickets(self):
        teams = self.env['helpdesk.team'].search_read(
            domain=[
                ('auto_close_ticket', '=', True),
                ('auto_close_day', '>', 0),
                ('to_stage_id', '!=', False)],
            fields=[
                'id',
                'auto_close_day',
                'from_stage_ids',
                'to_stage_id']
        )
        teams_dict = defaultdict(dict)  # key: team_id, values: the remaining result of the search_group
        today = fields.datetime.today()
        for team in teams:
            # Compute the threshold_date
            team['threshold_date'] = today - relativedelta.relativedelta(days=team['auto_close_day'])
            teams_dict[team['id']] = team
        tickets_domain = [('stage_id.is_close', '=', False), ('team_id', 'in', list(teams_dict.keys()))]
        tickets = self.env['helpdesk.ticket'].search(tickets_domain)

        def is_inactive_ticket(ticket):
            team = teams_dict[ticket.team_id.id]
            is_write_date_ok = ticket.write_date <= team['threshold_date']
            if team['from_stage_ids']:
                is_stage_ok = ticket.stage_id.id in team['from_stage_ids']
            else:
                is_stage_ok = not ticket.stage_id.is_close
            return is_write_date_ok and is_stage_ok

        inactive_tickets = tickets.filtered(is_inactive_ticket)
        for ticket in inactive_tickets:
            # to_stage_id is mandatory in the view but not in the model so it is better to test it.
            if teams_dict[ticket.team_id.id]['to_stage_id']:
                ticket.write({'stage_id': teams_dict[ticket.team_id.id]['to_stage_id'][0]})

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if len(self) == 1:
            optional_subtypes = [('use_credit_notes', self.env.ref('helpdesk.mt_team_ticket_refund_posted')),
                                 ('use_product_returns', self.env.ref('helpdesk.mt_team_ticket_return_done')),
                                 ('use_product_repairs', self.env.ref('helpdesk.mt_team_ticket_repair_done'))]
            for field, subtype in optional_subtypes:
                if not self[field] and subtype in res:
                    res -= subtype
        return res

class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _description = 'Helpdesk Stage'
    _order = 'sequence, id'

    def _default_team_ids(self):
        team_id = self.env.context.get('default_team_id')
        if team_id:
            return [(4, team_id, 0)]

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer('Sequence', default=10)
    is_close = fields.Boolean(
        'Closing Stage',
        help='Tickets in this stage are considered as done. This is used notably when '
             'computing SLAs and KPIs on tickets.')
    fold = fields.Boolean(
        'Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    team_ids = fields.Many2many(
        'helpdesk.team', relation='team_stage_rel', string='Helpdesk Teams',
        default=_default_team_ids,
        help='Specific team that uses this stage. Other teams will not be able to see or use this stage.')
    template_id = fields.Many2one(
        'mail.template', 'Email Template',
        domain="[('model', '=', 'helpdesk.ticket')]",
        help="Automated email sent to the ticket's customer when the ticket reaches this stage.")
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True,
        help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.')
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready'), translate=True, required=True,
        help='Override the default value displayed for the done state for kanban selection, when the task or issue is in that stage.')
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True,
        help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.')
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        res = self.env['helpdesk.ticket'].read_group(
            [('stage_id', 'in', self.ids)],
            ['stage_id'], ['stage_id'])
        stage_data = {r['stage_id'][0]: r['stage_id_count'] for r in res}
        for stage in self:
            stage.ticket_count = stage_data.get(stage.id, 0)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['helpdesk.ticket'].search([('stage_id', 'in', self.ids)]).write({'active': False})
        return super(HelpdeskStage, self).write(vals)

    def unlink(self):
        stages = self
        default_team_id = self.env.context.get('default_team_id')
        if default_team_id:
            shared_stages = self.filtered(lambda x: len(x.team_ids) > 1 and default_team_id in x.team_ids.ids)
            tickets = self.env['helpdesk.ticket'].with_context(active_test=False).search([('team_id', '=', default_team_id), ('stage_id', 'in', self.ids)])
            if shared_stages and not tickets:
                shared_stages.write({'team_ids': [(3, default_team_id)]})
                stages = self.filtered(lambda x: x not in shared_stages)
        return super(HelpdeskStage, stages).unlink()

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('stage_id', 'in', self.ids)],
            'context': {
                'default_stage_id': self.id,
            },
        })
        return action


class HelpdeskSLA(models.Model):
    _name = "helpdesk.sla"
    _order = "name"
    _description = "Helpdesk SLA Policies"

    name = fields.Char(required=True, index=True, translate=True)
    description = fields.Html('SLA Policy Description', translate=True)
    active = fields.Boolean('Active', default=True)
    team_id = fields.Many2one('helpdesk.team', 'Helpdesk Team', required=True)
    ticket_type_id = fields.Many2one(
        'helpdesk.ticket.type', "Type",
        help="Only apply the SLA to a specific ticket type. If left empty it will apply to all types.")
    tag_ids = fields.Many2many(
        'helpdesk.tag', string='Tags',
        help="Only apply the SLA to tickets with specific tags. If left empty it will apply to all tags.")
    stage_id = fields.Many2one(
        'helpdesk.stage', 'Target Stage',
        help='Minimum stage a ticket needs to reach in order to satisfy this SLA.')
    exclude_stage_ids = fields.Many2many(
        'helpdesk.stage', string='Excluding Stages', copy=True,
        domain="[('id', '!=', stage_id.id)]",
        help='The amount of time the ticket spends in this stage will not be taken into account when evaluating the status of the SLA Policy.')
    priority = fields.Selection(
        TICKET_PRIORITY, string='Minimum Priority',
        default='0', required=True,
        help='Tickets under this priority will not be taken into account.')
    partner_ids = fields.Many2many(
        'res.partner', string="Customers",
        help="This SLA Policy will apply to any tickets from the selected customers. Leave empty to apply this SLA Policy to any ticket without distinction.")
    company_id = fields.Many2one('res.company', 'Company', related='team_id.company_id', readonly=True, store=True)
    time = fields.Float('In', help='Time to reach given stage based on ticket creation date', default=0, required=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        res = self.env['helpdesk.ticket'].read_group(
            [('sla_ids', 'in', self.ids), ('stage_id.is_close', '=', False)],
            ['sla_ids'], ['sla_ids'])
        sla_data = {r['sla_ids']: r['sla_ids_count'] for r in res}
        for sla in self:
            sla.ticket_count = sla_data.get(sla.id, 0)

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('sla_ids', 'in', self.ids)],
            'context': {
                'search_default_is_open': True,
                'create': False,
            },
        })
        return action
