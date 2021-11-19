odoo.define('web_gantt.GanttRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');
var GanttRow = require('web_gantt.GanttRow');
var qweb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;


var GanttRenderer = AbstractRenderer.extend({
    config: {
        GanttRow: GanttRow
    },

    custom_events: _.extend({}, AbstractRenderer.prototype.custom_events, {
        'start_dragging': '_onStartDragging',
        'start_no_dragging': '_onStartNoDragging',
        'stop_dragging': '_onStopDragging',
        'stop_no_dragging': '_onStopNoDragging',
    }),

    DECORATIONS: [
        'decoration-secondary',
        'decoration-success',
        'decoration-info',
        'decoration-warning',
        'decoration-danger',
    ],
    sampleDataTargets: [
        '.o_gantt_row',
    ],
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     * @param {boolean} params.canCreate
     * @param {boolean} params.canEdit
     * @param {boolean} params.canCellCreate
     * @param {Object} params.cellPrecisions
     * @param {string} params.colorField
     * @param {Object} params.fieldsInfo
     * @param {Object} params.SCALES
     * @param {string} params.string
     * @param {string} params.totalRow
     * @param {string} [params.popoverTemplate]
     */
    init: function (parent, state, params) {
        var self = this;
        this._super.apply(this, arguments);

        this.$draggedPill = null;
        this.$draggedPillClone = null;

        this.canCreate = params.canCreate;
        this.canCellCreate = params.canCellCreate;
        this.canEdit = params.canEdit;
        this.canPlan = params.canPlan;
        this.cellPrecisions = params.cellPrecisions;
        this.colorField = params.colorField;
        this.disableDragdrop = params.disableDragdrop;
        this.progressField = params.progressField;
        this.consolidationParams = params.consolidationParams;
        this.fieldsInfo = params.fieldsInfo;
        this.SCALES = params.SCALES;
        this.string = params.string;
        this.totalRow = params.totalRow;
        this.collapseFirstLevel = params.collapseFirstLevel;
        this.thumbnails = params.thumbnails;
        this.rowWidgets = {};
        // Pill decoration colors, By default display primary color for pill
        this.pillDecorations = _.chain(this.arch.attrs)
            .pick(function (value, key) {
                return self.DECORATIONS.indexOf(key) >= 0;
            }).mapObject(function (value) {
                return py.parse(py.tokenize(value));
            }).value();
        if (params.popoverTemplate) {
            this.popoverQWeb = new qweb(config.isDebug(), {_s: session.origin});
            this.popoverQWeb.add_template(utils.json_node_to_xml(params.popoverTemplate));
        } else {
            this.popoverQWeb = QWeb;
        }

        this.isRTL = _t.database.parameters.direction === "rtl";
        this.template_to_use = "GanttView";
    },
    /**
     * Called each time the renderer is attached into the DOM.
     */
    on_attach_callback: function () {
        this._isInDom = true;
        core.bus.on("keydown", this, this._onKeydown);
        core.bus.on("keyup", this, this._onKeyup);
        if (!this.disableDragdrop) {
            this._setRowsDroppable();
        }
    },
    /**
     * Called each time the renderer is detached from the DOM.
     */
    on_detach_callback: function () {
        this._isInDom = false;
        core.bus.off("keydown", this, this._onKeydown);
        core.bus.off("keyup", this, this._onKeyup);
        _.invoke(this.rowWidgets, 'on_detach_callback');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Re-render a given row and its sub-rows. This typically occurs when a row
     * is collapsed/expanded, to prevent from re-rendering the whole view.
     *
     * @param {Object} rowState part of the state concerning the row to update
     * @returns {Promise}
     */
    updateRow: function (rowState) {
        var self = this;
        var oldRowIds = [rowState.id].concat(rowState.childrenRowIds);
        var oldRows = [];
        oldRowIds.forEach(function (rowId) {
            if (self.rowWidgets[rowId]) {
                oldRows.push(self.rowWidgets[rowId]);
                delete self.rowWidgets[rowId];
            }
        });
        this.proms = [];
        var rows = this._renderRows([rowState], rowState.groupedBy);
        var proms = this.proms;
        delete this.proms;
        return Promise.all(proms).then(function () {
            var $previousRow = oldRows[0].$el;
            rows.forEach(function (row) {
                row.$el.insertAfter($previousRow);
                $previousRow = row.$el;
            });
            _.invoke(oldRows, 'destroy');
            if (!self.disableDragdrop) {
                self._setRowsDroppable();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Determines if a dragged pill aims to be copied or updated
     * @private
     * @param {jQueryEvent} event
     */
    _getAction: function (event) {
        return event.ctrlKey || event.metaKey ? 'copy': 'reschedule';
    },
    /**
     * Format focus date which is used to display in gantt header (see XML
     * template).
     *
     * @private
     */
    _getFocusDateFormat: function () {
        var focusDate = this.state.focusDate;
        switch (this.state.scale) {
            case 'day':
                return focusDate.format('dddd, MMMM DD, YYYY');
            case 'week':
                var dateStart = focusDate.clone().startOf('week').format('DD MMMM YYYY');
                var dateEnd = focusDate.clone().endOf('week').format('DD MMMM YYYY');
                return _.str.sprintf('%s - %s', dateStart, dateEnd);
            case 'month':
                return focusDate.format('MMMM YYYY');
            case 'year':
                return focusDate.format('YYYY');
            default:
                break;
        }
    },
    /**
     * Get dates between gantt start and gantt stop date to render gantt slots
     *
     * @private
     * @returns {Moment[]}
     */
    _getSlotsDates: function () {
        var token = this.SCALES[this.state.scale].interval;
        var stopDate = this.state.stopDate;
        var day = this.state.startDate;
        var dates = [];
        while (day <= stopDate) {
            dates.push(day);
            day = day.clone().add(1, token);
        }
        return dates;
    },
    /**
     * Prepare view info which is used by GanttRow widget
     *
     * @private
     * @returns {Object}
     */
    _prepareViewInfo: function () {
        return {
            colorField: this.colorField,
            progressField: this.progressField,
            consolidationParams: this.consolidationParams,
            state: this.state,
            fieldsInfo: this.fieldsInfo,
            slots: this._getSlotsDates(),
            pillDecorations: this.pillDecorations,
            popoverQWeb: this.popoverQWeb,
            activeScaleInfo: {
                precision: this.cellPrecisions[this.state.scale],
                interval: this.SCALES[this.state.scale].cellPrecisions[this.cellPrecisions[this.state.scale]],
                time: this.SCALES[this.state.scale].time,
            },
        };
    },
    /**
     * Renders gantt view and its rows.
     *
     * @override
     */
    async _renderView() {
        var self = this;
        var oldRowWidgets = Object.keys(this.rowWidgets).map(function (rowId) {
            return self.rowWidgets[rowId];
        });
        this.rowWidgets = {};
        this.viewInfo = this._prepareViewInfo();

        this.proms = [];
        var rows = this._renderRows(this.state.rows, this.state.groupedBy);
        var totalRow;
        if (this.totalRow) {
            totalRow = this._renderTotalRow();
        }
        this.proms.push(this._super.apply(this, arguments));
        var proms = this.proms;
        delete this.proms;
        return Promise.all(proms).then(function () {
            _.invoke(oldRowWidgets, 'destroy');
            self.$el.empty();

            self._replaceElement(QWeb.render(self.template_to_use, {widget: self, isMobile: config.device.isMobile}));
            const $containment = $('<div id="o_gantt_containment"/>');
            const $rowContainer = self.$('.o_gantt_row_container');
            $rowContainer.append($containment);
            if (!self.state.groupedBy.length) {
                $containment.css(self.isRTL ? {right: 0} : {left: 0});
            }

            rows.forEach(function (row) {
                row.$el.appendTo($rowContainer);
            });
            if (totalRow) {
                totalRow.$el.appendTo(self.$('.o_gantt_total_row_container'));
            }

            if (self._isInDom && !self.disableDragdrop) {
                self._setRowsDroppable();
            }

            if (self.state.isSample) {
                self._renderNoContentHelper();
            }
        });
    },
    /**
     * Render rows outside the DOM, so that we can insert them to the DOM once
     * they are all ready.
     *
     * @private
     * @param {Object[]} rows recursive structure of records according to
     *   groupBys
     * @param {string[]} groupedBy
     * @returns {Promise<GanttRow[]>} resolved with the row widgets
     */
    _renderRows: function (rows, groupedBy) {
        var self = this;
        var rowWidgets = [];
        var disableResize = this.state.scale === 'year';

        var groupLevel = this.state.groupedBy.length - groupedBy.length;
        // FIXME: could we get rid of collapseFirstLevel in Renderer, and fully
        // handle this in Model?
        var hideSidebar = groupedBy.length === 0;
        if (this.collapseFirstLevel) {
            hideSidebar = self.state.groupedBy.length === 0;
        }
        rows.forEach(function (row) {
            const pillsInfo = self._getPillsInfo(row, groupLevel);
            if (groupedBy.length) {
                pillsInfo.groupName = row.name;
                pillsInfo.groupedByField = row.groupedByField;
            }
            var params = {
                canCreate: self.canCreate,
                canCellCreate: self.canCellCreate,
                canEdit: self.canEdit,
                canPlan: self.canPlan,
                isGroup: row.isGroup,
                consolidate: (groupLevel === 0) && (self.state.groupedBy[0] === self.consolidationParams.maxField),
                hideSidebar: hideSidebar,
                isOpen: row.isOpen,
                disableResize: disableResize,
                disableDragdrop: self.disableDragdrop,
                rowId: row.id,
                fromServer: row.fromServer,
                scales: self.SCALES,
                unavailabilities: row.unavailabilities,
            };
            if (self.thumbnails && row.groupedByField && row.groupedByField in self.thumbnails){
                params.thumbnail = {model: self.fieldsInfo[row.groupedByField].relation, field: self.thumbnails[row.groupedByField],};
            }
            rowWidgets.push(self._renderRow(pillsInfo, params));
            if (row.isGroup && row.isOpen) {
                var subRowWidgets = self._renderRows(row.rows, groupedBy.slice(1));
                rowWidgets = rowWidgets.concat(subRowWidgets);
            }
        });
        return rowWidgets;
    },
    /**
     * Render a row outside the DOM.
     *
     * Note that we directly call the private function _widgetRenderAndInsert to
     * prevent from generating a documentFragment for each row we have to
     * render. The Widget API should offer a proper way to start a widget
     * without inserting it anywhere.
     *
     * @private
     * @param {Object} pillsInfo
     * @param {Object} params
     * @returns {Promise<GanttRow>} resolved when the row is ready
     */
    _renderRow: function (pillsInfo, params) {
        var ganttRow = new this.config.GanttRow(this, pillsInfo, this.viewInfo, params);
        this.rowWidgets[ganttRow.rowId] = ganttRow;
        this.proms.push(ganttRow._widgetRenderAndInsert(function () {}));
        return ganttRow;
    },
    /**
     * Renders the total row outside the DOM, so that we can insert it to the
     * DOM once all rows are ready.
     *
     * @returns {Promise<GanttRow} resolved with the row widget
     */
    _renderTotalRow: function () {
        var pillsInfo = {
            pills: this.state.records,
            groupLevel: 0,
            groupName: "Total"
        };
        var params = {
            canCreate: this.canCreate,
            canCellCreate: this.canCellCreate,
            canEdit: this.canEdit,
            canPlan: this.canPlan,
            hideSidebar: this.state.groupedBy.length === 0,
            isGroup: true,
            rowId: '__total_row__',
            scales: this.SCALES,
        };
        return this._renderRow(pillsInfo, params);
    },
    /**
     * Set droppable on all rows
     */
    _setRowsDroppable: function () {
        // jQuery (< 3.0) rounds the width value but we need the exact value
        // getBoundingClientRect is costly when there are lots of rows
        const firstCell = this.$('.o_gantt_header_scale .o_gantt_header_cell:first')[0];
        _.invoke(this.rowWidgets, 'setDroppable', firstCell);
    },
    /**
     * Get pills info
     *
     * @param {Object} row
     * @param {*} groupLevel
     */
    _getPillsInfo: function (row, groupLevel) {
        return {
            resId: row.resId,
            pills: row.records,
            groupLevel: groupLevel,
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        this.action = this._getAction(ev);
        if (this.$draggedPill && this.action === 'copy') {
            this.$el.addClass('o_copying');
            this.$el.removeClass('o_grabbing');
        }
    },
    /**
     * @param {KeyboardEvent} ev
     */
    _onKeyup: function (ev) {
        this.action = this._getAction(ev);
        if (this.$draggedPill && this.action === 'reschedule') {
            this.$el.addClass('o_grabbing');
            this.$el.removeClass('o_copying');
        }
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onStartDragging: function (event) {
        this.$draggedPill = event.data.$draggedPill;
        this.$draggedPill.addClass('o_dragged_pill');
        if (this.action === 'copy') {
            this.$el.addClass('o_copying');
        } else {
            this.$el.addClass('o_grabbing');
        }
    },
    /**
     * Used to give a feedback on the impossibility of moving the pill
     * @private
     */
    _onStartNoDragging: function () {
        this.$el.addClass('o_no_dragging');
    },
    /**
     * @private
     */
    _onStopDragging: function () {
        this.$draggedPill.removeClass('o_dragged_pill');
        this.$draggedPill = null;
        this.$draggedPillClone = null;
        this.$el.removeClass('o_grabbing');
        this.$el.removeClass('o_copying');
    },
    /**
     * @private
     */
    _onStopNoDragging: function () {
        this.$el.removeClass('o_no_dragging');
    },
});

return GanttRenderer;

});
