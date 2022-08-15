# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def register_as_main_attachment(self, force=True):
        """Add the automatic scanning of attachments when registered as main.
           To avoid double scanning after message_post, we check that the automatic scanning is only made the first time.
        """
        self.ensure_one()
        super(IrAttachment, self).register_as_main_attachment(force=force)

        if self.res_model == 'hr.expense' and self.env.company.expense_extract_show_ocr_option_selection == 'auto_send':
            related_record = self.env[self.res_model].browse(self.res_id)
            if related_record.extract_state == "no_extract_requested" and not related_record.sample:
                related_record.retry_ocr()
