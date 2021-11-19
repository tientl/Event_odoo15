# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from lxml import etree

GANTT_VALID_ATTRIBUTES = set([
    '__validate__',                     # ir.ui.view implementation detail
    'date_start',
    'date_stop',
    'default_scale',
    'class',
    'js_class',
    'form_view_id',
    'progress',
    'consolidation',
    'consolidation_max',
    'consolidation_exclude',
    'string',
    'create',
    'on_create',
    'cell_create',
    'edit',
    'delete',
    'plan',
    'default_group_by',
    'dynamic_range',
    'display_unavailability',
    'disable_drag_drop',
    'total_row',
    'collapse_first_level',
    'offset',
    'scales',
    'thumbnails',
    'precision',
    'color',
    'decoration-secondary',
    'decoration-success',
    'decoration-info',
    'decoration-warning',
    'decoration-danger',
    'sample'
])

class View(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_access_rights(self, node, model):
        """ Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views. """
        super(View, self)._postprocess_access_rights(node, model)

        # testing ACL as real user
        is_base_model = self.env.context.get('base_model_name', model._name) == model._name

        if node.tag in ('gantt'):
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if (not node.get(action) and
                        not model.check_access_rights(operation, raise_exception=False) or
                        not self._context.get(action, True) and is_base_model):
                    node.set(action, 'false')

    def _validate_tag_gantt(self, node, name_manager, node_info):
        if not node_info['validate']:
            return

        templates_count = 0
        for child in node.iterchildren(tag=etree.Element):
            if child.tag == 'templates':
                if not templates_count:
                    templates_count += 1
                else:
                    msg = _('Gantt view can contain only one templates tag')
                    self._raise_view_error(msg, child)
            elif child.tag != 'field':
                msg = _('Gantt child can only be field or template, got %s', child.tag)
                self._raise_view_error(msg, child)

        default_scale = node.get('default_scale')
        if default_scale:
            if default_scale not in ('day', 'week', 'month', 'year'):
                self._raise_view_error(_("Invalid default_scale '%s' in gantt", default_scale), node)
        attrs = set(node.attrib)
        if 'date_start' not in attrs:
            msg = _("Gantt must have a 'date_start' attribute")
            self._raise_view_error(msg, node)

        if 'date_stop' not in attrs:
            msg = _("Gantt must have a 'date_stop' attribute")
            self._raise_view_error(msg, node)

        remaining = attrs - GANTT_VALID_ATTRIBUTES
        if remaining:
            msg = _(
                "Invalid attributes (%s) in gantt view. Attributes must be in (%s)",
                ','.join(remaining), ','.join(GANTT_VALID_ATTRIBUTES),
            )
            self._raise_view_error(msg, node)
