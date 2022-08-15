# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class CalendarAppointmentQuestion(models.Model):
    _name = "calendar.appointment.question"
    _description = "Online Appointment : Questions"
    _order = "sequence"

    sequence = fields.Integer('Sequence')
    appointment_type_id = fields.Many2one('calendar.appointment.type', 'Appointment Type', ondelete="cascade")
    name = fields.Char('Question', translate=True, required=True)
    placeholder = fields.Char('Placeholder', translate=True)
    question_required = fields.Boolean('Required Answer')
    question_type = fields.Selection([
        ('char', 'Single line text'),
        ('text', 'Multi-line text'),
        ('select', 'Dropdown (one answer)'),
        ('radio', 'Radio (one answer)'),
        ('checkbox', 'Checkboxes (multiple answers)')], 'Question Type', default='char')
    answer_ids = fields.Many2many('calendar.appointment.answer', 'calendar_appointment_question_answer_rel', 'question_id', 'answer_id', string='Available Answers')


class CalendarAppointmentAnswer(models.Model):
    _name = "calendar.appointment.answer"
    _description = "Online Appointment : Answers"

    question_id = fields.Many2many('calendar.appointment.question', 'calendar_appointment_question_answer_rel', 'answer_id', 'question_id', string='Questions')
    name = fields.Char('Answer', translate=True, required=True)
