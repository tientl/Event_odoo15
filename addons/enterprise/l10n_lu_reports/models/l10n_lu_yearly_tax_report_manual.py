# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

class L10nLuYearlyTaxReportManual(models.Model):
    """
    This wizard is used to store the data typical of Luxembourg's yearly tax report
    that can't be automatically inferred, but must be manually entered by the user.
    """
    _name = 'l10n_lu.yearly.tax.report.manual'
    _description = 'Yearly tax report manual data'
    _sql_constraints = [
        ('year_unique', 'unique(company_id, year)', _('Only one tax report data record per year (per company) is allowed!'))
    ]

    company_id = fields.Many2one('res.company', required=True)
    year = fields.Char(required=True)
    avg_nb_employees = fields.Float(string="Average number of employees for the fiscal year",
                                    compute="_compute_avg_nb_employees")
    avg_nb_employees_with_salary = fields.Float("  - with salary or wage")
    avg_nb_employees_with_no_salary = fields.Float("  - with no salary (family members)")
    phone_number = fields.Char(string="Phone number for contacting the declaring person", size=30)
    books_records_documents = fields.Char(
        string="Books, records and documents",
        help="Taxable persons established in Luxembourg: place of storage of books, records and documents the keeping, "
             "drafting and issuing of which are required by the modified VAT law of 12 February 1979 and its "
             "implementing provisions, when this place of storage is outside of the territory of Luxemburg (Art. 65)",
        size=30
    )
    submitted_rcs = fields.Boolean(string="Annual accounts submitted to the Trade and Companies Register (RCS)")

    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, _('Yearly Tax Report Manual Data') + ' (' + str(r.company_id.name) + ') ' + r.year))
        return result

    @api.depends("avg_nb_employees_with_salary", "avg_nb_employees_with_no_salary")
    def _compute_avg_nb_employees(self):
        self.avg_nb_employees = self.avg_nb_employees_with_no_salary + self.avg_nb_employees_with_salary

    # Yearly report fields: some fields in the yearly report are splits of fields in the monthly report;
    # since the taxes + tax tags in the LU localization are based on the monthly report,
    # there is no way to know how to split the amounts from the monthly report to the yearly report without user input.

    # Field 472 (Sales/Receipts) split
    report_section_001 = fields.Float()
    report_section_002 = fields.Float()
    report_section_003 = fields.Float()
    report_section_004 = fields.Float()
    report_section_005 = fields.Float()
    report_section_206 = fields.Char(size=30)
    report_section_007 = fields.Float()
    report_section_472 = fields.Float()
    report_section_472_rest = fields.Float(compute="_compute_totals")
    # Field 455 (Application of goods) split
    report_section_008 = fields.Float()
    report_section_009 = fields.Float()
    report_section_455 = fields.Float()
    report_section_455_rest = fields.Float(compute="_compute_totals")
    # Field 456 (Non-business use of goods and supply of services free of charge) split
    report_section_010 = fields.Float()
    report_section_011 = fields.Float()
    report_section_456 = fields.Float()
    report_section_456_rest = fields.Float(compute="_compute_totals")
    # Field 457 (Intra-community supply) split
    report_section_013 = fields.Float()
    report_section_202 = fields.Float()
    report_section_457 = fields.Float()
    report_section_457_rest = fields.Float(compute="_compute_totals")
    # Field 458 (Input tax invoiced by other taxable persons)
    report_section_077 = fields.Float()
    report_section_081 = fields.Float()
    report_section_085 = fields.Float()
    report_section_458 = fields.Float()
    report_section_458_rest = fields.Float(compute="_compute_totals")
    # Field 459 (Due in respect of IC acquisition of goods)
    report_section_078 = fields.Float()
    report_section_082 = fields.Float()
    report_section_086 = fields.Float()
    report_section_459 = fields.Float()
    report_section_459_rest = fields.Float(compute="_compute_totals")
    # Field 460 (Due or paid in respect of importation of goods)
    report_section_079 = fields.Float()
    report_section_083 = fields.Float()
    report_section_087 = fields.Float()
    report_section_460 = fields.Float()
    report_section_460_rest = fields.Float(compute="_compute_totals")
    # Field 461 (Due under the reverse charge)
    report_section_404 = fields.Float()
    report_section_405 = fields.Float()
    report_section_406 = fields.Float()
    report_section_461 = fields.Float()
    report_section_461_rest = fields.Float(compute="_compute_totals")
    # Names and addresses to be specified
    # Accountant (A9)
    report_section_397 = fields.Char(size=30)
    report_section_398 = fields.Char(size=30)
    report_section_399 = fields.Char(size=30)
    # Lessor (A18)
    report_section_400 = fields.Char(size=30)
    report_section_401 = fields.Char(size=30)
    report_section_402 = fields.Char(size=30)

    @api.depends(
        "report_section_001", "report_section_002", "report_section_003", "report_section_004", "report_section_005",
        "report_section_007", "report_section_008", "report_section_009", "report_section_010", "report_section_011",
        "report_section_013", "report_section_202", "report_section_077", "report_section_078", "report_section_079",
        "report_section_081", "report_section_082", "report_section_083", "report_section_085", "report_section_086",
        "report_section_087", "report_section_404", "report_section_405", "report_section_406")
    def _compute_totals(self):
        self.report_section_472_rest = self.report_section_472 - self.report_section_001 - self.report_section_002 - self.report_section_003 - self.report_section_004 - self.report_section_005 - self.report_section_007
        self.report_section_455_rest = self.report_section_455 - self.report_section_008 - self.report_section_009
        self.report_section_456_rest = self.report_section_456 - self.report_section_010 - self.report_section_011
        self.report_section_457_rest = self.report_section_457 - self.report_section_013 - self.report_section_202
        self.report_section_458_rest = self.report_section_458 - self.report_section_077 - self.report_section_081 - self.report_section_085
        self.report_section_459_rest = self.report_section_459 - self.report_section_078 - self.report_section_082 - self.report_section_086
        self.report_section_460_rest = self.report_section_460 - self.report_section_079 - self.report_section_083 - self.report_section_087
        self.report_section_461_rest = self.report_section_461 - self.report_section_404 - self.report_section_405 - self.report_section_406

    def print_xml(self):
        generating_wizard = self.env.context['calling_wizard_id']
        return self.env['l10n_lu.generate.tax.report'].browse(generating_wizard).with_context(tax_report_data_id=self.id).get_xml()
