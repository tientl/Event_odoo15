# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import unicodedata
import uuid
import re
import xml.etree.ElementTree as ET
from odoo.osv import expression
from odoo import api, fields, models, _, Command
from odoo.tools import ustr
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

OPTIONS_WL = ['use_active', 'use_responsible', 'use_partner', 'use_company',
              'use_notes', 'use_value', 'use_image', 'use_tags', 'use_sequence',
              'use_mail', 'use_stages', 'use_date', 'use_double_dates', 'lines']


def sanitize_for_xmlid(s):
    """ Transforms a string to a name suitable for use in an xmlid.
        Strips leading and trailing spaces, converts unicode chars to ascii,
        lowers all chars, replaces spaces with underscores and truncates the
        resulting string to 20 characters.
        :param s: str
        :rtype: str
    """
    s = ustr(s)
    uni = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

    slug_str = re.sub('[\W]', ' ', uni).strip().lower()
    slug_str = re.sub('[-\s]+', '_', slug_str)
    return slug_str[:20]


class Base(models.AbstractModel):
    _inherit = 'base'

    def create_studio_model_data(self, name):
        """ We want to keep track of created records with studio
            (ex: model, field, view, action, menu, etc.).
            An ir.model.data is created whenever a record of one of these models
            is created, tagged with studio.
        """
        IrModelData = self.env['ir.model.data']

        # Check if there is already an ir.model.data for the given resource
        data = IrModelData.search([
            ('model', '=', self._name), ('res_id', '=', self.id)
        ])
        if data:
            data.write({})  # force a write to set the 'studio' and 'noupdate' flags to True
        else:
            module = self.env['ir.module.module'].get_studio_module()
            IrModelData.create({
                'name': '%s_%s' % (sanitize_for_xmlid(name), uuid.uuid4()),
                'model': self._name,
                'res_id': self.id,
                'module': module.name,
            })


