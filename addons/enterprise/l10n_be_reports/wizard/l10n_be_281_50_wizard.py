from odoo import api, fields, models, _
from odoo.exceptions import UserError

class L10nBe28150Wizard(models.Model):
    _name = 'l10n_be_reports.281_50_wizard'
    _description = 'L10n BE 281.50 Form Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    reference_year = fields.Char(string='Reference Year', required=True, readonly=False,
                                default=lambda x: str(fields.Date.today().year - 1))
    is_test = fields.Boolean(string="Is It a test ?")
    type_sending = fields.Selection([
        ('0', 'Original send'),
        ('1', 'Send grouped corrections'),
        ], string="Sending Type", default='0', required=True,
        help="This field allows to make an original sending(correspond to first send) or a grouped corrections(if you have made some mistakes before).")
    type_treatment = fields.Selection([
        ('0', 'Original'),
        ('1', 'Modification'),
        ('2', 'Add'),
        ('3', 'Cancel'),
        ], string="Treatment Type", default='0', required=True,
        help="This field represents the nature of the form.")

    @api.onchange('reference_year')
    def _onchange_reference_year(self):
        if len(self.reference_year) == 4:
            try:
                reference_year_int = int(self.reference_year)
            except:
                pass
            if reference_year_int and (reference_year_int >= fields.Date.today().year or reference_year_int <= 0):
                self.is_test = True # Set to True when the user enter a year superior or equals to the current year

    def action_generate_281_50_form(self, file_type=('pdf', 'xml')):
        self._check_reference_year()
        values = {
            'reference_year': self.reference_year,
            'is_test': self.is_test,
            'type_sending': self.type_sending,
            'type_treatment': self.type_treatment,
        }
        if self.env.context.get('active_ids') and self.env.context.get('active_model') == 'res.partner':
            partners = self.env['res.partner'].browse(self.env.context.get('active_ids'))
        else:
            partners = self.env['res.partner'].search([('parent_id', '=', None)])
        return partners._generate_281_50_form(file_type, values)

    def action_generate_281_50_form_xml(self):
        return self.action_generate_281_50_form(('xml'))

    def action_generate_281_50_form_pdf(self):
        return self.action_generate_281_50_form(('pdf'))

    @api.constrains('reference_year')
    def _check_reference_year(self):
        for record in self.filtered(lambda r: not r.is_test): # No constrains when it's a test.
            if len(record.reference_year) != 4:
                raise UserError(_('Please make sure the reference year is written with four characters (e.g. 2019)'))
            reference_year_int = 0
            try:
                reference_year_int = int(record.reference_year)
            except:
                raise UserError(_('Please make sure that the reference year only contains numbers.'))
            if not reference_year_int or reference_year_int < 0 or reference_year_int >= fields.Date.today().year:
                raise UserError(_('Wrong reference year. Please make sure the given value corresponds to an actual year and is not superior or equal to the current one.'))
