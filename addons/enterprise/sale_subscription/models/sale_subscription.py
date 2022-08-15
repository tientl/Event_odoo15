# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import datetime
import traceback

from ast import literal_eval
from collections import Counter
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from uuid import uuid4

from odoo import api, fields, models, Command, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_date, is_html_empty, config
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)

INTERVAL_FACTOR = {
    'daily': 30.0,
    'weekly': 30.0 / 7.0,
    'monthly': 1.0,
    'yearly': 1.0 / 12.0,
}

PERIODS = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}

class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _description = "Subscription"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'rating.mixin', 'utm.mixin']
    _check_company_auto = True
    _mail_post_access = 'read'

    def _get_default_pricelist(self):
        return self.env['product.pricelist'].search([('currency_id', '=', self.env.company.currency_id.id)], limit=1).id

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    name = fields.Char(required=True, tracking=True, default="New")
    code = fields.Char(string="Reference", required=True, tracking=True, index=True, copy=False)
    stage_id = fields.Many2one(
        'sale.subscription.stage', string='Stage', index=True, default=lambda s: s._get_default_stage_id(),
        copy=False, group_expand='_read_group_stage_ids', tracking=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                          domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", check_company=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda s: s.env.company, required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, auto_join=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    tag_ids = fields.Many2many('account.analytic.tag', string='Tags',
                               domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", check_company=True)
    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date = fields.Date(string='End Date', tracking=True, help="If set in advance, the subscription will be set to renew 1 month before the date and will be closed on the date set in this field.")
    pricelist_id = fields.Many2one('product.pricelist',  domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                   string='Pricelist', default=_get_default_pricelist, required=True, check_company=True)
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Currency', readonly=True)
    recurring_invoice_line_ids = fields.One2many('sale.subscription.line', 'analytic_account_id', string='Subscription Lines', copy=True)
    archived_product_ids = fields.Many2many('product.product', string='Archived Products',
                                            compute='_compute_archived')
    archived_product_count = fields.Integer("Archived Product", compute='_compute_archived')
    recurring_rule_type = fields.Selection(string='Recurrence', help="Invoice automatically repeat at specified interval", related="template_id.recurring_rule_type", readonly=1)
    recurring_interval = fields.Integer(string='Repeat Every', help="Repeat every (Days/Week/Month/Year)", related="template_id.recurring_interval", readonly=1)
    recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today, help="The next invoice will be created on this date then the period will be extended.")
    recurring_invoice_day = fields.Integer('Recurring Invoice Day', copy=False, default=lambda e: fields.Date.today().day)
    recurring_total = fields.Float(compute='_amount_all', string="Recurring Price", store=True, tracking=40)
    # add tax calculation
    recurring_tax = fields.Float('Taxes', compute="_amount_all", compute_sudo=True, store=True)
    recurring_total_incl = fields.Float('Total', compute="_amount_all", compute_sudo=True, store=True, tracking=50)
    recurring_monthly = fields.Float(compute='_compute_recurring_monthly', string="Monthly Recurring Revenue", store=True)
    close_reason_id = fields.Many2one("sale.subscription.close.reason", string="Close Reason", copy=False, tracking=True)
    template_id = fields.Many2one(
        'sale.subscription.template', string='Subscription Template',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", required=True,
        help="The subscription template defines the invoice policy and the payment terms.", tracking=True, check_company=True)
    subscription_log_ids = fields.One2many('sale.subscription.log', 'subscription_id', string='Subscription Logs', readonly=True)
    payment_mode = fields.Selection(related='template_id.payment_mode', readonly=False)
    description = fields.Html()
    user_id = fields.Many2one('res.users', string='Salesperson', tracking=True, default=lambda self: self.env.user)
    team_id = fields.Many2one(
        'crm.team', 'Sales Team', change_default=True, default=_get_default_team,
        check_company=True, ondelete="set null", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    team_user_id = fields.Many2one('res.users', string="Team Leader", related="team_id.user_id", readonly=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    country_id = fields.Many2one('res.country', related='partner_id.country_id', store=True, readonly=False, compute_sudo=True)
    industry_id = fields.Many2one('res.partner.industry', related='partner_id.industry_id', store=True, readonly=False)
    sale_order_count = fields.Integer(compute='_compute_sale_order_count')
    # customer portal
    uuid = fields.Char('Account UUID', default=lambda self: str(uuid4()), copy=False, required=True)
    website_url = fields.Char('Website URL', compute='_website_url', help='The full URL to access the document through the website.')
    commercial_partner_id = fields.Many2one('res.partner', related='partner_id.commercial_partner_id', store=False)
    payment_token_id = fields.Many2one(
        'payment.token', 'Payment Token', check_company=True,
        help='If not set, the automatic payment will fail.',
        domain="[('partner_id', 'child_of', commercial_partner_id), ('company_id', '=', company_id)]")
    recurring_rule_boundary = fields.Selection(related="template_id.recurring_rule_boundary", readonly=False)
    starred_user_ids = fields.Many2many(
        'res.users', 'subscription_starred_user_rel', 'subscription_id', 'user_id',
        default=lambda s: s._get_default_starred_user_ids(),
        string='Members')
    starred = fields.Boolean(compute='_compute_starred', inverse='_inverse_starred', string='Show Subscription on dashboard',
                             help="Whether this subscription should be displayed on the dashboard or not")
    kpi_1month_mrr_delta = fields.Float('KPI 1 Month MRR Delta')
    kpi_1month_mrr_percentage = fields.Float('KPI 1 Month MRR Percentage')
    kpi_3months_mrr_delta = fields.Float('KPI 3 months MRR Delta')
    kpi_3months_mrr_percentage = fields.Float('KPI 3 Months MRR Percentage')
    percentage_satisfaction = fields.Integer(
        compute="_compute_percentage_satisfaction", string="% Happy", store=True, compute_sudo=True, default=-1,
        help="Calculate the ratio between the number of the best ('great') ratings and the total number of ratings")
    health = fields.Selection([
        ('normal', 'Neutral'),
        ('done', 'Good'),
        ('bad', 'Bad')], string="Health", copy=False, default='normal', help="Show the health status")
    stage_category = fields.Selection(related='stage_id.category', store=True)
    to_renew = fields.Boolean(string='To Renew', default=False, copy=False)
    payment_term_id = fields.Many2one('account.payment.term', string='Default Payment Terms', check_company=True, tracking=True, help="These payment terms will be used when generating new invoices and renewal/upsell orders. Note that invoices paid using online payment will use 'Already paid' regardless of this setting.")

    _sql_constraints = [
        ('uuid_uniq', 'unique (uuid)', """UUIDs (Universally Unique IDentifier) for Sale Subscriptions should be unique!"""),
    ]

    @api.depends('rating_ids.rating')
    def _compute_percentage_satisfaction(self):
        for subscription in self:
            activities = subscription.rating_get_grades()
            total_activity_values = sum(activities.values())
            subscription.percentage_satisfaction = activities['great'] * 100 / total_activity_values if total_activity_values else -1

    def _compute_sale_order_count(self):
        sol = self.env['sale.order.line']
        if sol.check_access_rights('read', raise_exception=False):
            raw_data = sol.read_group(
                [('subscription_id', 'in', self.ids)],
                ['subscription_id', 'order_id'],
                ['subscription_id', 'order_id'],
                lazy=False,
            )
            count = Counter(g['subscription_id'][0] for g in raw_data)
        else:
            count = Counter()

        for subscription in self:
            subscription.sale_order_count = count[subscription.id]

    def _get_default_stage_id(self):
        return self.env['sale.subscription.stage'].search([], order='sequence', limit=1)

    def _get_default_starred_user_ids(self):
        return [(6, 0, [self.env.uid])]

    def _compute_starred(self):
        for subscription in self:
            subscription.starred = self.env.user in subscription.starred_user_ids

    def _inverse_starred(self):
        starred_subscriptions = not_star_subscriptions = self.env['sale.subscription'].sudo()
        for subscription in self:
            if self.env.user in subscription.starred_user_ids:
                starred_subscriptions |= subscription
            else:
                not_star_subscriptions |= subscription
        not_star_subscriptions.write({'starred_user_ids': [(4, self.env.uid)]})
        starred_subscriptions.write({'starred_user_ids': [(3, self.env.uid)]})

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.sudo().search([], order=order)

    def action_open_sales(self):
        self.ensure_one()
        sales = self.env['sale.order'].search([('order_line.subscription_id', 'in', self.ids)])
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[self.env.ref('sale_subscription.sale_order_view_tree_subscription').id, "tree"],
                      [self.env.ref('sale.view_order_form').id, "form"],
                      [False, "kanban"], [False, "calendar"], [False, "pivot"], [False, "graph"]],
            "domain": [["id", "in", sales.ids]],
            "context": {"create": False},
            "name": _("Sales Orders"),
        }

    def partial_invoice_line(self, sale_order, option_line, refund=False, date_from=False):
        """ Add an invoice line on the sales order for the specified option and add a discount
        to take the partial recurring period into account """
        order_line_obj = self.env['sale.order.line']
        ratio, message, period_msg = self.with_context(lang=sale_order.partner_id.lang)\
            ._partial_recurring_invoice_ratio(date_from=date_from)
        if message != "":
            sale_order.message_post(body=message)
        _discount = (1 - ratio) * 100
        values = {
            'order_id': sale_order.id,
            'product_id': option_line.product_id.id,
            'subscription_id': self.id,
            'product_uom_qty': option_line.quantity,
            'product_uom': option_line.uom_id.id,
            'discount': _discount,
            'price_unit': self.pricelist_id.with_context(uom=option_line.uom_id.id).get_product_price(option_line.product_id, 1, False),
            'name': order_line_obj.with_context(lang=sale_order.partner_id.lang).get_sale_order_line_multiline_description_sale(
                option_line.product_id.with_context(lang=sale_order.partner_id.lang)) + '\n' + period_msg,
        }
        return order_line_obj.create(values)

    def _partial_recurring_invoice_ratio(self, date_from=False):
        """Computes the ratio of the amount of time remaining in the current invoicing period
        over the total length of said invoicing period"""
        if date_from:
            date = fields.Date.from_string(date_from)
        else:
            date = datetime.date.today()
        invoicing_period = relativedelta(**{PERIODS[self.recurring_rule_type]: self.recurring_interval})
        recurring_next_invoice = fields.Date.from_string(self.recurring_next_date)
        recurring_last_invoice = recurring_next_invoice - invoicing_period
        time_to_invoice = recurring_next_invoice - date
        ratio = float(time_to_invoice.days) / float((recurring_next_invoice - recurring_last_invoice).days)
        period_msg = _("Invoicing period") + ": %s - %s" % (format_date(self.env, date), format_date(self.env, recurring_next_invoice - relativedelta(days=1))) # The period does not include the next renewal date
        if (ratio < 0 or ratio > 1):
            message = _(
                "Discount computation failed because the upsell date is not between the next "
                "invoice date and the computed last invoice date. Defaulting to NO Discount policy."
            )
            message += "<br/>{}{}<br/>{}{}<br/>{}{}".format(
                _("Upsell date: "), format_date(self.env, date),
                _("Next invoice date: "), format_date(self.env, recurring_next_invoice),
                _("Last invoice date: "), format_date(self.env, recurring_last_invoice),
            )
            ratio = 1.00
        else:
            message = ""
        return ratio, message, period_msg

    def partial_recurring_invoice_ratio(self, date_from=False):
        return self._partial_recurring_invoice_ratio(date_from=False)[0]

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return self.env.ref('sale_subscription.subtype_stage_change')
        return super(SaleSubscription, self)._track_subtype(init_values)

    def _compute_invoice_count(self):
        can_read = self.env['account.move'].check_access_rights('read', raise_exception=False)
        if not can_read:
            self.update({'invoice_count': 0})
            return
        res = self.env['account.move.line'].read_group(
            [('subscription_id', 'in', self.ids)], ['move_id:count_distinct'], ['subscription_id'])
        invoice_count_dict = {r['subscription_id'][0]: r['move_id'] for r in res}
        for subscription in self:
            subscription.invoice_count = invoice_count_dict.get(subscription.id, 0)

    @api.depends('recurring_total', 'template_id.recurring_interval', 'template_id.recurring_rule_type')
    def _compute_recurring_monthly(self):
        # Generally accepted ratios for monthly reporting
        for sub in self:
            sub.recurring_monthly = (
                sub.recurring_total * INTERVAL_FACTOR[sub.recurring_rule_type] / sub.recurring_interval
            ) if sub.template_id else 0

    @api.depends('uuid')
    def _website_url(self):
        for account in self:
            account.website_url = '/my/subscription/%s/%s' % (account.id, account.uuid)

    @api.depends('recurring_invoice_line_ids.price_subtotal')
    def _amount_all(self):
        """
        Compute the total amounts of the subscription.
        """
        for subscription in self:
            amount_tax = 0.0
            recurring_total = 0.0
            for line in subscription.recurring_invoice_line_ids:
                recurring_total += line.price_subtotal
                # _amount_line_tax needs singleton
                amount_tax += line._amount_line_tax()
            recurring_tax = subscription.currency_id and subscription.currency_id.round(amount_tax) or 0.0
            subscription.update({
                'recurring_total': recurring_total,
                'recurring_tax': recurring_tax,
                'recurring_total_incl': recurring_tax + recurring_total,
            })

    @api.depends('recurring_invoice_line_ids.product_id')
    def _compute_archived(self):
        # Search which products are archived when reading the subscriptions lines
        self = self.with_context(active_test=False)
        for subscription in self:
            subscription.archived_product_ids = self.env['product.product'].search(
                [('id', 'in', subscription.recurring_invoice_line_ids.mapped('product_id').ids),
                 ('recurring_invoice', '=', True),
                 ('active', '=', False)],
            )
            subscription.archived_product_count = len(subscription.archived_product_ids)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.pricelist_id = self.partner_id.with_company(self.company_id).property_product_pricelist.id
            self.payment_term_id = self.partner_id.with_company(self.company_id).property_payment_term_id.id
            addresses = self.partner_id.address_get(['delivery', 'invoice'])
            self.partner_shipping_id = addresses['delivery']
            self.partner_invoice_id = addresses['invoice']
        if self.partner_id.user_id:
            self.user_id = self.partner_id.user_id

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id and self.user_id.sale_team_id:
            self.team_id = self.user_id.sale_team_id

    @api.onchange('date_start', 'template_id')
    def onchange_date_start(self):
        if self.date_start and self.recurring_rule_boundary == 'limited':
            self.date = fields.Date.from_string(self.date_start) + relativedelta(**{
                PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval})
        else:
            self.date = False

    @api.onchange('template_id', 'partner_id')
    def on_change_template(self):
        for subscription in self.filtered('template_id'):
            subscription.description = subscription.template_id.with_context(lang=subscription.partner_id.lang or self.env.lang).description

    @api.model
    def create(self, vals):
        vals['code'] = (
            vals.get('code') or
            self.env.context.get('default_code') or
            self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('sale.subscription') or
            'New'
        )
        if vals.get('name', 'New') == 'New':
            vals['name'] = vals['code']
        if not vals.get('recurring_invoice_day'):
            sub_date = vals.get('recurring_next_date') or vals.get('date_start') or fields.Date.context_today(self)
            if isinstance(sub_date, datetime.date):
                vals['recurring_invoice_day'] = sub_date.day
            else:
                vals['recurring_invoice_day'] = fields.Date.from_string(sub_date).day
        subscription = super(SaleSubscription, self).create(vals)
        if vals.get('stage_id'):
            subscription._send_subscription_rating_mail(force_send=True)
        if subscription.partner_id and subscription.stage_category == "progress":
            subscription.message_subscribe(subscription.partner_id.ids)
        return subscription

    def write(self, vals):
        recurring_next_date = vals.get('recurring_next_date')
        if recurring_next_date and not self.env.context.get('skip_update_recurring_invoice_day'):
            if isinstance(recurring_next_date, datetime.date):
                vals['recurring_invoice_day'] = recurring_next_date.day
            else:
                vals['recurring_invoice_day'] = fields.Date.from_string(recurring_next_date).day
        old_partners = {s.id: s.partner_id.id for s in self}
        old_in_progress = {s.id: s.stage_category == "progress" for s in self}
        if vals.get('payment_token_id'):
            # check access rule for token to make sure the user is allowed to read it. This prevents
            # assigning unowned tokens through RPC calls
            self.env['payment.token'].browse(vals.get('payment_token_id')).check_access_rule('read')
        result = super(SaleSubscription, self).write(vals)
        if vals.get('stage_id'):
            self._send_subscription_rating_mail(force_send=True)
        for subscription in self:
            diff_partner = subscription.partner_id.id != old_partners[subscription.id]
            diff_in_progress = (subscription.stage_category == "progress") != old_in_progress[subscription.id]
            if diff_partner or diff_in_progress:
                if subscription.stage_category == "progress":
                    subscription.message_subscribe(subscription.partner_id.ids)
                if diff_partner or subscription.stage_category != "progress":
                    subscription.message_unsubscribe([old_partners[subscription.id]])
        return result

    def _init_column(self, column_name):
        # to avoid generating a single default uuid when installing the module,
        # we need to set the default row by row for this column
        if column_name == "uuid":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                          self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE uuid IS NULL" % self._table)
            acc_ids = self.env.cr.dictfetchall()
            query_list = [{'id': acc_id['id'], 'uuid': str(uuid4())} for acc_id in acc_ids]
            query = 'UPDATE ' + self._table + ' SET uuid = %(uuid)s WHERE id = %(id)s;'
            self.env.cr._obj.executemany(query, query_list)

        else:
            super(SaleSubscription, self)._init_column(column_name)

    def name_get(self):
        res = []
        for sub in self.filtered('id'):
            partner_name = sub.partner_id.sudo().display_name
            subscription_name = '%s - %s' % (sub.code, partner_name) if sub.code else partner_name
            template_name = sub.template_id.sudo().code
            display_name = '%s/%s' % (template_name, subscription_name) if template_name else subscription_name
            res.append((sub.id, display_name))
        return res

    def action_subscription_invoice(self):
        self.ensure_one()
        invoices = self.env['account.move'].search([('invoice_line_ids.subscription_id', 'in', self.ids)])
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action["context"] = {
            "create": False,
            "default_move_type": "out_invoice"
        }
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.model
    def cron_account_analytic_account(self):
        today = fields.Date.today()
        next_month = fields.Date.to_string(fields.Date.from_string(today) + relativedelta(months=1))

        # set to pending if date is in less than a month
        domain_pending = [('date', '<', next_month), ('stage_category', '=', 'progress')]
        subscriptions_pending = self.search(domain_pending)
        subscriptions_pending.set_to_renew()

        # set to close if date is passed
        domain_close = [('date', '<', today), '|', ('stage_category', '=', 'progress'), ('to_renew', '=', True)]
        subscriptions_close = self.search(domain_close)
        subscriptions_close.set_close()

        return dict(pending=subscriptions_pending.ids, closed=subscriptions_close.ids)

    @api.model
    def _cron_recurring_create_invoice(self):
        return self._recurring_create_invoice(automatic=True)

    @api.model
    def _cron_update_kpi(self):
        subscriptions = self.search([('stage_category', '=', 'progress')])
        subscriptions._compute_kpi()

    def _mail_track(self, tracked_fields, initial):
        """ For a given record, fields to check (tuple column name, column info)
                and initial values, return a structure that is a tuple containing :
                 - a set of updated column names
                 - a list of ORM (0, 0, values) commands to create 'mail.tracking.value' """
        res = super()._mail_track(tracked_fields, initial)
        updated_fields, commands = res
        if any(f in updated_fields for f in ['recurring_total', 'template_id']):
            # Intial may not always contains all the needed values if they didn't changed
            # Fallback on record value in that case
            initial_rrule_type = INTERVAL_FACTOR[initial.get('recurring_rule_type', self.recurring_rule_type)]
            initial_rrule_interval = initial.get('recurring_interval', self.recurring_interval)
            old_factor = initial_rrule_type / initial_rrule_interval
            old_value_monthly = initial.get('recurring_total', self.recurring_total) * old_factor
            new_factor = INTERVAL_FACTOR[self.recurring_rule_type] / self.recurring_interval
            new_value_monthly = self.recurring_total * new_factor
            delta = new_value_monthly - old_value_monthly
            cur_round = self.company_id.currency_id.rounding
            if not float_is_zero(delta, precision_rounding=cur_round):
                self.env['sale.subscription.log'].sudo().create({
                    'event_date': fields.Date.context_today(self),
                    'subscription_id': self.id,
                    'currency_id': self.currency_id.id,
                    'recurring_monthly': new_value_monthly,
                    'amount_signed': delta,
                    'event_type': '1_change',
                    'category': self.stage_id.category,
                    'user_id': self.user_id.id,
                    'team_id': self.team_id.id,
                })
        if 'stage_id' in updated_fields:
            old_stage_id = initial['stage_id']
            new_stage_id = self.stage_id
            if new_stage_id.category in ['progress', 'closed'] and old_stage_id.category != new_stage_id.category:
                # subscription started or churned
                start_churn = {'progress': {'type': '0_creation', 'amount_signed': self.recurring_monthly,
                                            'recurring_monthly': self.recurring_monthly},
                                'closed': {'type': '2_churn', 'amount_signed': -self.recurring_monthly,
                                            'recurring_monthly': 0}}
                self.env['sale.subscription.log'].sudo().create({
                    'event_date': fields.Date.context_today(self),
                    'subscription_id': self.id,
                    'currency_id': self.currency_id.id,
                    'recurring_monthly': start_churn[new_stage_id.category]['recurring_monthly'],
                    'amount_signed': start_churn[new_stage_id.category]['amount_signed'],
                    'event_type': start_churn[new_stage_id.category]['type'],
                    'category': self.stage_id.category,
                    'user_id': self.user_id.id,
                    'team_id': self.team_id.id,
                })
        return res

    def _get_subscription_delta(self, date):
        self.ensure_one()
        delta, percentage = False, False
        subscription_log = self.env['sale.subscription.log'].search([
            ('subscription_id', '=', self.id), ('event_type', 'in', ['1_change', '0_creation']),
            ('event_date', '<=', date)], order='event_date desc', limit=1)
        if subscription_log:
            delta = self.recurring_monthly - subscription_log.recurring_monthly
            percentage = delta / subscription_log.recurring_monthly if subscription_log.recurring_monthly != 0 else 100
        return {'delta': delta, 'percentage': percentage}

    def _get_subscription_health(self):
        self.ensure_one()
        domain = [('id', '=', self.id)]
        if self.template_id.bad_health_domain != '[]' and self.search_count(domain + literal_eval(self.template_id.bad_health_domain)):
            health = 'bad'
        elif self.template_id.good_health_domain != '[]' and self.search_count(domain + literal_eval(self.template_id.good_health_domain)):
            health = 'done'
        else:
            health = 'normal'
        return health

    def _compute_kpi(self):
        for subscription in self:
            delta_1month = subscription._get_subscription_delta(datetime.date.today() - relativedelta(months=1))
            delta_3months = subscription._get_subscription_delta(datetime.date.today() - relativedelta(months=3))
            health = subscription._get_subscription_health()
            subscription.write({
                'kpi_1month_mrr_delta': delta_1month['delta'],
                'kpi_1month_mrr_percentage': delta_1month['percentage'],
                'kpi_3months_mrr_delta': delta_3months['delta'],
                'kpi_3months_mrr_percentage': delta_3months['percentage'],
                'health': health,
            })

    def _send_subscription_rating_mail(self, force_send=False):
        for subscription in self.filtered(lambda subscription: subscription.stage_id.rating_template_id):
            subscription.rating_send_request(
                subscription.stage_id.rating_template_id,
                lang=subscription.partner_id.lang,
                force_send=force_send)

    def set_to_renew(self):
        return self.write({'to_renew': True})

    def unset_to_renew(self):
        return self.write({'to_renew': False})

    def clear_date(self):
        return self.write({'date': False})

    def set_close(self):
        today = fields.Date.from_string(fields.Date.context_today(self))
        search = self.env['sale.subscription.stage'].search
        for sub in self:
            stage = search([('category', '=', 'closed'), ('sequence', '>=', sub.stage_id.sequence)], limit=1)
            if not stage:
                stage = search([('category', '=', 'closed')], limit=1)
            values = {'stage_id': stage.id, 'to_renew': False}
            if sub.recurring_rule_boundary == 'unlimited' or not sub.date or today < sub.date:
                values['date'] = today
            sub.write(values)
        return True

    def set_open(self):
        search = self.env['sale.subscription.stage'].search
        for sub in self:
            stage = search([('category', '=', 'progress'), ('sequence', '>=', sub.stage_id.sequence)], limit=1)
            if not stage:
                stage = search([('category', '=', 'progress')], limit=1)
            date = sub.date if sub.date_start and sub.template_id.recurring_rule_boundary == 'limited' else False
            sub.write({'stage_id': stage.id, 'to_renew': False, 'date': date})

    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("You must first select a Customer for Subscription %s!", self.name))

        company = self.env.company or self.company_id

        journal = self.template_id.journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError(_('Please define a sale journal for the company "%s".') % (company.name or '', ))

        next_date = self.recurring_next_date
        if not next_date:
            raise UserError(_('Please define Date of Next Invoice of "%s".') % (self.display_name,))
        recurring_next_date = self._get_recurring_next_date(self.recurring_rule_type, self.recurring_interval, next_date, self.recurring_invoice_day)
        end_date = fields.Date.from_string(recurring_next_date) - relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_id = self.partner_invoice_id.id or addr['invoice']
        partner_shipping_id = self.partner_shipping_id.id or addr['delivery']
        fpos = self.env['account.fiscal.position'].with_company(company).get_fiscal_position(self.partner_id.id, partner_shipping_id)
        narration = _("This invoice covers the following period: %s - %s") % (format_date(self.env, next_date), format_date(self.env, end_date))
        if not is_html_empty(self.description):
            narration += Markup('<br/>') + self.description
        elif self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and not is_html_empty(self.company_id.invoice_terms):
            narration += Markup('<br/>') + self.company_id.invoice_terms
        res = {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'partner_shipping_id': partner_shipping_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'journal_id': journal.id,
            'invoice_origin': self.code,
            'fiscal_position_id': fpos.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'narration': narration,
            'invoice_user_id': self.user_id.id,
            'partner_bank_id': company.partner_id.bank_ids.filtered(lambda b: not b.company_id or b.company_id == company)[:1].id,
        }
        if self.env.context.get('new_invoice_ref'):
            res['ref'] = self.env.context['new_invoice_ref']
        if self.team_id:
            res['team_id'] = self.team_id.id
        return res

    @api.model
    def _get_recurring_next_date(self, interval_type, interval, current_date, recurring_invoice_day):
        """
        This method is used for calculating next invoice date for a subscription
        :params interval_type: type of interval i.e. yearly, monthly, weekly etc.
        :params interval: number of interval i.e. 2 week, 1 month, 6 month, 1 year etc.
        :params current_date: date from which next invoice date is to be calculated
        :params recurring_invoice_day: day on which next invoice is to be generated in future
        :returns: date on which invoice will be generated
        """
        interval_type = PERIODS[interval_type]
        recurring_next_date = fields.Date.from_string(current_date) + relativedelta(**{interval_type: interval})
        if interval_type == 'months':
            last_day_of_month = recurring_next_date + relativedelta(day=31)
            if last_day_of_month.day >= recurring_invoice_day:
                # In cases where the next month does not have same day as of previous recurrent invoice date, we set the last date of next month
                # Example: current_date is 31st January then next date will be 28/29th February
                return recurring_next_date.replace(day=recurring_invoice_day)
            # In cases where the subscription was created on the last day of a particular month then it should stick to last day for all recurrent monthly invoices
            # Example: 31st January, 28th February, 31st March, 30 April and so on.
            return last_day_of_month
        # Return the next day after adding interval
        return recurring_next_date

    def _prepare_invoice_line(self, line, fiscal_position, date_start=False, date_stop=False):
        company = self.env.company or line.analytic_account_id.company_id
        tax_ids = line.product_id.taxes_id.filtered(lambda t: t.company_id == company)
        price_unit = line.price_unit
        if fiscal_position and tax_ids:
            tax_ids = self.env['account.fiscal.position'].browse(fiscal_position).map_tax(tax_ids)
            price_unit = self.env['account.tax']._fix_tax_included_price_company(line.price_unit, line.product_id.taxes_id, tax_ids, self.company_id)
        values = {
            'name': line.name,
            'subscription_id': line.analytic_account_id.id,
            'price_unit': price_unit or 0.0,
            'discount': line.discount,
            'quantity': line.quantity,
            'product_uom_id': line.uom_id.id,
            'product_id': line.product_id.id,
            'tax_ids': [(6, 0, tax_ids.ids)],
            'subscription_start_date': date_start,
            'subscription_end_date': date_stop,
        }
        # only adding analytic_account_id and tag_ids if they exist in the sale.subscription.
        # if not, they will be computed used the analytic default rule
        if line.analytic_account_id.analytic_account_id.id:
            values.update({'analytic_account_id': line.analytic_account_id.analytic_account_id.id})
        if line.analytic_account_id.tag_ids.ids:
            values.update({'analytic_tag_ids': [(6, 0, line.analytic_account_id.tag_ids.ids)]})
        return values
    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        revenue_date_start = self.recurring_next_date
        revenue_date_stop = revenue_date_start + relativedelta(**{PERIODS[self.recurring_rule_type]: self.recurring_interval}) - relativedelta(days=1)
        return [(0, 0, self._prepare_invoice_line(line, fiscal_position, revenue_date_start, revenue_date_stop)) for line in self.recurring_invoice_line_ids.filtered(
            lambda l: not float_is_zero(l.quantity, precision_rounding=l.product_id.uom_id.rounding)
        )]

    def _prepare_invoice(self):
        """
        Note that the company of the environment will be the one for which the invoice will be created.

        :returns: account.move create values
        :rtype: dict
        """
        invoice = self._prepare_invoice_data()
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(invoice['fiscal_position_id'])
        return invoice

    def generate_recurring_invoice(self):
        res = self._recurring_create_invoice()
        if res:
            return self.action_subscription_invoice()
        else:
            raise UserError("You already have generated an invoice for each period.")

    def _prepare_renewal_order_values(self, discard_product_ids=False, new_lines_ids=False):
        res = dict()
        for subscription in self:
            subscription = subscription.with_company(subscription.company_id)
            order_lines = []
            fpos = subscription.env['account.fiscal.position'].get_fiscal_position(subscription.partner_id.id)
            partner_lang = subscription.partner_id.lang
            if discard_product_ids:
                # Prevent to add products discarded during the renewal
                line_ids = subscription.with_context(active_test=False).recurring_invoice_line_ids.filtered(
                    lambda l: l.product_id.id not in discard_product_ids)
            else:
                line_ids = subscription.recurring_invoice_line_ids
            for line in line_ids:
                product = line.product_id.with_context(lang=partner_lang) if partner_lang else line.product_id
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': product.with_context(active_test=False).get_product_multiline_description_sale(),
                    'subscription_id': subscription.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                }))
            if new_lines_ids:
                # Add products during the renewal (sort of upsell)
                for line in new_lines_ids:
                    existing_line_ids = subscription.recurring_invoice_line_ids.filtered(
                        lambda l: l.product_id.id == line.product_id.id)
                    if existing_line_ids:
                        # The product already exists in the SO lines, update the quantity
                        def _update_quantity(so_line):
                            # Map function to update the quantity of the SO line.
                            if so_line[2]['product_id'] in existing_line_ids.mapped('product_id').ids:
                                so_line[2]['product_uom_qty'] = line.quantity + so_line[2]['product_uom_qty']
                            return so_line
                        # Update the order lines with the new quantity
                        order_lines = list(map(_update_quantity, order_lines))
                    else:
                        order_lines.append((0, 0, {
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'subscription_id': subscription.id,
                            'product_uom': line.uom_id.id,
                            'product_uom_qty': line.quantity,
                            'price_unit': subscription.pricelist_id.with_context(uom=line.uom_id.id).get_product_price(
                                line.product_id, line.quantity, subscription.partner_id),
                            'discount': 0,
                        }))
            addr = subscription.partner_id.address_get(['delivery', 'invoice'])
            res[subscription.id] = {
                'pricelist_id': subscription.pricelist_id.id,
                'partner_id': subscription.partner_id.id,
                'partner_invoice_id': subscription.partner_invoice_id.id or addr['invoice'],
                'partner_shipping_id': subscription.partner_shipping_id.id or addr['delivery'],
                'currency_id': subscription.pricelist_id.currency_id.id,
                'order_line': order_lines,
                'analytic_account_id': subscription.analytic_account_id.id,
                'subscription_management': 'renew',
                'origin': subscription.code,
                'note': subscription.description,
                'fiscal_position_id': fpos.id,
                'user_id': subscription.user_id.id,
                'payment_term_id': subscription.payment_term_id.id,
                'company_id': subscription.company_id.id,
            }
        return res

    def prepare_renewal_order(self, discard_product_ids=False, new_lines_ids=False):
        self.ensure_one()
        values = self._prepare_renewal_order_values(discard_product_ids, new_lines_ids)
        order = self.env['sale.order'].create(values[self.id])
        order.message_post(body=(_("This renewal order has been created from the subscription ") + " <a href=# data-oe-model=sale.subscription data-oe-id=%d>%s</a>" % (self.id, self.display_name)))
        order.order_line._compute_tax_id()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": order.id,
        }

    def start_subscription(self):
        self.ensure_one()
        next_stage_in_progress = self.env['sale.subscription.stage'].search([('category', '=', 'progress'), ('sequence', '>=', self.stage_id.sequence)], limit=1)
        if not next_stage_in_progress:
            next_stage_in_progress = self.env['sale.subscription.stage'].search([('category', '=', 'progress')], limit=1)
        self.stage_id = next_stage_in_progress
        return True

    def increment_period(self, renew=False):
        for subscription in self:
            current_date = subscription.recurring_next_date or self.default_get(['recurring_next_date'])['recurring_next_date']
            new_date = subscription._get_recurring_next_date(subscription.recurring_rule_type, subscription.recurring_interval, current_date, subscription.recurring_invoice_day)
            new_values = {'recurring_next_date': new_date}
            if subscription.date and renew:
                new_values['date'] = subscription.date + relativedelta(**{
                    PERIODS[subscription.recurring_rule_type]:
                        subscription.template_id.recurring_rule_count * subscription.template_id.recurring_interval
                })
            subscription.write(new_values)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', '|', ('code', operator, name), ('name', operator, name), ('partner_id.name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def wipe(self):
        """Wipe a subscription clean by deleting all its lines."""
        lines = self.mapped('recurring_invoice_line_ids')
        lines.unlink()
        return True

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }

    def add_option(self, option_id):
        pass

    def set_option(self, subscription, new_option, price):
        pass

    def remove_option(self, option_id):
        pass

    def _compute_options(self):
        pass

    def _do_payment(self, payment_token, invoice):
        tx_obj = self.env['payment.transaction']
        results = []

        for subscription in self:
            reference = tx_obj._compute_reference(
                payment_token.acquirer_id.provider, prefix=subscription.code
            )   # There is no sub_id field to rely on
            values = {
                'acquirer_id': payment_token.acquirer_id.id,
                'reference': reference,
                'amount': invoice.amount_total,
                'currency_id': invoice.currency_id.id,
                'partner_id': subscription.partner_id.id,
                'token_id': payment_token.id,
                'operation': 'offline',
                'invoice_ids': [(6, 0, [invoice.id])],
                'callback_model_id': self.env['ir.model']._get_id(subscription._name),
                'callback_res_id': subscription.id,
                'callback_method': 'reconcile_pending_transaction',
            }
            tx = tx_obj.create(values)
            tx._send_payment_request()
            results.append(tx)
        return results

    def _reconcile_and_assign_token(self, tx):
        """ Callback method to make the reconciliation and assign the payment token.

        Note: self.ensure_one()

        :param recordset tx: The transaction that created the token, and that must be reconciled,
                             as a `payment.transaction` record
        :return: Whether the conditions were met to execute the callback
        :rtype: bool
        """
        self.ensure_one()

        if tx.renewal_allowed:
            self._assign_token(tx)
            self._reconcile_and_send_mail(tx)
            return True
        return False

    def _assign_token(self, tx):
        """ Callback method to assign a token after the validation of a transaction.

        Note: self.ensure_one()

        :param recordset tx: The validated transaction, as a `payment.transaction` record
        :return: Whether the conditions were met to execute the callback
        :rtype: bool
        """
        self.ensure_one()

        if tx.renewal_allowed:
            self.payment_token_id = tx.token_id.id
            return True
        return False

    def _reconcile_and_send_mail(self, tx):
        """ Callback method to make the reconciliation and send a confirmation email.

        Note: self.ensure_one()

        :param recordset tx: The transaction to reconcile, as a `payment.transaction` record
        :return: None
        """
        self.ensure_one()

        if self.reconcile_pending_transaction(tx):
            invoice = tx.invoice_ids[0]
            self.send_success_mail(tx, invoice)
            msg_body = _(
                "Manual payment succeeded. Payment reference: <a href=# data-oe-model=%(tx_model)s "
                "data-oe-id=%(tx_id)s>%(tx_ref)s</a>; Amount: %(amount)s. Invoice "
                "<a href=# data-oe-model=%(inv_model)s data-oe-id=%(inv_id)s>View Invoice</a>.",
                tx_model=tx._name, tx_id=tx.id, tx_ref=tx.reference, amount=tx.amount,
                inv_model=invoice._name, inv_id=invoice.id
            )
            self.message_post(body=msg_body)
            return True
        return False

    def reconcile_pending_transaction(self, tx):
        """ Callback method to make the reconciliation.

        Note: self.ensure_one()

        :param recordset tx: The transaction to reconcile, as a `payment.transaction` record
        :return: Whether the transaction was successfully reconciled
        :rtype: bool
        """
        self.ensure_one()

        if tx.renewal_allowed:  # The payment is confirmed, it can be reconciled
            # avoid to create an invoice when one is already linked
            if not tx.invoice_ids:
                # Re-create the invoice that was deleted in the controller and post it immediately
                invoice_values = self.with_context(lang=self.partner_id.lang)._prepare_invoice()
                invoice_values.update({
                    'ref': tx.reference,
                    'payment_reference': tx.reference
                })
                invoice = self.env['account.move'].create(invoice_values)
                invoice.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': invoice, 'origin': self},
                    subtype_id=self.env.ref('mail.mt_note').id
                )
                tx.invoice_ids = invoice.id,

            # Renew the subscription
            self.increment_period(renew=self.to_renew)
            self.set_open()
            return True
        return False

    def _get_subscription_domain_for_invoicing(self, current_date, tags):
        """
        Get the domain for subscriptions to invoice
        """
        return [
            ('tag_ids', 'not in', tags.ids),
            ('recurring_next_date', '<=', current_date),
            ('template_id.payment_mode', '!=', 'manual'),
            '|',
            ('stage_category', '=', 'progress'),
            ('to_renew', '=', True),
        ]

    def _recurring_create_invoice(self, automatic=False, batch_size=20):
        auto_commit = self.env.context.get('auto_commit', True)
        cr = self.env.cr
        invoices = self.env['account.move']
        current_date = datetime.date.today()
        # To avoid triggering the cron infinitely, we will add a temporary tag that will be removed by the last
        # call of the cron. The domain search will include the subscriptions without the tag.
        subscription_payment_exception_tag = self.env.ref('sale_subscription.subscription_payment_exception', raise_if_not_found=False)
        batch_tag = self.env.ref('sale_subscription.subscription_invalid_payment', raise_if_not_found=False)
        if automatic:
            if not subscription_payment_exception_tag:
                subscription_payment_exception_tag = self.env['account.analytic.tag'].sudo().create({'name': 'Subscription Payment Exception', 'color': 4})
                self.env['ir.model.data'].create({
                    'name': 'subscription_payment_exception',
                    'module': 'sale_subscription',
                    'res_id': subscription_payment_exception_tag.id,
                    'model': 'account.analytic.tag',
                    'noupdate': True
                })
            if not batch_tag:
                batch_tag = self.env['account.analytic.tag'].sudo().create(
                    {'name': 'Subscription Batch Invoicing', 'color': 4})
                self.env['ir.model.data'].create({
                    'name': 'subscription_invalid_payment',
                    'module': 'sale_subscription',
                    'res_id': batch_tag.id,
                    'model': 'account.analytic.tag',
                    'noupdate': True
                })
            if automatic and auto_commit:
                cr.commit()

        # To avoid charging without updating the subscription, we will add a temporary tag that will be removed when the invoice is properly processed
        if len(self) > 0:
            subscriptions = self
            need_cron_trigger = False
        else:
            subscriptions = self.search(self._get_subscription_domain_for_invoicing(current_date, subscription_payment_exception_tag | batch_tag), limit=batch_size + 1)
            need_cron_trigger = len(subscriptions) > batch_size
            if need_cron_trigger:
                subscriptions = subscriptions[:batch_size]
        if subscriptions:
            sub_data = subscriptions.read(fields=['id', 'company_id'])
            for company_id in set(data['company_id'][0] for data in sub_data):
                sub_ids = [s['id'] for s in sub_data if s['company_id'][0] == company_id]
                subs = self.with_company(company_id).with_context(company_id=company_id).browse(sub_ids)
                # We tag the subscription. If something happen, it will prevent multiple payment attempt
                Invoice = self.env['account.move'].with_context(move_type='out_invoice', company_id=company_id).with_company(company_id)
                subs_order_lines = self.env['sale.order.line'].search([('subscription_id', 'in', sub_ids)])
                for subscription in subs:
                    subscription = subscription[0]  # Trick to not prefetch other subscriptions, as the cache is currently invalidated at each iteration
                    sub_so = subs_order_lines.filtered(lambda ol: ol.subscription_id.id == subscription.id).order_id
                    sub_so_renewal = sub_so.filtered(lambda so: so.subscription_management == 'renew')
                    reference_so = max(sub_so_renewal, key=lambda so: so.date_order, default=False) or min(sub_so,
                                                                                                           key=lambda so: so.date_order,
                                                                                                           default=False)
                    invoice_ctx = {'lang': subscription.partner_id.lang}
                    if reference_so and reference_so.client_order_ref:
                        invoice_ctx['new_invoice_ref'] = reference_so.client_order_ref
                    if automatic and auto_commit:
                        cr.commit()

                    # if we reach the end date of the subscription then we close it and avoid to charge it
                    if automatic and subscription.date and subscription.date <= current_date:
                        subscription.set_close()
                        continue

                    # payment + invoice (only by cron)
                    if subscription.template_id.payment_mode == 'success_payment' and subscription.recurring_total and automatic:
                        subscription.with_context(mail_notrack=True).write({'tag_ids': [(4, subscription_payment_exception_tag.id)]}) # flag the sub in exception
                        if auto_commit:
                            cr.commit()
                        try:
                            payment_token = subscription.payment_token_id
                            tx = None
                            if payment_token:

                                invoice_values = subscription.with_context(invoice_ctx)._prepare_invoice()
                                new_invoice = Invoice.create(invoice_values)
                                if subscription.analytic_account_id or subscription.tag_ids:
                                    useful_tags = subscription.tag_ids - subscription_payment_exception_tag - batch_tag
                                    for line in new_invoice.invoice_line_ids:
                                        if subscription.analytic_account_id:
                                            line.analytic_account_id = subscription.analytic_account_id
                                        if useful_tags:
                                            line.analytic_tag_ids = useful_tags
                                new_invoice.message_post_with_view(
                                    'mail.message_origin_link',
                                    values={'self': new_invoice, 'origin': subscription},
                                    subtype_id=self.env.ref('mail.mt_note').id)
                                tx = subscription._do_payment(payment_token, new_invoice)[0]
                                # commit change as soon as we try the payment so we have a trace somewhere
                                if auto_commit:
                                    cr.commit()
                                if tx.renewal_allowed:
                                    subscription.with_context(mail_notrack=True).write({'tag_ids': [(3, subscription_payment_exception_tag.id)]})
                                    msg_body = _('Automatic payment succeeded. Payment reference: <a href=# data-oe-model=payment.transaction data-oe-id=%d>%s</a>; Amount: %s. Invoice <a href=# data-oe-model=account.move data-oe-id=%d>View Invoice</a>.') % (tx.id, tx.reference, tx.amount, new_invoice.id)
                                    subscription.message_post(body=msg_body)
                                    # success_payment
                                    if new_invoice.state != 'posted':
                                        new_invoice._post(False)
                                    subscription.send_success_mail(tx, new_invoice)
                                    if auto_commit:
                                        cr.commit()
                                else:
                                    _logger.error('Fail to create recurring invoice for subscription %s', subscription.code)
                                    if auto_commit:
                                        cr.rollback()
                                    # Check that the invoice still exists before unlinking. It might already have been deleted by `reconcile_pending_transaction`.
                                    new_invoice.exists().unlink()
                            if tx is None or not tx.renewal_allowed:
                                amount = subscription.recurring_total
                                auto_close_limit = subscription.template_id.auto_close_limit or 15
                                date_close = (
                                    subscription.recurring_next_date +
                                    relativedelta(days=auto_close_limit)
                                )
                                close_subscription = current_date >= date_close
                                email_context = self.env.context.copy()
                                email_context.update({
                                    'payment_token': subscription.payment_token_id and subscription.payment_token_id.name,
                                    'renewed': False,
                                    'total_amount': amount,
                                    'email_to': subscription.partner_id.email,
                                    'code': subscription.code,
                                    'currency': subscription.pricelist_id.currency_id.name,
                                    'date_end': subscription.date,
                                    'date_close': date_close,
                                    'auto_close_limit': auto_close_limit
                                })
                                if close_subscription:
                                    template = self.env.ref('sale_subscription.email_payment_close')
                                    template.with_context(email_context).send_mail(subscription.id)
                                    _logger.debug("Sending Subscription Closure Mail to %s for subscription %s and closing subscription", subscription.partner_id.email, subscription.id)
                                    msg_body = _('Automatic payment failed after multiple attempts. Subscription closed automatically.')
                                    subscription.message_post(body=msg_body)
                                    subscription.set_close()
                                    # remove the exception flag as we are done with this sub
                                    subscription.with_context(mail_notrack=True).write({'tag_ids': [(3, subscription_payment_exception_tag.id)]})
                                else:
                                    subscription.write({'tag_ids': [Command.link(batch_tag.id)]})
                                    template = self.env.ref('sale_subscription.email_payment_reminder')
                                    msg_body = _('Automatic payment failed. Subscription set to "To Renew".')
                                    if (datetime.date.today() - subscription.recurring_next_date).days in [0, 3, 7, 14]:
                                        template.with_context(email_context).send_mail(subscription.id)
                                        _logger.debug("Sending Payment Failure Mail to %s for subscription %s and setting subscription to pending", subscription.partner_id.email, subscription.id)
                                        msg_body += _(' E-mail sent to customer.')
                                    subscription.message_post(body=msg_body)
                                    subscription.set_to_renew()
                                    # remove the flag as we are done with this sub
                                    subscription.with_context(mail_notrack=True).write({'tag_ids': [(3, subscription_payment_exception_tag.id)]})
                            if auto_commit:
                                cr.commit()
                        except Exception:
                            if auto_commit:
                                cr.rollback()
                            # we assume that the payment is run only once a day
                            traceback_message = traceback.format_exc()
                            _logger.error(traceback_message)
                            last_tx = self.env['payment.transaction'].search([('reference', 'like', 'SUBSCRIPTION-%s-%s' % (subscription.id, datetime.date.today().strftime('%y%m%d')))], limit=1)
                            error_message = "Error during renewal of subscription %s (%s)" % (subscription.code, 'Payment recorded: %s' % last_tx.reference if last_tx and last_tx.state == 'done' else 'No payment recorded.')
                            _logger.error(error_message)

                    # invoice only
                    elif subscription.template_id.payment_mode in ['draft_invoice', 'manual', 'validate_send']:
                        try:
                            # We don't allow to create invoice past the end date of the contract.
                            # The subscription must be renewed in that case
                            if subscription.date and subscription.recurring_next_date >= subscription.date:
                                return
                            else:
                                invoice_values = subscription.with_context(invoice_ctx)._prepare_invoice()
                                new_invoice = Invoice.create(invoice_values)
                                if subscription.analytic_account_id or subscription.tag_ids:
                                    for line in new_invoice.invoice_line_ids:
                                        if subscription.analytic_account_id:
                                            line.analytic_account_id = subscription.analytic_account_id
                                        if subscription.tag_ids:
                                            line.analytic_tag_ids = subscription.tag_ids
                                new_invoice.message_post_with_view(
                                    'mail.message_origin_link',
                                    values={'self': new_invoice, 'origin': subscription},
                                    subtype_id=self.env.ref('mail.mt_note').id)
                                invoices += new_invoice
                                # When `recurring_next_date` is updated by cron or by `Generate Invoice` action button,
                                # write() will skip resetting `recurring_invoice_day` value based on this context value
                                subscription.with_context(skip_update_recurring_invoice_day=True).increment_period()
                                if subscription.template_id.payment_mode == 'validate_send':
                                    new_invoice.action_post()
                                if automatic and auto_commit:
                                    cr.commit()
                        except Exception:
                            if automatic and auto_commit:
                                cr.rollback()
                                _logger.exception('Fail to create recurring invoice for subscription %s', subscription.code)
                            else:
                                raise

        # Retrieve the invoice to send mails.
        self._cr.execute('''
            SELECT
                DISTINCT aml.move_id,
                move.date
            FROM account_move_line aml
            JOIN sale_subscription subscr ON subscr.id = aml.subscription_id
            JOIN sale_subscription_template subscr_tpl ON subscr_tpl.id = subscr.template_id
            JOIN account_move move ON move.id = aml.move_id
            WHERE move.state = 'posted'
                AND move.is_move_sent IS FALSE
                AND subscr_tpl.payment_mode = 'validate_send'
            ORDER BY move.date DESC
        ''')
        invoice_to_send_ids = [row[0] for row in self._cr.fetchall()]

        invoices_to_send = self.env['account.move'].browse(invoice_to_send_ids)
        for invoice in invoices_to_send:
            if invoice._is_ready_to_be_sent():
                subscription = invoice.line_ids.subscription_id[:1]  # Only select one in case of multiple subscriptions on the invoice
                subscription.validate_and_send_invoice(invoice)

        # There is still some subscriptions to process. Then, make sure the CRON will be triggered again asap.
        if need_cron_trigger:
            if config['test_enable'] or config['test_file']:
                # Test environnement: we launch the next iteration in the same thread
                self.env['sale.subscription']._recurring_create_invoice(automatic, batch_size)
            else:
                self.env.ref('sale_subscription.account_analytic_cron_for_invoice')._trigger()

        # If this is the last call of the cron and if the invalid_payment_tag is defined, we can remove the tag used
        # mark the payment failed subscriptions.
        if not need_cron_trigger and batch_tag:
            failing_subscriptions = self.search([('tag_ids', 'in', batch_tag.ids)])
            failing_subscriptions.write({'tag_ids': [Command.unlink(batch_tag.id)]})

        return invoices

    def send_success_mail(self, tx, invoice):
        current_date = datetime.date.today()
        next_date = self.recurring_next_date or current_date
        # if no recurring next date, have next invoice be today + interval
        if not self.recurring_next_date:
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
            next_date = next_date + invoicing_period
        email_context = self.env.context.copy()
        email_context.update({
            'payment_token': self.payment_token_id.name,
            'renewed': True,
            'total_amount': tx.amount,
            'next_date': next_date,
            'previous_date': self.recurring_next_date,
            'email_to': self.partner_id.email,
            'code': self.code,
            'currency': self.pricelist_id.currency_id.name,
            'date_end': self.date,
        })
        _logger.debug("Sending Payment Confirmation Mail to %s for subscription %s", self.partner_id.email, self.id)
        template = self.env.ref('sale_subscription.email_payment_success')

        # This function can be called by the public user via the callback_method set in
        # /my/subscription/transaction/. The email template contains the invoice PDF in
        # attachment, so to render it successfully sudo() is not enough.
        if self.env.su:
            template = template.with_user(SUPERUSER_ID)

        return template.with_context(email_context).send_mail(invoice.id)

    def validate_and_send_invoice(self, invoice):
        self.ensure_one()
        if invoice.state != 'posted':
            invoice._post(False)
        email_context = self.env.context.copy()
        email_context.update({
            'total_amount': invoice.amount_total,
            'email_to': self.partner_id.email,
            'code': self.code,
            'currency': self.pricelist_id.currency_id.name,
            'date_end': self.date,
            'mail_notify_force_send': False,
            'no_new_invoice': True,
        })
        _logger.debug("Sending Invoice Mail to %s for subscription %s", self.partner_id.email, self.id)
        invoice.with_context(email_context).message_post_with_template(self.template_id.invoice_mail_template_id.id)
        invoice.is_move_sent = True
        if hasattr(invoice, "attachment_ids") and invoice.attachment_ids:
            invoice._message_set_main_attachment_id([(4, id) for id in invoice.attachment_ids.ids])