class IrModel(models.Model):
    _name = 'ir.model'
    _inherit = ['studio.mixin', 'ir.model']

    abstract = fields.Boolean(compute='_compute_abstract',
                              store=False,
                              help="Wheter this model is abstract",
                              search='_search_abstract')

    def _compute_abstract(self):
        for record in self:
            record.abstract = self.env[record.model]._abstract

    def _search_abstract(self, operator, value):
        abstract_models = [
            model._name
            for model in self.env.values()
            if model._abstract
        ]
        dom_operator = 'in' if (operator, value) in [('=', True), ('!=', False)] else 'not in'

        return [('model', dom_operator, abstract_models)]

    @api.model
    def studio_model_create(self, name, vals=None, options=None):
        """ Allow quick creation of models through Studio.
        
        :param name: functional name of the model (_description attribute)
        :param vals: dict of values that will be included in the create call
        :param options: list of options that can trigger automated behaviours,
                        in the form of 'use_<behaviour>' (e.g. 'use_tags')
        :return: the main model created as well as extra models needed for the
                 requested behaviours (e.g. tag or stage models) in the form of
                 a tuple (main_model, extra_models)
        :rtype: tuple
        """
        model_name = vals and vals.get('model') or ('x_' + sanitize_for_xmlid(name))
        # will contain extra models (tags, stages) for which a menu entry might need to be created
        extra_models = self
        options = options if options is not None else []
        valid_options = [opt for opt in options if opt in OPTIONS_WL]
        auto_vals = {
            'name': name,
            'model': model_name,
        }
        if vals is not None:
            vals.update(auto_vals)
        else:
            vals = auto_vals
        main_model = self.create(vals)
        # setup mail first so that other behaviours know if they can
        # enable tracking on important fields
        if 'use_mail' in options:
            main_model.write({
                'is_mail_thread': True,
                'is_mail_activity': True,
            })
            main_model.field_id.filtered(lambda f: f.name == 'x_name').tracking = True
        # now let's check other options and accumulate potential extra models (tags, stages)
        # created during this process, they will need to get their own action and menu
        # (which will be done at the controller level)
        if 'use_active' in valid_options:
            extra_models |= main_model._setup_active()
        if 'use_responsible' in valid_options:
            extra_models |= main_model._setup_responsible()
        if 'use_partner' in valid_options:
            extra_models |= main_model._setup_partner()
        if 'use_company' in valid_options:
            extra_models |= main_model._setup_company()
        if 'use_notes' in valid_options:
            extra_models |= main_model._setup_notes()
        if 'use_value' in valid_options:
            extra_models |= main_model._setup_value()
        if 'use_image' in valid_options:
            extra_models |= main_model._setup_image()
        if 'use_tags' in valid_options:
            extra_models |= main_model._setup_tags()
        if 'use_sequence' in valid_options or 'use_stages' in valid_options:
            extra_models |= main_model._setup_sequence()
        if 'use_stages' in valid_options:
            extra_models |= main_model._setup_stages()
        if 'use_date' in valid_options:
            extra_models |= main_model._setup_date()
        if 'use_double_dates' in valid_options:
            extra_models |= main_model._setup_double_dates()
        if 'lines' in valid_options:
            main_model._setup_one2many_lines()
        # set the ordering of the model, depending on the use of sequences and stages
        # stages create a kanban view and a priority field, in which case the list view
        # will not have the handle widget to avoid inconsistencies
        # note that using stages will automatically add sequences as well, since the
        # kanban view needs both for ordering anyway
        if 'use_stages' in valid_options:
            # need to order by priority then sequence
            main_model.order = 'x_studio_priority desc, x_studio_sequence asc, id asc'
        elif 'use_sequence' in valid_options:
            main_model.order = 'x_studio_sequence asc, id asc'
        # Create automatic views that will include fields and views relevant to the model's options
        self.env['ir.ui.view'].create_automatic_views(main_model.model)
        main_model._setup_access_rights()
        return (main_model, extra_models)

    @api.model
    def name_create(self, name):
        if self._context.get('studio'):
            (main_model, _) = self.studio_model_create(name)
            return main_model.name_get()[0]
        return super().name_create(name)

    def _setup_one2many_lines(self):
        """ Creates a new model (with sequence and description fields) and a
            one2many field pointing to that model.
        """
        # create the Line model
        model_name = self.model.replace('.', '_')
        if model_name[:2] != 'x_':
            model_name = 'x_' + model_name

        relation_field_name = model_name + '_id'
        line_model_values = {
            'name': model_name[2:] + '_line',
            'model': model_name + '_line_' + uuid.uuid4().hex[:5],
            'field_id': [
                (Command.create({
                    'name': 'x_studio_sequence',
                    'ttype': 'integer',
                    'field_description': _('Sequence'),
                })),
                (Command.create({
                    'name': 'x_name',
                    'ttype': 'char',
                    'required': True,
                    'field_description': _('Description'),
                    'translate': True,
                })),
                (Command.create({
                    'name': relation_field_name,
                    'ttype': 'many2one',
                    'relation': self.model,
                })),
            ],
        }
        line_model = self.with_context(list_editable="bottom").studio_model_create(
            '%s  Lines' % model_name[2:].replace('_', ' ').title(),
            vals=line_model_values,
        )[0]
        line_model._setup_access_rights()
        self.env['ir.ui.view'].create_automatic_views(line_model.model)

        # create and return the one2many pointing to the Line model
        return self.env['ir.model.fields'].create({
            'name': model_name + '_line_ids_' + uuid.uuid4().hex[:5],
            'ttype': 'one2many',
            'relation': line_model.model,
            'relation_field': relation_field_name,
            'field_description': _('New Lines'),
            'model_id': self.id,
        })

    def _setup_active(self):
        for model in self:
            active_field = self.env['ir.model.fields'].create({
                'name': 'x_active',  # can't use x_studio_active as not supported by ORM
                'ttype': 'boolean',
                'field_description': _('Active'),
                'model_id': model.id,
                'tracking': model.is_mail_thread,
            })
            self.env['ir.default'].set(model.model, active_field.name, True)
        return self.env['ir.model']

    def _setup_sequence(self):
        for model in self:
            sequence_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_sequence',
                'ttype': 'integer',
                'field_description': _('Sequence'),
                'model_id': model.id,
                'copied': True,
            })
            # set a default to 10 like most other sequence fields, avoid
            # new stages to become the first one upon creation 'by accident'
            self.env['ir.default'].set(model.model, sequence_field.name, 10)
        return self.env['ir.model']

    def _setup_responsible(self):
        for model in self:
            responsible_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_user_id',
                'ttype': 'many2one',
                'relation': 'res.users',
                'domain': "[('share', '=', False)]",
                'field_description': _('Responsible'),
                'model_id': model.id,
                'tracking': model.is_mail_thread,
                'copied': True,
            })
        return self.env['ir.model']

    def _setup_partner(self):
        for model in self:
            partner_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_partner_id',
                'ttype': 'many2one',
                'relation': 'res.partner',
                'field_description': _('Contact'),
                'model_id': model.id,
                'tracking': model.is_mail_thread,
                'copied': True,
            })
            phone_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_partner_phone',
                'ttype': 'char',
                'related': 'x_studio_partner_id.phone',
                'field_description': _('Phone'),
                'model_id': model.id,
            })
            email_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_partner_email',
                'ttype': 'char',
                'related': 'x_studio_partner_id.email',
                'field_description': _('Email'),
                'model_id': model.id,
            })
        return self.env['ir.model']

    def _setup_company(self):
        for model in self:
            company_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_company_id',
                'ttype': 'many2one',
                'relation': 'res.company',
                'field_description': _('Company'),
                'model_id': model.id,
                'tracking': model.is_mail_thread,
                'copied': True,
            })
            rule = self.env['ir.rule'].create({
                'name': '%s - Multi-Company' % model.name,
                'model_id': model.id,
                'domain_force': "['|', ('x_studio_company_id', '=', False), ('x_studio_company_id', 'in', company_ids)]"
            })
            # generate default for each company (note: also done when creating a new company)
            for company in self.env['res.company'].sudo().search([]):
                self.env['ir.default'].set(model.model, company_field.name, company.id, company_id=company.id)
        return self.env['ir.model']

    def _setup_notes(self):
        for model in self:
            note_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_notes',
                'ttype': 'html',
                'field_description': _('Notes'),
                'model_id': model.id,
                'copied': True,
            })
        return self.env['ir.model']

    def _setup_date(self):
        for model in self:
            date_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_date',
                'ttype': 'date',
                'field_description': _('Date'),
                'model_id': model.id,
                'copied': True,
            })
        return self.env['ir.model']

    def _setup_double_dates(self):
        for model in self:
            stop_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_date_stop',
                'ttype': 'datetime',
                'field_description': _('End Date'),
                'model_id': model.id,
                'copied': True,
            })
            start_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_date_start',
                'ttype': 'datetime',
                'field_description': _('Start Date'),
                'model_id': model.id,
                'copied': True,
            })
        return self.env['ir.model']

    def _setup_value(self):
        for model in self:
            currency_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_currency_id',
                'ttype': 'many2one',
                'relation': 'res.currency',
                'field_description': _('Currency'),
                'model_id': model.id,
                'copied': True,
            })
            value_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_value',
                'ttype': 'float',
                'field_description': _('Value'),
                'model_id': model.id,
                'tracking': model.is_mail_thread,
                'copied': True,
            })
            # generate default for each company (note: also done when creating a new company)
            for company in self.env['res.company'].sudo().search([]):
                self.env['ir.default'].set(model.model, currency_field.name, company.currency_id.id, company_id=company.id)
        return self.env['ir.model']

    def _setup_image(self):
        for model in self:
            image_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_image',
                'ttype': 'binary',
                'field_description': _('Image'),
                'model_id': model.id,
                'copied': True,
            })
        return self.env['ir.model']

    def _setup_stages(self):
        stage_models = self.env['ir.model']
        for model in self:
            # 1. Create the stage model
            stage_model_vals = {
                'name': '%s Stages' % model.name,
                'model': '%s_stage' % model.model,
                'field_id' : list(),
            }
            stage_model_vals['field_id'].append((0, 0, {
                'name': 'x_name',
                'ttype': 'char',
                'required': True,
                'field_description': _('Stage Name'),
                'translate': True,
                'copied': True,
            }))
            stage_options = ['use_sequence']
            stage_model = self.with_context(list_editable="bottom").studio_model_create(
                '%s Stages' % model.name,
                vals=stage_model_vals,
                options=stage_options
            )[0]
            _logger.info('created stage model %s (%s) for main model %s', stage_model.model, stage_model.name, model.model)
            # 2. Link our model with the tag model
            stage_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_stage_id',
                'ttype': 'many2one',
                'relation': stage_model.model,
                'on_delete': 'restrict',
                'required': True,
                'field_description': _('Stage'),
                'model_id': model.id,
                'tracking': model.is_mail_thread,
                'copied': True,
                'group_expand': True,
            })
            # create stage 'New','In Progress','Done' and set 'New' as default
            default_stage = self.env[stage_model.model].create({'x_name': _('New')})
            self.env[stage_model.model].create([{'x_name': _('In Progress')}, {'x_name': _('Done')}])
            self.env['ir.default'].set(model.model, stage_field.name, default_stage.id)
            priority_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_priority',
                'ttype': 'boolean',
                'field_description': _('High Priority'),
                'model_id': model.id,
                'copied': True,
            })
            self.env['ir.model.fields'].create({
                'name': 'x_color',
                'ttype': 'integer',
                'field_description': _('Color'),
                'model_id': model.id,
            })
            kanban_state_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_kanban_state',
                'ttype': 'selection',
                'selection_ids': [
                    (0, 0 ,{'value': 'normal', 'name': _('In Progress'), 'sequence': 10}),
                    (0, 0 ,{'value': 'done', 'name': _('Ready'), 'sequence': 20}),
                    (0, 0 ,{'value': 'blocked', 'name': _('Blocked'), 'sequence': 30})
                ],
                'relation': stage_model.model,
                'field_description': _('Kanban State'),
                'model_id': model.id,
                'copied': True,
            })
            stage_models |= stage_model
        return stage_models

    def _setup_tags(self):
        tag_models = self.env['ir.model']
        for model in self:
            # 1. Create the tag model
            tag_model_vals = {
                'name': '%s Tags' % model.name,
                'model': '%s_tag' % model.model,
                'field_id' : list(),
            }
            tag_model_vals['field_id'].append((0, 0, {
                'name': 'x_name',
                'ttype': 'char',
                'required': True,
                'field_description': _('Name'),
                'copied': True,
            }))
            tag_model_vals['field_id'].append((0, 0, {
                'name': 'x_color',
                'ttype': 'integer',
                'field_description': _('Color'),
                'copied': True,
            }))
            tag_model = self.with_context(list_editable="bottom").studio_model_create(
                '%s Tags' % model.name,
                vals=tag_model_vals
            )[0]
            _logger.info('created tag model %s (%s) for main model %s', tag_model.model, tag_model.name, model.model)
            # 2. Link our model with the tag model
            tag_field = self.env['ir.model.fields'].create({
                'name': 'x_studio_tag_ids',
                'ttype': 'many2many',
                'relation': tag_model.model,
                'field_description': _('Tags'),
                'model_id': model.id,
                'relation_table': '%s_tag_rel' % model.model,
                'column1': '%s_id' % model.model,
                'column2': 'x_tag_id',
                'copied': True,
            })
            tag_models |= tag_model
        return tag_models

    def _setup_access_rights(self):
        for model in self:
            # Give all access to the created model to Employees by default, except deletion. All access to System
            # Note: a better solution may be to create groups at the app creation but the model is created
            # before the app and for other models we need to have info about the app.
            self.env['ir.model.access'].create({
                'name': model.name + ' group_system',
                'model_id': model.id,
                'group_id': self.env.ref('base.group_system').id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': True,
            })
            self.env['ir.model.access'].create({
                'name': model.name + ' group_user',
                'model_id': model.id,
                'group_id': self.env.ref('base.group_user').id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': False,
            })
        return True

    def _get_default_view(self, view_type, view_id=False, create=True):
        """Get the default view for a given model.
        
        By default, create a view if one does not exist.
        """
        self.ensure_one()
        View = self.env['ir.ui.view']
        # If we have no view_id to inherit from, it's because we are adding
        # fields to the default view of a new model. We will materialize the
        # default view as a true view so we can keep using our xpath mechanism.
        if view_id:
            view = View.browse(view_id)
        elif create:
            arch = self.env[self.model].fields_view_get(view_id, view_type)['arch']
            # set sample data when activating a pivot/graph view through studio
            if view_type in ['graph', 'pivot']:
                sample_view_arch = ET.fromstring(arch)
                sample_view_arch.set('sample', '1')
                arch = ET.tostring(sample_view_arch, encoding='unicode')
            view = View.create({
                'type': view_type,
                'model': self.model,
                'arch': arch,
                'name': "Default %s view for %s" % (view_type, self),
            })
        else:
            view = View.browse(View.default_view(self.model, view_type))
        return view

    def _create_default_action(self, name):
        """Create an ir.act_window record set up with the available view types set up."""
        self.ensure_one()
        model_views = self.env['ir.ui.view'].search_read([('model', '=', self.model), ('type', '!=', 'search')],
                                                         fields=['type'])
        available_view_types = set(map(lambda v: v['type'], model_views))
        # in actions, kanban should be first, then list, etc.
        # this is arbitrary, but we need consistency!
        VIEWS_ORDER = {'kanban': 0, 'tree': 1, 'form': 2, 'calendar': 3, 'gantt': 4, 'map': 5,
                       'pivot': 6, 'graph': 7, 'qweb': 8, 'activity': 9}
        sorted_view_types = list(sorted(available_view_types, key=lambda vt: VIEWS_ORDER.get(vt, 10)))
        view_mode = ','.join(sorted_view_types) if sorted_view_types else 'tree,form'
        action = self.env['ir.actions.act_window'].create({
            'name': name,
            'res_model': self.model,
            'view_mode': view_mode,
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    This is your new action.
                </p>
                <p>By default, it contains a list and a form view and possibly
                    other view types depending on the options you chose for your model.
                </p>
                <p>
                    You can start customizing these screens by clicking on the Studio icon on the
                    top right corner (you can also customize this help message there).
                </p>
            """),
        })
        return action

class IrModelField(models.Model):
    _name = 'ir.model.fields'
    _inherit = ['studio.mixin', 'ir.model.fields']

    def name_get(self):
        if self.env.context.get('studio'):
            return [(field.id, "%s (%s)" % (field.field_description, field.model_id.name)) for field in self]
        return super(IrModelField, self).name_get()

    @api.constrains('name')
    def _check_name(self):
        super()._check_name()
        for field in self:
            if '__' in field.name:
                raise ValidationError(_("Custom field names cannot contain double underscores."))

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        # To search records based on Field name, Field technical name, Model name and Model technical name
        elif name and self._context.get('studio') :
            domain = ['|', '|', '|', ('name', operator, name), ('field_description', operator, name), ('model', operator, name), ('model_id.name', operator, name)]
        else:
            domain = [('field_description', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.model
    def _get_next_relation(self, model_name, comodel_name):
        """Prevent using the same m2m relation table when adding the same field.

        If the same m2m field was already added on the model, the user is in fact
        trying to add another relation - not the same one. We need to create another
        relation table.
        """
        result = super()._custom_many2many_names(model_name, comodel_name)[0]
        # check if there's already a m2m field from model_name to comodel_name;
        # if yes, check the relation table and add a sequence to it - we want to
        # be able to mirror these fields on the other side in the same order
        base = result
        attempt = 0
        existing_m2m = self.search([
            ('model', '=', model_name),
            ('relation', '=', comodel_name),
            ('relation_table', '=', result)
        ])
        while existing_m2m:
            attempt += 1
            result = '%s_%s' % (base, attempt)
            existing_m2m = self.search([
                ('model', '=', model_name),
                ('relation', '=', comodel_name),
                ('relation_table', '=', result)
            ])
        return result


class IrModelAccess(models.Model):
    _name = 'ir.model.access'
    _inherit = ['studio.mixin', 'ir.model.access']
