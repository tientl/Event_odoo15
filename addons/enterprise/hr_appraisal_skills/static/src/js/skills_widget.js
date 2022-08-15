odoo.define('hr_appraisal_skills.Widget', function (require) {

var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var ListRenderer = require('web.ListRenderer');
var field_registry = require('web.field_registry');

var core = require('web.core');
var QWeb = core.qweb;

var ListRendererGrouped = ListRenderer.extend({
    groupBy: 'skill_type_id',

    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.sampleData = parent.recordData.state == 'new';
    },

    _renderHeader: function () {
        var $tr = $('<tr>')
            .append(_.map(this.columns, this._renderHeaderCell.bind(this)));

        if (this.state.data.length == 0 && !this.sampleData) {
            return $('<thead/>');
        } else {
            return $('<thead>').append($tr);
        }
    },

    _renderBody: function () {
        var self = this;
        var $body = $('<tbody>');

        if (this.state.data.length === 0 && this.sampleData) {
            let sampleData = [{
                'skill': '80px',
                'level': '25px',
                'progress': '120px',
                'justification': '190px'
            }, {
                'skill': '70px',
                'level': '40px',
                'progress': '100px',
                'justification': '130px'
            }, {
                'skill': '40px',
                'level': '80px',
                'progress': '30px',
                'justification': '210px'
            }, {
                'skill': '90px',
                'level': '47px',
                'progress': '70px',
                'justification': '100px'
            }];
            sampleData.forEach((data) => $body.append(QWeb.render('hr_appraisal_skills_sample_row', data)));
            $body.addClass('o_appraisal_blur');
        } else {
            var grouped_by = _.groupBy(this.state.data, function (record) {
                return record.data[self.groupBy].res_id;
            });

            for (var key in grouped_by) {
                var group = grouped_by[key];
                var title, groupId;
                if (key !== 'undefined') {
                    title = group[0].data[this.groupBy].data.display_name;
                    groupId = group[0].data[this.groupBy].data.id;
                    $body.append(this._renderTitleCell(title, groupId));
                }

                group.forEach(function(record) {
                    $body.append(self._renderRow(record));
                });
            }

            if (self.addCreateLine) {
                $body.append(QWeb.render('hr_appraisal_skills_add_row', {
                    'empty': $body.is(':empty'),
                }));
            }
        }

        return $body;
    },

    _renderTitleCell: function(name, groupId) {
        return QWeb.render('hr_appraisal_skills_row_title', {
            name: name,
            context: !!groupId?JSON.stringify({ 'default_skill_type_id': groupId}):'{}',
        });
    },

    confirmUpdate: function (state, id, fields, ev) {
        this._setState(state);
        return this.confirmChange(state, id, fields, ev);
    },

    renderButtons: function(visible) {
        this.$el.find('.o_field_x2many_list_row_add a').toggleClass('d-none', visible);
    },

    _shouldRenderOptionalColumnsDropdown: function() {
        return this._super.apply(this, arguments) && this.state.count > 0;;
    },

    async _renderView() {
        const self = this;
        await this._super(...arguments);

        if (this.state.data.length === 0 && this.sampleData) {
            const table = this.$el.find('.table-responsive');
            table.addClass('o_appraisal_blur');
        }
    },
});

var FieldsSkillsJustification = FieldOne2Many.extend({
    _getRenderer: function () {
        return ListRendererGrouped;
    },

    _renderButtons: function () {
        if (this.renderer) {
            this.renderer.renderButtons(this.creatingRecord);
        }

        return this._super.apply(this, arguments);
    },
});

field_registry.add('hr_skills_justification', FieldsSkillsJustification);

});