class SaleSubscriptionLine(models.Model):
    _name = "sale.subscription.line"
    _description = "Subscription Line"
    _check_company_auto = True

    product_id = fields.Many2one(
        'product.product', string='Product', check_company=True,
        domain="[('recurring_invoice','=',True)]", required=True)
    analytic_account_id = fields.Many2one('sale.subscription', string='Subscription', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='analytic_account_id.company_id', store=True, index=True)
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', help="Quantity that will be invoiced.", default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')
    discount = fields.Float(string='Discount (%)', digits='Discount')
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', digits='Account', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='analytic_account_id.currency_id', store=True)

    @api.depends('quantity', 'discount', 'price_unit', 'analytic_account_id.pricelist_id', 'uom_id', 'company_id')
    def _compute_amount(self):
        """
        Compute the amounts of the Subscription line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.product_id.sudo().taxes_id.filtered(lambda tax: tax.company_id == line.company_id)
            amounts = taxes.compute_all(price, line.currency_id, line.quantity, product=line.product_id, partner=line.analytic_account_id.partner_id)
            line.update({
                'price_subtotal': amounts['total_excluded'],
            })

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id
        partner = self.analytic_account_id.partner_id
        if partner.lang:
            product = product.with_context(lang=partner.lang)

        self.name = product.get_product_multiline_description_sale()
        self.uom_id = product.uom_id.id

    @api.onchange('product_id', 'quantity')
    def onchange_product_quantity(self):
        if not self.product_id:
            self.price_unit = 0.0
        else:
            subscription = self.analytic_account_id
            pricelist = subscription.pricelist_id

            self = self.with_company(subscription.company_id)

            if not self.uom_id or self.product_id.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = self.product_id.uom_id.id

            product = self.product_id.with_context(
                pricelist=pricelist.id,
                quantity=self.quantity,
                uom=self.uom_id.id
            )
            pricelist_price = product.price     # Price according to pricelist in pricelist currency in self.uom
            base_price = product.lst_price      # Base price of the product in self.uom

            if product.currency_id != pricelist.currency_id:
                base_price = product.currency_id._convert(base_price, pricelist.currency_id, product.company_id or self.env.company, fields.Date.today())

            if pricelist.discount_policy == 'without_discount' and pricelist_price:
                discount = max(0, (base_price - pricelist_price) * 100 / base_price)
                price_unit = base_price
            else:
                price_unit = pricelist_price
                discount = 0

            self.update({
                'price_unit': price_unit,
                'discount': discount
            })

    @api.onchange('uom_id')
    def onchange_uom_id(self):
        if not self.uom_id:
            self.price_unit = 0.0
        else:
            return self.onchange_product_quantity()

    def get_template_option_line(self):
        """ Return the account.analytic.invoice.line.option which has the same product_id as
        the invoice line"""
        if not self.analytic_account_id and not self.analytic_account_id.template_id:
            return False
        template = self.analytic_account_id.template_id
        return template.sudo().subscription_template_option_ids.filtered(lambda r: r.product_id == self.product_id)

    def _amount_line_tax(self):
        self.ensure_one()
        partner = self.analytic_account_id.partner_id
        product_taxes = self.product_id.sudo().taxes_id.filtered(
            lambda t: t.company_id == self.analytic_account_id.company_id)
        fpos = self.env['account.fiscal.position'].with_company(
            self.analytic_account_id.company_id).get_fiscal_position(partner.id)
        taxes = fpos.map_tax(product_taxes)
        tax_values = taxes.compute_all(
            self.price_unit * (1 - (self.discount or 0.0) / 100.0),
            self.analytic_account_id.currency_id,
            self.quantity,
            self.product_id,
            partner)['taxes']
        return sum(tax.get('amount', 0.0) for tax in tax_values)

    @api.model
    def create(self, values):
        if values.get('product_id') and not values.get('name'):
            line = self.new(values)
            line.onchange_product_id()
            values['name'] = line._fields['name'].convert_to_write(line['name'], line)
        return super(SaleSubscriptionLine, self).create(values)


class SaleSubscriptionCloseReason(models.Model):
    _name = "sale.subscription.close.reason"
    _order = "sequence, id"
    _description = "Subscription Close Reason"

    name = fields.Char('Reason', required=True, translate=True)
    sequence = fields.Integer(default=10)


class SaleSubscriptionTemplate(models.Model):
    _name = "sale.subscription.template"
    _description = "Subscription Template"
    _inherit = "mail.thread"
    _check_company_auto = True

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char(help="Code is added automatically in the display name of every subscription.")
    description = fields.Html(translate=True, string="Terms and Conditions")
    recurring_rule_type = fields.Selection([('daily', 'Days'), ('weekly', 'Weeks'),
                                            ('monthly', 'Months'), ('yearly', 'Years'), ],
                                           string='Recurrence', required=True,
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', tracking=True)
    recurring_interval = fields.Integer(string="Invoicing Period", help="Repeat every (Days/Week/Month/Year)", required=True, default=1, tracking=True)
    recurring_rule_boundary = fields.Selection([
        ('unlimited', 'Forever'),
        ('limited', 'Fixed')
    ], string='Duration', default='unlimited')
    recurring_rule_count = fields.Integer(string="End After", default=1)

    # Read-only copy of recurring_rule_type for proper readability of recurrence limitation:
    recurring_rule_type_readonly = fields.Selection(
        string="Recurrence Unit",
        related='recurring_rule_type', readonly=True, tracking=False)

    user_closable = fields.Boolean(string="Closable by Customer", help="If checked, the user will be able to close his account from the frontend")
    payment_mode = fields.Selection([
        ('manual', 'Manually'),
        ('draft_invoice', 'Draft'),
        ('validate_send', 'Post'),
        ('success_payment', 'Send after successful payment'),
    ], required=True, default='draft_invoice')
    product_ids = fields.One2many('product.template', 'subscription_template_id', copy=True)
    journal_id = fields.Many2one(
        'account.journal', string="Accounting Journal",
        domain="[('type', '=', 'sale')]", company_dependent=True, check_company=True,
        help="If set, subscriptions with this template will invoice in this journal; "
        "otherwise the sales journal with the lowest sequence is used.")
    tag_ids = fields.Many2many(
        'account.analytic.tag', 'sale_subscription_template_tag_rel',
        'template_id', 'tag_id', string='Tags', help="Use these tags to filter your subscription reporting",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_count = fields.Integer(compute='_compute_product_count')
    subscription_count = fields.Integer(compute='_compute_subscription_count')
    color = fields.Integer()
    auto_close_limit = fields.Integer(
        string="Automatic Closing", default=15,
        help="If the chosen payment method has failed to renew the subscription after this time, "
             "the subscription is automatically closed.")
    good_health_domain = fields.Char(string='Good Health', default='[]',
                                     help="Domain used to change subscription's Kanban state with a 'Good' rating")
    bad_health_domain = fields.Char(string='Bad Health', default='[]',
                                    help="Domain used to change subscription's Kanban state with a 'Bad' rating")
    invoice_mail_template_id = fields.Many2one(
        'mail.template', string='Invoice Email Template', domain=[('model', '=', 'account.move')],
        default=lambda self: self.env.ref('sale_subscription.mail_template_subscription_invoice', raise_if_not_found=False))
    company_id = fields.Many2one('res.company', index=True)

    @api.constrains('recurring_interval')
    def _check_recurring_interval(self):
        for template in self:
            if template.recurring_interval <= 0:
                raise ValidationError(_("The recurring interval must be positive"))

    def _compute_subscription_count(self):
        subscription_data = self.env['sale.subscription'].read_group(domain=[('template_id', 'in', self.ids), ('stage_id', '!=', False)],
                                                                     fields=['template_id'],
                                                                     groupby=['template_id'])
        mapped_data = dict([(m['template_id'][0], m['template_id_count']) for m in subscription_data])
        for template in self:
            template.subscription_count = mapped_data.get(template.id, 0)

    def _compute_product_count(self):
        product_data = self.env['product.template'].sudo().read_group([('subscription_template_id', 'in', self.ids)], ['subscription_template_id'], ['subscription_template_id'])
        result = dict((data['subscription_template_id'][0], data['subscription_template_id_count']) for data in product_data)
        for template in self:
            template.product_count = result.get(template.id, 0)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('code', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        res = []
        for sub in self:
            name = '%s - %s' % (sub.code, sub.name) if sub.code else sub.name
            res.append((sub.id, name))
        return res


class SaleSubscriptionStage(models.Model):
    _name = 'sale.subscription.stage'
    _description = 'Subscription Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(
        "Requirements", help="Enter here the internal requirements for this stage. It will appear "
                             "as a tooltip over the stage's name.", translate=True)
    sequence = fields.Integer(default=1)
    fold = fields.Boolean(string='Folded in Kanban',
                          help='This stage is folded in the kanban view when there are no records in that stage to display.')
    rating_template_id = fields.Many2one('mail.template', string='Rating Email Template',
                                         help="Send an email to the customer when the subscription is moved to this stage.",
                                         domain=[('model', '=', 'sale.subscription')])
    category = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('closed', 'Closed')], required=True, default='draft', help="Category of the stage")


class SaleSubscriptionLog(models.Model):
    _name = 'sale.subscription.log'
    _description = 'Subscription Log'
    _order = 'event_date desc, id desc'

    subscription_id = fields.Many2one(
        'sale.subscription', string='Subscription',
        required=True, ondelete='cascade', readonly=True
        )
    create_date = fields.Datetime(string='Date', readonly=True)
    event_type = fields.Selection(
        string='Type of event',
        selection=[('0_creation', 'Creation'), ('1_change', 'Change in MRR'), ('2_churn', 'Churn')],
        required=True, readonly=True,)
    recurring_monthly = fields.Monetary(string='MRR after Change', required=True,
                                        help="MRR, after applying the changes of that particular event",
                                        group_operator=None, readonly=True)
    category = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('closed', 'Closed')], required=True, default='draft', help="Subscription stage category when the change occurred")

    user_id = fields.Many2one('res.users', string='Salesperson')
    team_id = fields.Many2one('crm.team', string='Sales Team', ondelete="set null")
    amount_signed = fields.Monetary(string='Change in MRR', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    amount_company_currency = fields.Monetary(
        string='Change in MRR (company currency)', currency_field='company_currency_id',
        compute="_compute_amount_company_currency", store=True,
        readonly=True
    )
    event_date = fields.Date(string='Event Date', required=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', related='company_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related='subscription_id.company_id', store=True, readonly=True)

    @api.depends('company_id', 'company_currency_id', 'amount_signed', 'event_date')
    def _compute_amount_company_currency(self):
        for log in self:
            log.amount_company_currency = log.currency_id._convert(
                from_amount=log.amount_signed,
                to_currency=log.company_currency_id,
                date=log.event_date,
                company=log.company_id
            )

class SaleSubscriptionAlert(models.Model):
    _name = 'sale.subscription.alert'
    _description = 'Subscription Alert'
    _inherits = {'base.automation': 'automation_id'}
    _check_company_auto = True

    @api.model
    def default_get(self, default_fields):
        res = super(SaleSubscriptionAlert, self).default_get(default_fields)
        if 'model_id' in default_fields:
            # model_id default cannot be specified at field level
            # because model_id is an inherited field from base.automation
            res['model_id'] = self.env['ir.model']._get_id('sale.subscription')
        return res

    automation_id = fields.Many2one('base.automation', 'Automated Action', required=True, ondelete='restrict')
    action = fields.Selection([
        ('next_activity', 'Create next activity'),
        ('set_tag', 'Set a tag on the subscription'),
        ('set_stage', 'Set a stage on the subscription'),
        ('set_to_renew', 'Mark as To Renew'),
        ('email', 'Send an email to the customer'),
        ('sms', 'Send an SMS Text Message to the customer'),
    ], string='Action', required=True, default=None)
    trigger_condition = fields.Selection([
        ('on_create_or_write', 'Modification'),
        ('on_time', 'Timed Condition'),
    ], string='Trigger On', required=True, default='on_create_or_write')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    subscription_template_ids = fields.Many2many(
        'sale.subscription.template', string='Subscription Templates',
        check_company=True)
    customer_ids = fields.Many2many('res.partner', string='Customers')
    company_id = fields.Many2one('res.company', string='Company')
    mrr_min = fields.Monetary('MRR Range Min', currency_field='currency_id', help="Monthly Recurring Revenue")
    team_ids = fields.Many2many('crm.team', string='Sales Team')
    mrr_max = fields.Monetary('MRR Range Max', currency_field='currency_id')
    product_ids = fields.Many2many(
        'product.product', string='Specific Products',
        domain="[('product_tmpl_id.subscription_template_id', '!=', None), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    mrr_change_amount = fields.Float('MRR Change Amount')
    mrr_change_unit = fields.Selection(selection='_get_selection_mrr_change_unit', string='MRR Change Unit', default='percentage')
    mrr_change_period = fields.Selection([('1month', '1 Month'), ('3months', '3 Months')], string='MRR Change Period',
                                         default='1month', help="Period over which the KPI is calculated")
    rating_percentage = fields.Integer('Rating Percentage', help="Rating Satisfaction is the ratio of positive rating to total number of rating.")
    rating_operator = fields.Selection([('>', 'greater than'), ('<', 'less than')], string='Rating Operator', default='>')
    stage_from_id = fields.Many2one('sale.subscription.stage', help="Trigger on changes of stage. Trigger over all stages if not set")
    stage_to_id = fields.Many2one('sale.subscription.stage')

    tag_id = fields.Many2one('account.analytic.tag', string='Tag')
    stage_id = fields.Many2one('sale.subscription.stage', string='Stage')
    activity_user = fields.Selection([
        ('contract', 'Subscription Salesperson'),
        ('channel_leader', 'Sales Team Leader'),
        ('users', 'Specific Users'),
    ], string='Assign To')
    activity_user_ids = fields.Many2many('res.users', string='Specific Users')

    subscription_count = fields.Integer(compute='_compute_subscription_count')
    cron_nextcall = fields.Datetime(compute='_compute_nextcall', store=False)

    def _get_selection_mrr_change_unit(self):
        return [('percentage', '%'), ('currency', self.env.company.currency_id.symbol)]

    def _compute_subscription_count(self):
        for alert in self:
            domain = literal_eval(alert.filter_domain) if alert.filter_domain else []
            alert.subscription_count = self.env['sale.subscription'].search_count(domain)

    def _configure_filter_domain(self):
        for alert in self:
            domain = []
            if alert.subscription_template_ids:
                domain += [('template_id', 'in', alert.subscription_template_ids.ids)]
            if alert.customer_ids:
                domain += [('partner_id', 'in', alert.customer_ids.ids)]
            if alert.team_ids:
                domain += [('team_id', 'in', alert.team_ids.ids)]
            if alert.company_id:
                domain += [('company_id', '=', alert.company_id.id)]
            if alert.mrr_min:
                domain += [('recurring_monthly', '>=', alert.mrr_min)]
            if alert.mrr_max:
                domain += [('recurring_monthly', '<=', alert.mrr_max)]
            if alert.product_ids:
                domain += [('recurring_invoice_line_ids.product_id', 'in', alert.product_ids.ids)]
            if alert.mrr_change_amount:
                if alert.mrr_change_unit == 'percentage':
                    domain += [('kpi_%s_mrr_percentage' % (alert.mrr_change_period), '>', alert.mrr_change_amount / 100)]
                else:
                    domain += [('kpi_%s_mrr_delta' % (alert.mrr_change_period), '>', alert.mrr_change_amount)]
            if alert.rating_percentage:
                domain += [('percentage_satisfaction', alert.rating_operator, alert.rating_percentage)]
            if alert.stage_to_id:
                domain += [('stage_id', '=', alert.stage_to_id.id)]
            super(SaleSubscriptionAlert, alert).write({'filter_domain': domain})

    def unlink(self):
        for record in self:
            record.automation_id.active = False
        return super(SaleSubscriptionAlert, self).unlink()

    def _configure_filter_pre_domain(self):
        for alert in self:
            if alert.stage_from_id:
                domain = [('stage_id', '=', alert.stage_from_id.id)]
            else:
                domain = []
            super(SaleSubscriptionAlert, alert).write({'filter_pre_domain': domain})

    def _configure_alert_from_action(self, vals):
        # Unlink the children server actions if not needed anymore
        self.filtered(lambda alert: alert.action != 'next_activity' and alert.child_ids).unlink()
        for alert in self:
            if alert.action == 'set_tag' and alert.tag_id:
                alert._set_field_action('tag_ids', [(4, alert.tag_id.id, False)])
            elif alert.action == 'set_stage' and alert.stage_id:
                alert._set_field_action('stage_id', alert.stage_id.id)
            elif alert.action == 'set_to_renew':
                alert._set_field_action('to_renew', True)
            elif vals.get('action') in ('email', 'sms'):
                super(SaleSubscriptionAlert, alert).write({'state': vals.get('action')})
            elif vals.get('action') == 'next_activity' or vals.get('activity_user_ids') or vals.get('activity_user'):
                alert.set_activity_action()

    @api.model
    def create(self, vals):
        if vals.get('trigger_condition'):
            vals['trigger'] = vals['trigger_condition']
        res = super(SaleSubscriptionAlert, self).create(vals)
        res._configure_filter_domain()
        res._configure_filter_pre_domain()
        res._configure_alert_from_action(vals)
        return res

    def write(self, vals):
        if vals.get('trigger_condition'):
            vals['trigger'] = vals['trigger_condition']
        res = super(SaleSubscriptionAlert, self).write(vals)
        self._configure_filter_domain()
        self._configure_filter_pre_domain()
        self._configure_alert_from_action(vals)
        return res

    def action_view_subscriptions(self):
        self.ensure_one()
        domain = literal_eval(self.filter_domain) if self.filter_domain else []
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'sale.subscription',
            'view_mode': 'kanban,tree,form,pivot,graph,cohort,activity',
            'domain': domain,
            'context': {'create': False},
        }

    def run_cron_manually(self):
        self.ensure_one()
        domain = literal_eval(self.filter_domain)
        subs = self.env['sale.subscription'].search(domain)
        ctx = {
            'active_model': 'sale.subscription',
            'active_ids': subs.ids,
            'domain_post': domain,
        }
        self.action_server_id.with_context(**ctx).run()

    def _set_field_action(self, field_name, value):
        for alert in self.sudo():  # Require sudo to write on ir.actions.server fields
            tag_field = self.env['ir.model.fields'].search([('model', '=', alert.model_name), ('name', '=', field_name)])
            super(SaleSubscriptionAlert, alert).write({
                'state': 'object_write',
                'fields_lines': [(5, 0, 0), (0, False, {
                    'evaluation_type': 'equation',
                    'col1': tag_field.id,
                    'value': value})
                ]})

    def set_activity_action(self):
        for alert in self:
            alert.child_ids.unlink()
            if self.activity_user == 'users':
                action_ids = []
                for user in alert.activity_user_ids:
                    seq = len(action_ids)
                    action = self.env['ir.actions.server'].create({
                        'name': '%s-%s' % (alert.name, seq),
                        'sequence': seq,
                        'state': 'next_activity',
                        'model_id': alert.model_id.id,
                        'activity_summary': alert.activity_summary,
                        'activity_type_id': alert.activity_type_id.id,
                        'activity_note': alert.activity_note,
                        'activity_date_deadline_range': alert.activity_date_deadline_range,
                        'activity_date_deadline_range_type': alert.activity_date_deadline_range_type,
                        'activity_user_type': 'specific',
                        'activity_user_id': user.id,
                        'usage': 'base_automation',
                    })
                    action_ids.append(action.id)
                alert.write({
                    'state': 'multi',
                    'child_ids': [(6, False, action_ids)],
                })
            elif self.activity_user == 'contract':
                alert.write({
                    'state': 'next_activity',
                    'activity_user_type': 'generic',
                    'activity_user_field_name': 'user_id',
                })
            elif self.activity_user == 'channel_leader':
                alert.write({
                    'state': 'next_activity',
                    'activity_user_type': 'generic',
                    'activity_user_field_name': 'team_user_id',
                })

    def _compute_nextcall(self):
        cron = self.env.ref('sale_subscription.ir_cron_sale_subscription_update_kpi', raise_if_not_found=False)
        if not cron:
            self.update({'cron_nextcall': False})
        else:
            nextcall = cron.read(fields=['nextcall'])[0]
            self.update({'cron_nextcall': fields.Datetime.to_string(nextcall['nextcall'])})
