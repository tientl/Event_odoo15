# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.osv import expression

from collections import defaultdict, namedtuple

HierarchyDetail = namedtuple('HierarchyDetail', ['field', 'foldable', 'lazy', 'section_total', 'namespan'])
ColumnDetail = namedtuple('ColumnDetail', ['name', 'classes', 'getter', 'formatter'])


class AccountingReport(models.AbstractModel):
    """Helper to create accounting reports.

    Everything you need to create most of the reports is done here.
    To create a new report, you need to:
      * Create the SQL query used to create the vue with _get_sql()
      * Implement _get_column_details. It should return a list of ColumnDetail.
        Most of the time, you should only build the list using _field_column(),
        but in some cases, _custom_column() might be usefull.
      * Implement _get_hierarchy_details(). It should return a list of HierarchyDetail.
        You should build it using _hierarchy_level(). By default, a hierarchy level
        is not foldable.
      * Implement _format_{hierarchy}_line, where hierarchy is each one of the hierarchy
        names given in _get_hierarchy_details.
        If you have totals, you should also Implement _format_total_line. You can also
        implement _format_all_line if some part of the formatting is common to all levels
     You can also:
      * Implement _show_line() if you want to hide some lines based on its values.
    """

    _inherit = 'account.report'
    _name = 'account.accounting.report'
    _description = 'Accounting Report Helper'

    _depends = {
        'account.move.line': [
            'id',
            'move_id',
            'name',
            'account_id',
            'journal_id',
            'company_id',
            'currency_id',
            'analytic_account_id',
            'display_type',
            'date',
            'debit',
            'credit',
            'balance',
        ],
    }

    total_line = True  # add a grand total line at the end of the report

    # Common account.move.line fields
    move_id = fields.Many2one('account.move')
    name = fields.Char()
    account_id = fields.Many2one('account.account')
    journal_id = fields.Many2one('account.journal')
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency')
    analytic_account_id = fields.Many2one('account.analytic.account')
    display_type = fields.Char()
    analytic_tag_ids = fields.Many2many(
        comodel_name='account.analytic.tag',
        relation='account_analytic_tag_account_move_line_rel',
        column1='account_move_line_id',
        column2='account_analytic_tag_id'
    )
    date = fields.Date(group_operator="min")
    debit = fields.Monetary()
    credit = fields.Monetary()
    balance = fields.Monetary()

    # VUE MANAGEMENT ###########################################################
    # ##########################################################################

    @property
    def _table_query(self):
        query = self._get_sql()
        return ''.join(query) if isinstance(query, tuple) else query

    # To override
    def _get_sql(self):
        """Get the SQL query to be executed to retrive the report's values.

        The query can be split in mutiple parts to make the override of queries easier.
        :return (tuple(*psycopg2.sql.Composable)): a list of Composable to be concatenated to a
            SQL query.
        """
        return """
            SELECT {}
              FROM account_move_line
             WHERE FALSE
        """.format(self._get_move_line_fields())

    def _get_move_line_fields(self, aml_alias="account_move_line"):
        return ', '.join('%s.%s' % (aml_alias, field) for field in self._depends['account.move.line'])

    # COLUMN/CELL FORMATTING ###################################################
    # ##########################################################################
    def _field_column(self, field_name, sortable=False, name=None, ellipsis=False, blank_if_zero=False):
        """Build a column based on a field.

        The type of the field determines how it is displayed.
        The column's title is the name of the field.
        :param field_name: The name of the fields.Field to use
        :param sortable: Allow the user to sort data based on this column
        :param name: Use a specific name for display.
        :param ellispsis (bool): The text displayed can be truncated in the web browser.
        :param blank_if_zero (bool): For numeric fields, do not display a value if it is equal to zero.
        :return (ColumnDetail): A usable column declaration to build the html
        """
        classes = ['text-nowrap']
        def getter(v):
            return self._fields[field_name].convert_to_cache(v.get(field_name, ''), self)
        if self._fields[field_name].type in ['float']:
            classes += ['number']
            def formatter(v):
                return v if v or not blank_if_zero else ''
        elif self._fields[field_name].type in ['monetary']:
            classes += ['number']
            def m_getter(v):
                return (v.get(field_name, ''), self.env['res.currency'].browse(
                    v.get(self._fields[field_name].currency_field, (False,))[0])
                )
            getter = m_getter
            def formatter(v):
                return self.format_value(v[0], v[1], blank_if_zero=blank_if_zero)
        elif self._fields[field_name].type in ['char']:
            classes += ['text-center']
            def formatter(v): return v
        elif self._fields[field_name].type in ['date']:
            classes += ['date']
            def formatter(v): return format_date(self.env, v)
        elif self._fields[field_name].type in ['many2one']:
            classes += ['text-center']
            def r_getter(v):
                return v.get(field_name, False)
            getter = r_getter
            def formatter(v):
                return v[1] if v else ''

        IrModelFields = self.env['ir.model.fields']
        return self._custom_column(name=name or IrModelFields._get(self._name, field_name).field_description,
                                   getter=getter,
                                   formatter=formatter,
                                   classes=classes,
                                   ellipsis=ellipsis,
                                   sortable=sortable)

    def _custom_column(self, name, getter, formatter=None, classes=None, sortable=False, ellipsis=False):
        """Build custom column.

        :param name (str): The displayed title of the column.
        :param getter (function<dict,object>): A function that gets the unformatted value to
            display in this column out of the dictionary containing all the info about a row.
            If the value is a tuple, the first element is taken as `no_format` value.
        :param formatter (function<object,str>): A function that transforms the value from the
            getter function and returns the displayed string, according to locale etc.
        :param classes (list<str>): All the html classes used for that column.
        :param sortable (bool): Allow the user to sort data based on this column.
        :param ellispsis (bool): The text displayed can be truncated in the web browser.
        :return (ColumnDetail): A usable column declaration to build the html
        """
        if not formatter:
            formatter = lambda v: v
        classes = classes or []
        if sortable:
            classes += ['sortable']
        if ellipsis:
            classes += ['o_account_report_line_ellipsis']
        return ColumnDetail(name=name,
                            classes=' '.join(classes),
                            getter=getter,
                            formatter=formatter)

    def _header_column(self):
        """Build dummy column for the name."""
        return ColumnDetail(name='', classes='', getter=None, formatter=None)

    # To override
    def _get_column_details(self, options):
        """Get the details of columns.

        The details are composed of the name, classes, as well as the value getter
        and formatter for it.
        Some helpers can be used: _custom_column, _field_column and _header_column
        :param options (dict): report options
        :return (list<ColumnDetail>)
        """
        return []

    def _get_columns_name(self, options):
        return [{'name': col.name, 'class': col.classes} for col in self._get_column_details(options)]

    # HIERARCHY FORMATTING #####################################################
    # ##########################################################################
    # To override
    def _get_hierarchy_details(self, options):
        """Get the successive group by terms.

        Get a list of HierarchyDetail containing the name of the column in the SQL
        query, its foldability, if we should load lazily ("load more" functionality),
        and if we have a section total.
        and unfoldability is True iff the level should have the ability to be folded
        :param options (dict): report options.
        :return (list<HierarchyDetail>):
        """
        return []

    def _hierarchy_level(self, field_name, foldable=False, lazy=False, section_total=False, namespan=1):
        return HierarchyDetail(field=field_name,
                               foldable=foldable,
                               lazy=lazy,
                               section_total=section_total,
                               namespan=namespan)

    # REPORT LINE LIST BUILDING ################################################
    # ##########################################################################
    def _get_values(self, options, line_id):
        """Fetch the result from the database.

        :param options (dict): report options.
        :param line_id (str): optional id of the unfolded line.
        :return (list<dict>): the fetched results
        """
        def hierarchydict():
            return defaultdict(lambda: {'values': {}, 'children': hierarchydict()})
        root = hierarchydict()['root']
        groupby = self._get_hierarchy_details(options)
        unprocessed = 0
        for i in range(len(groupby)):
            current_groupby = [gb.field for gb in groupby[:i+1]]
            domain = self._get_options_domain(options)
            if i > 0 and groupby[i-1].foldable:
                # Only fetch unfolded lines (+ the newly unfoled line_id)
                if options.get('unfold_all'):
                    pass
                elif options.get('unfolded_lines') or line_id:
                    unfolded_domain = []
                    for unfolded_line in options['unfolded_lines'] + [line_id]:
                        parsed = self._parse_line_id(unfolded_line)
                        if len(current_groupby) == len(parsed) + 1:
                            unfolded_domain = expression.OR([
                                unfolded_domain,
                                [(field_name, '=', value) for field_name, model_name, value in parsed]
                            ])
                    domain = expression.AND([domain, unfolded_domain])
                else:
                    break
            if not groupby[i].foldable and i != len(groupby)-1:
                # Do not query higher level group by as we will have to fetch later anyway
                continue
            offset = int(options.get('lines_offset', 0))
            limit = self.MAX_LINES if current_groupby and groupby[i-1].lazy else None
            if 'id' in current_groupby:
                read = self.search_read(domain, self._fields.keys(), offset=offset, limit=limit)
            else:
                read = self.read_group(
                    domain=domain,
                    fields=self._fields.keys(),
                    groupby=current_groupby,
                    offset=offset,
                    limit=limit,
                    orderby=self._order,
                    lazy=False,
                )
            j = -1
            for r in read:
                hierarchy = root
                if not unprocessed:
                    self._aggregate_values(root['values'], r)
                for j, gb in enumerate(current_groupby):
                    gb_model = self._fields[gb].comodel_name if gb != 'id' else self._get_id_field_comodel()
                    key = (gb, gb_model, isinstance(r[gb], tuple) and r[gb][0] or r[gb])
                    hierarchy = hierarchy['children'][key]
                    if j >= unprocessed:
                        self._aggregate_values(hierarchy['values'], r)
            unprocessed = j+1
        return root

    def _aggregate_values(self, destination, source):
        for field, value in source.items():
            if field == '__domain':
                continue
            if not destination.get(field):
                destination[field] = value
            elif field == '__count' or self._fields[field].group_operator == 'sum':
                destination[field] = destination[field] + value
            elif self._fields[field].group_operator == 'min':
                destination[field] = min(destination[field] or value, value or destination[field])
            elif self._fields[field].group_operator == 'max':
                destination[field] = max(destination[field] or value, value or destination[field])
            elif self._fields[field].group_operator == 'bool_and':
                destination[field] = destination[field] and value
            elif self._fields[field].group_operator is None:
                pass
            else:
                raise NotImplementedError('%s operator not implemented for %s' % (self._fields[field].group_operator, field))

    def _append_grouped(self, lines, current, line_dict, value_getters, value_formatters, options, hidden_lines):
        """Append the current line and all of its children recursively.

        :param lines (list<dict>): the list of report lines to send to the client
        :param current (list<tuple>): list of tuple(grouping_key, id)
        :param line_dict: the current hierarchy to unpack
        :param value_getters (list<function>): list of getter to retrieve each column's data.
            The parameter passed to the getter is the result of the read_group
        :param value_formatters (list<functions>): list of the value formatters.
            The parameter passed to the setter is the result of the getter.
        :param options (dict): report options.
        :param hidden_lines (dict): mapping between the lines hidden and their parent.
        """
        if line_dict['values'].get('__count', 1) == 0:
            return

        line = self._format_line(line_dict['values'], value_getters, value_formatters, current, options)
        if line['parent_id'] in hidden_lines:
            line['parent_id'] = hidden_lines[line['parent_id']]

        if self._show_line(line, line_dict['values'], current, options):
            lines.append(line)
        else:
            hidden_lines[line['id']] = hidden_lines.get('parent_id') or line['parent_id']

        # Add children recursively
        for key in line_dict['children']:
            self._append_grouped(
                lines=lines,
                current=current + [key],
                line_dict=line_dict['children'][key],
                value_getters=value_getters,
                value_formatters=value_formatters,
                options=options,
                hidden_lines=hidden_lines,
            )

        # Handle load more
        offset = line['offset'] = len(line_dict['children']) + int(options.get('lines_offset', 0))
        if (
            current and self._get_hierarchy_details(options)[len(current)-1].lazy
            and len(line_dict['children']) >= self.MAX_LINES and line_dict['children']
        ):
            load_more_line = self._get_load_more_line(
                line_dict=line_dict,
                value_getters=value_getters,
                value_formatters=value_formatters,
                current=current,
                options=options,
                offset=offset,
            )
            lines.append(load_more_line)

        # Handle section total line
        if (
            current and self._get_hierarchy_details(options)[len(current)-1].section_total
            and line_dict['children']
            and lines[-1] != line
        ):
            total_line = self._format_line(
                value_dict=line_dict['values'],
                value_getters=value_getters,
                value_formatters=value_formatters,
                current=current,
                options=options,
                total=True,
            )
            if self._show_line(total_line, line_dict['values'], current, options):
                lines.append(total_line)

    def _get_load_more_line(self, line_dict, value_getters, value_formatters, current, options, offset):
        load_more_line = self._format_line(line_dict['values'], value_getters, value_formatters, current, options)
        load_more_line['unfoldable'] = False
        load_more_line['offset'] = offset
        load_more_line['remaining'] = line_dict['values'].get('__count', 1) - offset
        load_more_line['columns'] = [{} for i in range(len(load_more_line['columns']))]
        load_more_line['name'] = _('Load more... (%s remaining)') % (line_dict['values'].get('__count', 1) - offset)
        return load_more_line

    @api.model
    def _get_lines(self, options, line_id=None):
        self = self.with_context(report_options=options)

        line_dict = self._get_values(options=options, line_id=line_id)
        if line_id:  # prune the empty tree and keep only the wanted branch
            for field, model, value in self._parse_line_id(line_id):
                line_dict = line_dict['children'][(field, model, value)]
        if not line_dict['values']:
            return []

        lines = []
        self._append_grouped(
            lines=lines,
            current=self._parse_line_id(line_id),
            line_dict=line_dict,
            value_getters=[d.getter for d in self._get_column_details(options)[1:]],
            value_formatters=[d.formatter for d in self._get_column_details(options)[1:]],
            options=options,
            hidden_lines={},
        )

        if line_id:
            if options.get('lines_offset', 0):
                return lines[1:-1]  # TODO remove total line depending on param
            return lines  # No need to handle the total as we already only have pruned the tree
        if lines:
            # put the total line at the end or remove it
            return lines[1:] + (self.total_line and [{**lines[0], 'name': _('Total')}] or [])
        return []

    # Can be overridden
    def _get_id_field_comodel(self):
        """ The id field of the report typically is set to refer to some other
        model determining its content. In some cases, we want to access this model, but
        we than can't infer it from just the field. This function is used to get it.
        In typical cases, 'id' will refer to account.move.line, so that's the
        default value we return here, but it can be overridden if needed.
        """
        return 'account.move.line'

    # Can be overridden
    def _show_line(self, report_dict, value_dict, current, options):
        """Determine if a line should be shown.

        By default, show only children of unfolded lines and children of non unfoldable lines
        :param report_dict: the lines to be displayed or not
        :param value_dict: the raw values of the current line
        :param current (list<tuple>): list of tuple(grouping_key, id)
        :param options (dict): report options.
        :return (bool): True if the line should be shown
        """
        return (report_dict['parent_id'] is None
                or report_dict['parent_id'] == 'total-None'
                or (report_dict['parent_id'] in options.get('unfolded_lines', [])
                or options.get('unfold_all'))
                or not self._get_hierarchy_details(options)[len(current) - 2].foldable)

    # To override
    def _format_line(self, value_dict, value_getters, value_formatters, current, options, total=False):
        """Build the report line based on the position in the report.

        Basic informations such as id, parent_id, unfoldable, unfolded, level are set here
        but this should be overriden to customize columns, the name and other specific fields
        in each report.
        :param value_dict (dict): the result of the read_group
        :param value_getters (list<function>): list of getter to retrieve each column's data.
            The parameter passed to the getter is the result of the read_group
        :param value_formatters (list<functions>): list of the value formatters.
            The parameter passed to the setter is the result of the getter.
        :param current (list<tuple>): list of tuple(grouping_key, id)
        :param options (dict): report options
        :param total (bool): set to True for section totals
        :return dict: the report line
        """
        id = self._build_line_id(current)
        hierarchy_detail = self._get_hierarchy_details(options)[len(current) - 1]
        res = {
            'id': id,
            'parent_id': self._build_parent_line_id(current) or None,
            'unfolded': ((id in options.get('unfolded_lines', []))
                         or options.get('unfold_all')
                         or self._context.get('print_mode')),
            'unfoldable': hierarchy_detail.foldable,
            'level': len(current),
            'colspan': hierarchy_detail.namespan,
            'columns': [
                {'name': formatter(v), 'no_format': v[0] if isinstance(v, tuple) else v}
                for v, formatter in zip(
                    [getter(value_dict) for getter in value_getters],
                    value_formatters,
                )
            ],
            'class': 'total' if len(current) == 0 else '',
        }
        if getattr(self, '_format_all_line', None):
            self._format_all_line(res, value_dict, options)
        format_func = None
        if current:
            # For example, it the line id ends with ('account_id', 'account_account', 42),
            # we want to add an 'account_id' key to the result, with value 42.
            res[current[-1][0]] = current[-1][2]
            format_func = getattr(self, '_format_%s_line' % current[-1][0])
        else:
            format_func = getattr(self, '_format_total_line', None)
        if format_func:
            format_func(res, value_dict, options)
        if total:
            res['name'] = _('Total %s') % res['name']
        res['columns'] = res['columns'][hierarchy_detail.namespan-1:]

        return res
