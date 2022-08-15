# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _lt

class Project(models.Model):
    _inherit = 'project.project'

    subscriptions_count = fields.Integer('# Subscriptions', compute='_compute_subscriptions_count', groups='sale_subscription.group_sale_subscription_view')

    @api.depends('analytic_account_id')
    def _compute_subscriptions_count(self):
        subscriptions_data = self.env['sale.subscription'].read_group([
            ('analytic_account_id', '!=', False),
            ('analytic_account_id', 'in', self.analytic_account_id.ids)
        ], ['analytic_account_id'], ['analytic_account_id'])
        mapped_data = {data['analytic_account_id'][0]: data['analytic_account_id_count'] for data in subscriptions_data}
        for project in self:
            project.subscriptions_count = mapped_data.get(project.analytic_account_id.id, 0)

    # -------------------------------------------
    # Actions
    # -------------------------------------------

    def action_open_project_subscriptions(self):
        self.ensure_one()
        subscriptions = self.env['sale.subscription'].search([
            ('analytic_account_id', '!=', False),
            ('analytic_account_id', 'in', self.analytic_account_id.ids)
        ])
        action = self.env["ir.actions.actions"]._for_xml_id("sale_subscription.sale_subscription_action")
        action_context = {'default_analytic_account_id': self.analytic_account_id.id}
        if self.commercial_partner_id:
            action_context['default_partner_id'] = self.commercial_partner_id.id
        action.update({
            'views': [[False, 'tree'], [False, 'form'], [False, 'pivot'], [False, 'graph'], [False, 'cohort']],
            'context': action_context,
            'domain': [('id', 'in', subscriptions.ids)]
        })
        if(len(subscriptions) == 1):
            action["views"] = [[False, 'form']]
            action["res_id"] = subscriptions.id
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('sale_subscription.group_sale_subscription_view'):
            buttons.append({
                'icon': 'refresh',
                'text': _lt('Subscriptions'),
                'number': self.subscriptions_count,
                'action_type': 'object',
                'action': 'action_open_project_subscriptions',
                'show': self.subscriptions_count > 0,
                'sequence': 12,
            })
        return buttons
