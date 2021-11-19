# -*- coding: utf-8 -*-
from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _update_translations(self, filter_lang=None, overwrite=False):
        """ Create missing translations after loading the one of account.financial.html.report

        Use the translations of the account.financial.html.report to translate the linked
        ir.actions.client and ir.ui.menu generated at the creation of the report
        """
        res = super(IrModuleModule, self)._update_translations(filter_lang=filter_lang, overwrite=overwrite)

        # generated missing action translations for translated reports
        self.env.cr.execute("""
           INSERT INTO ir_translation (lang, type, name, res_id, src, value, module, state)
           SELECT DISTINCT ON (l.code, a.id) l.code, 'model', 'ir.actions.client,name', a.id, t.src, t.value, t.module, t.state
             FROM account_financial_html_report r
             JOIN ir_ui_menu menu ON menu.id = r.generated_menu_id
             JOIN ir_act_client a ON a.id = CAST(SPLIT_PART(menu.action, ',', 2) AS INTEGER)
             JOIN ir_translation t ON (t.res_id = r.id AND t.name = 'account.financial.html.report,name')
             JOIN res_lang l on  (l.code = t.lang)
            WHERE NOT EXISTS (
                  SELECT 1 FROM ir_translation tt
                  WHERE (tt.name = 'ir.actions.client,name'
                    AND tt.lang = l.code
                    AND type='model'
                    AND tt.res_id = a.id)
                  )
        """)

        # generated missing menu translations for translated reports
        self.env.cr.execute("""
           INSERT INTO ir_translation (lang, type, name, res_id, src, value, module, state)
           SELECT DISTINCT ON (l.code, menu.id) l.code, 'model', 'ir.ui.menu,name', menu.id, t.src, t.value, t.module, t.state
             FROM account_financial_html_report r
             JOIN ir_ui_menu menu ON menu.id = r.generated_menu_id
             JOIN ir_translation t ON (t.res_id = r.id AND t.name = 'account.financial.html.report,name')
             JOIN res_lang l on  (l.code = t.lang)
            WHERE NOT EXISTS (
                  SELECT 1 FROM ir_translation tt
                  WHERE (tt.name = 'ir.ui.menu,name'
                    AND tt.lang = l.code
                    AND type='model'
                    AND tt.res_id = menu.id)
                  )
        """)

        return res
