# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

from collections import defaultdict


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    _check_company_auto = True

    @api.model
    def _read_group_request_status(self, stages, domain, order):
        request_status_list = dict(self._fields['request_status'].selection).keys()
        return request_status_list

    name = fields.Char(string="Approval Subject", tracking=True)
    category_id = fields.Many2one('approval.category', string="Category", required=True)
    category_image = fields.Binary(related='category_id.image')
    approver_ids = fields.One2many('approval.approver', 'request_id', string="Approvers", check_company=True,
        compute='_compute_approver_ids', store=True, readonly=False)
    company_id = fields.Many2one(
        string='Company', related='category_id.company_id',
        store=True, readonly=True, index=True)
    date = fields.Datetime(string="Date")
    date_start = fields.Datetime(string="Date start")
    date_end = fields.Datetime(string="Date end")
    quantity = fields.Float(string="Quantity")
    location = fields.Char(string="Location")
    date_confirmed = fields.Datetime(string="Date Confirmed")
    partner_id = fields.Many2one('res.partner', string="Contact", check_company=True)
    reference = fields.Char(string="Reference")
    amount = fields.Float(string="Amount")
    reason = fields.Html(string="Description")
    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel'),
    ], default="new", compute="_compute_request_status",
        store=True, tracking=True,
        group_expand='_read_group_request_status')
    request_owner_id = fields.Many2one('res.users', string="Request Owner",
        check_company=True, domain="[('company_ids', 'in', company_id)]")
    user_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], compute="_compute_user_status")
    has_access_to_request = fields.Boolean(string="Has Access To Request", compute="_compute_has_access_to_request")
    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')
    product_line_ids = fields.One2many('approval.product.line', 'approval_request_id', check_company=True)

    has_date = fields.Selection(related="category_id.has_date")
    has_period = fields.Selection(related="category_id.has_period")
    has_quantity = fields.Selection(related="category_id.has_quantity")
    has_amount = fields.Selection(related="category_id.has_amount")
    has_reference = fields.Selection(related="category_id.has_reference")
    has_partner = fields.Selection(related="category_id.has_partner")
    has_payment_method = fields.Selection(related="category_id.has_payment_method")
    has_location = fields.Selection(related="category_id.has_location")
    has_product = fields.Selection(related="category_id.has_product")
    requirer_document = fields.Selection(related="category_id.requirer_document")
    approval_minimum = fields.Integer(related="category_id.approval_minimum")
    approval_type = fields.Selection(related="category_id.approval_type")
    automated_sequence = fields.Boolean(related="category_id.automated_sequence")

    def _compute_has_access_to_request(self):
        is_approval_user = self.env.user.has_group('approvals.group_approval_user')
        for request in self:
            request.has_access_to_request = request.request_owner_id == self.env.user and is_approval_user

    def _compute_attachment_number(self):
        domain = [('res_model', '=', 'approval.request'), ('res_id', 'in', self.ids)]
        attachment_data = self.env['ir.attachment'].read_group(domain, ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for request in self:
            request.attachment_number = attachment.get(request.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            category = 'category_id' in vals and self.env['approval.category'].browse(vals['category_id'])
            if category and category.automated_sequence:
                vals['name'] = category.sequence_id.next_by_id()
        return super().create(vals_list)

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'approval.request'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'approval.request', 'default_res_id': self.id}
        return res

    def action_confirm(self):
        # make sure that the manager is present in the list if he is required
        self.ensure_one()
        if self.category_id.manager_approval == 'required':
            employee = self.env['hr.employee'].search([('user_id', '=', self.request_owner_id.id)], limit=1)
            if not employee.parent_id:
                raise UserError(_('This request needs to be approved by your manager. There is no manager linked to your employee profile.'))
            if not employee.parent_id.user_id:
                raise UserError(_('This request needs to be approved by your manager. There is no user linked to your manager.'))
            if not self.approver_ids.filtered(lambda a: a.user_id.id == employee.parent_id.user_id.id):
                raise UserError(_('This request needs to be approved by your manager. Your manager is not in the approvers list.'))
        if len(self.approver_ids) < self.approval_minimum:
            raise UserError(_("You have to add at least %s approvers to confirm your request.", self.approval_minimum))
        if self.requirer_document == 'required' and not self.attachment_number:
            raise UserError(_("You have to attach at lease one document."))
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        approvers._create_activity()
        approvers.write({'status': 'pending'})
        self.write({'date_confirmed': fields.Datetime.now()})

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'approval.request'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('approvals.mail_activity_data_approval').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities

    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

    def action_refuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'refused'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

    def action_withdraw(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'pending'})

    def action_draft(self):
        self.mapped('approver_ids').write({'status': 'new'})

    def action_cancel(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        self.mapped('approver_ids').write({'status': 'cancel'})

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            approval.user_status = approval.approver_ids.filtered(lambda approver: approver.user_id == self.env.user).status

    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('approver_ids.status')
            required_statuses = request.approver_ids.filtered('required').mapped('status')
            required_approved = required_statuses.count('approved') == len(required_statuses)
            minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)
            if status_lst:
                if status_lst.count('cancel'):
                    status = 'cancel'
                elif status_lst.count('refused'):
                    status = 'refused'
                elif status_lst.count('new'):
                    status = 'new'
                elif status_lst.count('approved') >= minimal_approver and required_approved:
                    status = 'approved'
                else:
                    status = 'pending'
            else:
                status = 'new'
            request.request_status = status

    @api.depends('category_id', 'request_owner_id')
    def _compute_approver_ids(self):
        for request in self:
            #Don't remove manually added approvers
            users_to_approver = defaultdict(lambda: self.env['approval.approver'])
            for approver in request.approver_ids:
                users_to_approver[approver.user_id.id] |= approver
            users_to_category_approver = defaultdict(lambda: self.env['approval.category.approver'])
            for approver in request.category_id.approver_ids:
                users_to_category_approver[approver.user_id.id] |= approver
            new_users = request.category_id.user_ids
            manager_user = 0
            if request.category_id.manager_approval:
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee.parent_id.user_id:
                    new_users |= employee.parent_id.user_id
                    manager_user = employee.parent_id.user_id.id
            approver_id_vals = []
            for user in new_users:
                # Force require on the manager if he is explicitely in the list
                required = users_to_category_approver[user.id].required or \
                    (request.category_id.manager_approval == 'required' if manager_user == user.id else False)
                current_approver = users_to_approver[user.id]
                if current_approver and current_approver.required != required:
                    approver_id_vals.append(Command.update(current_approver.id, {'required': required}))
                elif not current_approver:
                    approver_id_vals.append(Command.create({
                        'user_id': user.id,
                        'status': 'new',
                        'required': required,
                    }))
            request.update({'approver_ids': approver_id_vals})

