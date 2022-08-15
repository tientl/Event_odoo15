# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, models, fields


class Task(models.Model):
    _inherit = 'project.task'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', help='Ticket this task was generated from', readonly=True)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'helpdesk_ticket_id'}

    def action_view_ticket(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'form',
            'res_id': self.helpdesk_ticket_id.id,
        }

    def write(self, vals):
        previous_states = None
        if 'fsm_done' in vals:
            previous_states = {task: task.fsm_done for task in self}
        res = super().write(vals)
        if 'fsm_done' in vals:
            tracked_tasks = self.filtered(
                lambda t: t.fsm_done and t.helpdesk_ticket_id.use_fsm and previous_states[t] != t.fsm_done)
            subtype_id = self.env.ref('helpdesk_fsm.mt_ticket_task_done')
            for task in tracked_tasks:
                body = '<a href="#" data-oe-model="project.task" data-oe-id="%s">%s</a>' % (task.id, task.display_name)
                task.helpdesk_ticket_id.sudo().message_post(subtype_id=subtype_id.id, body=body)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks.filtered('helpdesk_ticket_id'):
            task.message_post_with_view('helpdesk.ticket_creation', values={'self': task, 'ticket': task.helpdesk_ticket_id}, subtype_id=self.env.ref('mail.mt_note').id)
        return tasks
