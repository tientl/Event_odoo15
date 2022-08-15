from odoo import models


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_vat_report_attachments(self, options):
        attachments = super()._get_vat_report_attachments(options)

        # Add the XML along with other attachments when the VAT report is posted
        if self.env.company.account_fiscal_country_id.code == 'BE':
            xml = self.get_xml(options)
            attachments.append(('vat_report.xml', xml))

        return attachments
