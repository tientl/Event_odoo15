# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    intrastat_id = fields.Many2one('account.intrastat.code', string='Commodity Code', domain=[('type', '=', 'commodity')])

    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_id or (self.parent_id and self.parent_id.search_intrastat_code()) or self.intrastat_id


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    intrastat_id = fields.Many2one('account.intrastat.code', string='Commodity Code', domain="[('type', '=', 'commodity')]")
    intrastat_origin_country_id = fields.Many2one('res.country', string='Country of Origin')

    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_id or self.categ_id.search_intrastat_code()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Product variant may need different intrastat code.
    intrastat_variant_id = fields.Many2one(comodel_name='account.intrastat.code', string='Variant commodity Code',
                                           domain="[('type', '=', 'commodity')]")

    intrastat_id = fields.Many2one(comodel_name='account.intrastat.code', string='Commodity Code',
                                   domain="[('type', '=', 'commodity')]", compute='_compute_intrastat_id',
                                   inverse='_set_intrastat_id')

    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_variant_id or self.product_tmpl_id.search_intrastat_code()

    def _compute_intrastat_id(self):
        """Get the intrastat id from the template if no intrastat id is set on the variant."""
        for product in self:
            product.intrastat_id = product.intrastat_variant_id or product.product_tmpl_id.intrastat_id

    def _set_intrastat_id(self):
        return self._set_template_field('intrastat_id', 'intrastat_variant_id')