class ApprovalApprover(models.Model):
    _name = 'approval.approver'
    _description = 'Approver'

    _check_company_auto = True

    user_id = fields.Many2one('res.users', string="User", required=True, check_company=True, domain="[('id', 'not in', existing_request_user_ids)]")
    existing_request_user_ids = fields.Many2many('res.users', compute='_compute_existing_request_user_ids')
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string="Status", default="new", readonly=True)
    request_id = fields.Many2one('approval.request', string="Request",
        ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        string='Company', related='request_id.company_id',
        store=True, readonly=True, index=True)
    required = fields.Boolean(default=False, readonly=True)
    can_edit = fields.Boolean(compute='_compute_can_edit')

    def action_approve(self):
        self.request_id.action_approve(self)

    def action_refuse(self):
        self.request_id.action_refuse(self)

    def _create_activity(self):
        for approver in self:
            approver.request_id.activity_schedule(
                'approvals.mail_activity_data_approval',
                user_id=approver.user_id.id)

    @api.depends('request_id.request_owner_id', 'request_id.approver_ids.user_id')
    def _compute_existing_request_user_ids(self):
        for approver in self:
            approver.existing_request_user_ids = \
                self.mapped('request_id.approver_ids.user_id')._origin \
              | self.request_id.request_owner_id._origin

    @api.depends_context('uid')
    def _compute_can_edit(self):
        self.update({'can_edit': self.env.user.has_group('approvals.group_approval_user')})
