# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountTaxReport(models.Model):
    _inherit = 'account.tax.report'

    # https://eservices.minfin.fgov.be/intervat/static/help/FR/regles_de_validation_d_une_declaration.htm
    # The numerotation in the comments is extended here if it wasn't done in the
    # source document: ... X, Y, Z, AA, AB, AC, ...
    def get_checks_to_perform(self, amounts, carried_over):
        if self.id == self.env['ir.model.data']._xmlid_to_res_id('l10n_be.tax_report_vat'):
            return [
                # code 13.
                (_('Not allowed negative amounts'),
                    not all(v >= 0 for v in amounts.values())),
                # Code C
                (_('[55] > 0 if [86] > 0 or [88] > 0'),
                    min(0.0, amounts['c55']) if amounts['c86'] > 0 or amounts['c88'] > 0 else False),
                # Code D
                (_('[56] + [57] > 0 if [87] > 0'),
                    min(0.0, amounts['c55']) if amounts['c86'] > 0 or amounts['c88'] > 0 else False),
                # Code O
                ('[01] * 6% + [02] * 12% + [03] * 21% = [54]',
                 amounts['c01'] * 0.06 + amounts['c02'] * 0.12 + amounts['c03'] * 0.21 - amounts['c54'] if abs(amounts['c01'] * 0.06 + amounts['c02'] * 0.12 + amounts['c03'] * 0.21 - amounts['c54']) > 62 else False),
                # Code P
                ('([84] + [86] + [88]) * 21% >= [55]',
                    min(0.0, (amounts['c84'] + amounts['c86'] + amounts['c88']) * 0.21 - amounts['c55']) if min(0.0, (amounts['c84'] + amounts['c86'] + amounts['c88']) * 0.21 - amounts['c55']) < -62 else False),
                # Code Q
                ('([85] + [87]) * 21% >= ([56] + [57])',
                    min(0.0, (amounts['c85'] + amounts['c87']) * 0.21 - (amounts['c56'] + amounts['c57'])) if min(0.0, (amounts['c85'] + amounts['c87']) * 0.21 - (amounts['c56'] + amounts['c57'])) < -62 else False),
                # Code S
                ('([81] + [82] + [83] + [84] + [85]) * 50% >= [59]',
                    min(0.0, (amounts['c81'] + amounts['c82'] + amounts['c83'] + amounts['c84'] + amounts['c85']) * 0.5 - amounts['c59'])),
                # Code T
                ('[85] * 21% >= [63]',
                    min(0.0, amounts['c85'] * 0.21 - amounts['c63']) if min(0.0, amounts['c85'] * 0.21 - amounts['c63']) < -62 else False),
                # Code U
                ('[49] * 21% >= [64]',
                    min(0.0, amounts['c49'] * 0.21 - amounts['c64']) if min(0.0, amounts['c49'] * 0.21 - amounts['c64']) < -62 else False),
                # Code AC
                (_('[88] < ([81] + [82] + [83] + [84]) * 100 if [88] > 99.999'),
                    max(0.0, amounts['c88'] - (amounts['c81'] + amounts['c82'] + amounts['c83'] + amounts['c84']) * 100) if amounts['c88'] > 99999 else False),
                # Code AD
                (_('[44] < ([00] + [01] + [02] + [03] + [45] + [46] + [47] + [48] + [49]) * 200 if [44] > 99.999'),
                    max(0.0, amounts['c44'] - (amounts['c00'] + amounts['c01'] + amounts['c02'] + amounts['c03'] + amounts['c45'] + amounts['c46L'] + amounts['c46T'] + amounts['c47'] + amounts['c48s44'] + amounts['c48s46L'] + amounts['c48s46T'] + amounts['c49']) * 200) if amounts['c44'] > 99999 else False),
            ]
        return super(AccountTaxReport, self).get_checks_to_perform(amounts, carried_over)
