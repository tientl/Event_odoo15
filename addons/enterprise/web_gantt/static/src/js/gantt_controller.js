odoo.define('web_gantt.GanttController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var core = require('web.core');
var config = require('web.config');
var dialogs = require('web.view_dialogs');
var confirmDialog = require('web.Dialog').confirm;

var QWeb = core.qweb;
var _t = core._t;

var GanttController = AbstractController.extend({
    events: _.extend({}, AbstractController.prototype.events, {
        'click .o_gantt_button_add': '_onAddClicked',
        'click .o_gantt_button_scale': '_onScaleClicked',
        'click .o_gantt_button_prev': '_onPrevPeriodClicked',
        'click .o_gantt_button_next': '_onNextPeriodClicked',
        'click .o_gantt_button_today': '_onTodayClicked',
        'click .o_gantt_button_expand_rows': '_onExpandClicked',
        'click .o_gantt_button_collapse_rows': '_onCollapseClicked',
    }),
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        add_button_clicked: '_onCellAddClicked',
        plan_button_clicked: '_onCellPlanClicked',
        collapse_row: '_onCollapseRow',
        expand_row: '_onExpandRow',
        pill_clicked: '_onPillClicked',
        pill_resized: '_onPillResized',
        pill_dropped: '_onPillDropped',
        updating_pill_started: '_onPillUpdatingStarted',
        updating_pill_stopped: '_onPillUpdatingStopped',
    }),
    buttonTemplateName: 'GanttView.buttons',

    /**
     * @override
     * @param {Widget} parent
     * @param {GanttModel} model
     * @param {GanttRenderer} renderer
     * @param {Object} params
     * @param {Object} params.context
     * @param {Array[]} params.dialogViews
     * @param {Object} params.SCALES
     * @param {boolean} params.collapseFirstLevel
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.model = model;
        this.context = params.context;
        this.dialogViews = params.dialogViews;
        this.SCALES = params.SCALES;
        this.allowedScales = params.allowedScales;
        this.collapseFirstLevel = params.collapseFirstLevel;
        this.createAction = params.createAction;
        this.actionDomain = params.actionDomain;

        this.isRTL = _t.database.parameters.direction === "rtl";
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQuery} [$node] to which the buttons will be appended
     */
    renderButtons: function ($node) {
        this.$buttons = this._renderButtonsQWeb();
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },
    _renderButtonsQWeb: function () {
        return $(QWeb.render(this.buttonTemplateName, this._renderButtonQWebParameter()));
    },
    _renderButtonQWebParameter: function () {
        var state = this.model.get();
        var nbGroups = state.groupedBy.length;
        var minNbGroups = this.collapseFirstLevel ? 0 : 1;
        var displayExpandCollapseButtons = nbGroups > minNbGroups;
        return {
            groupedBy: state.groupedBy,
            widget: this,
            SCALES: this.SCALES,
            activateScale: state.scale,
            allowedScales: this.allowedScales,
            displayExpandCollapseButtons: displayExpandCollapseButtons,
            isMobile: config.device.isMobile,
        };
    },
    /**
     * @override
     */
    updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        this.$buttons.html(this._renderButtonsQWeb());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {integer} id
     * @param {Object} schedule
     */
    _copy: function (id, schedule) {
        return this._executeAsyncOperation(
            this.model.copy.bind(this.model),
            [id, schedule]
        );
    },
    /**
     * @private
     * @param {function} operation
     * @param {Array} args
     */
    _executeAsyncOperation: function (operation, args) {
        const self = this;
        var prom = new Promise(function (resolve, reject) {
            var asyncOp = operation(...args);
            asyncOp.then(resolve).guardedCatch(resolve);
            self.dp.add(asyncOp).guardedCatch(reject);
        });
        return prom.then(this.reload.bind(this, {}));
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _getDialogContext: function (date, rowId) {
        var state = this.model.get();
        var context = {};
        context[state.dateStartField] = date.clone();
        context[state.dateStopField] = date.clone().endOf(this.SCALES[state.scale].interval);
        if (rowId) {
            // Default values of the group this cell belongs in
            // We can read them from any pill in this group row
            _.each(state.groupedBy, function (fieldName) {
                const groupValue = Object.assign({}, ...JSON.parse(rowId));
                var value = groupValue[fieldName];
                if (Array.isArray(value)) {
                    const { type: fieldType } = state.fields[fieldName];
                    if (fieldType === "many2many") {
                        value = [value[0]];
                    } else if (fieldType === "many2one") {
                        value = value[0];
                    }
                }
                if (value !== undefined) {
                    context[fieldName] = value;
                }
            });
        }

        // moment context dates needs to be converted in server time in view
        // dialog (for default values)
        for (var k in context) {
            var type = state.fields[k].type;
            if (context[k] && (type === 'datetime' || type === 'date')) {
                context[k] = this.model.convertToServerTime(context[k]);
            }
        }

        return context;
    },
    /**
     * Opens dialog to add/edit/view a record
     *
     * @private
     * @param {integer|undefined} resID
     * @param {Object|undefined} context
     * @returns {FormViewDialog}
     */
    _openDialog: function (resID, context) {
        var title = resID ? _t("Open") : _t("Create");

        return new dialogs.FormViewDialog(this, {
            title: _.str.sprintf(title),
            res_model: this.modelName,
            view_id: this.dialogViews[0][0],
            res_id: resID,
            readonly: !this.is_action_enabled('edit'),
            deletable: this.is_action_enabled('delete') && resID,
            context: _.extend({}, this.context, context),
            on_saved: this.reload.bind(this, {}),
            on_remove: this._onDialogRemove.bind(this, resID),
        }).open();
    },
    /**
     * Handler called when clicking the
     * delete button in the edit/view dialog.
     * Reload the view and close the dialog
     *
     * @returns {function}
     */
    _onDialogRemove: function (resID) {
        var controller = this;

        var confirm = new Promise(function (resolve) {
            confirmDialog(this, _t('Are you sure to delete this record?'), {
                confirm_callback: function () {
                    resolve(true);
                },
                cancel_callback: function () {
                    resolve(false);
                },
            });
        });

        return confirm.then(function (confirmed) {
            if ((!confirmed)) {
                return Promise.resolve();
            }// else
            return controller._rpc({
                model: controller.modelName,
                method: 'unlink',
                args: [[resID,],],
            }).then(function () {
                return controller.reload();
            })
        });
    },
    /**
     * Opens dialog to plan records.
     *
     * @private
     * @param {Object} context
     */
    _openPlanDialog: function (context) {
        var self = this;
        var state = this.model.get();
        var domain = [
            '|',
            [state.dateStartField, '=', false],
            [state.dateStopField, '=', false],
        ];
        new dialogs.SelectCreateDialog(this, {
            title: _t("Plan"),
            res_model: this.modelName,
            domain: this.actionDomain.concat(domain),
            views: this.dialogViews,
            context: _.extend({}, this.context, context),
            on_selected: function (records) {
                var ids = _.pluck(records, 'id');
                if (ids.length) {
                    // Here, the dates are already in server time so we set the
                    // isUTC parameter of reschedule to true to avoid conversion
                    self._reschedule(ids, context, true, self.openPlanDialogCallback);
                }
            },
        }).open();
    },
    /**
     * upon clicking on the create button, determines if a dialog with a formview should be opened
     * or if a wizard should be openned, then opens it
     *
     * @param {object} context
     */
    _onCreate: function (context) {
        if (this.createAction) {
            var fullContext = _.extend({}, this.context, context);
            this.do_action(this.createAction, {
                additional_context: fullContext,
                on_close: this.reload.bind(this, {})
            });
        } else {
            this._openDialog(undefined, context);
        }
    },
    /**
     * Reschedule records and reload.
     *
     * Use a DropPrevious to prevent unnecessary reload and rendering.
     *
     * Note that when the rpc fails, we have to reload and re-render as some
     * records might be outdated, causing the rpc failure).
     *
     * @private
     * @param {integer[]|integer} ids
     * @param {Object} schedule
     * @param {boolean} isUTC
     * @returns {Promise} resolved when the record has been reloaded, rejected
     *   if the request has been dropped by DropPrevious
     */
    _reschedule: function (ids, schedule, isUTC, callback) {
        return this._executeAsyncOperation(
            this.model.reschedule.bind(this.model),
            [ids, schedule, isUTC, callback]
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens a dialog to create a new record.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCellAddClicked: function (ev) {
        ev.stopPropagation();
        const context = this._getDialogContext(ev.data.date, ev.data.rowId);
        for (var k in context) {
            context[_.str.sprintf('default_%s', k)] = context[k];
        }
        this._onCreate(context);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddClicked: function (ev) {
        ev.preventDefault();
        var context = {};
        var state = this.model.get();
        context[state.dateStartField] = this.model.convertToServerTime(state.focusDate.clone().startOf(state.scale));
        context[state.dateStopField] = this.model.convertToServerTime(state.focusDate.clone().endOf(state.scale));
        for (var k in context) {
            context[_.str.sprintf('default_%s', k)] = context[k];
        }
        this._onCreate(context);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCollapseClicked: function (ev) {
        ev.preventDefault();
        this.model.collapseRows();
        this.update({}, { reload: false });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.rowId
     */
    _onCollapseRow: function (ev) {
        ev.stopPropagation();
        this.model.collapseRow(ev.data.rowId);
        this.renderer.updateRow(this.model.get(ev.data.rowId));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onExpandClicked: function (ev) {
        ev.preventDefault();
        this.model.expandRows();
        this.update({}, { reload: false });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.rowId
     */
    _onExpandRow: function (ev) {
        ev.stopPropagation();
        this.model.expandRow(ev.data.rowId);
        this.renderer.updateRow(this.model.get(ev.data.rowId));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onNextPeriodClicked: function (ev) {
        ev.preventDefault();
        var state = this.model.get();
        this.update({ date: state.focusDate.add(1, state.scale) });
    },
    /**
     * Opens dialog when clicked on pill to view record.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {jQuery} ev.data.target
     */
    _onPillClicked: async function (ev) {
        if (!this._updating) {
            ev.data.target.addClass('o_gantt_pill_editing');

            // Sync with the mutex to wait for potential changes on the view
            await this.model.mutex.getUnlockedDef();

            var dialog = this._openDialog(ev.data.target.data('id'));
            dialog.on('closed', this, function () {
                ev.data.target.removeClass('o_gantt_pill_editing');
            });
        }
    },
    /**
     * Saves pill information when dragged.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {integer} [ev.data.diff]
     * @param {integer} [ev.data.groupLevel]
     * @param {string} [ev.data.pillId]
     * @param {string} [ev.data.newRowId]
     * @param {string} [ev.data.oldRowId]
     * @param {'copy'|'reschedule'} [ev.data.action]
     */
    _onPillDropped: function (ev) {
        ev.stopPropagation();

        var state = this.model.get();

        var schedule = {};

        var diff = ev.data.diff;
        diff = this.isRTL ? -diff : diff;
        if (diff) {
            var pill = _.findWhere(state.records, { id: ev.data.pillId });
            schedule[state.dateStartField] = this.model.dateAdd(pill[state.dateStartField], diff, this.SCALES[state.scale].time);
            schedule[state.dateStopField] = this.model.dateAdd(pill[state.dateStopField], diff, this.SCALES[state.scale].time);
        } else if (ev.data.action === 'copy') {
            // When we copy the info on dates is sometimes mandatory (e.g. working on hr.leave, see copy_data)
            const pill = _.findWhere(state.records, { id: ev.data.pillId });
            schedule[state.dateStartField] = pill[state.dateStartField].clone();
            schedule[state.dateStopField] = pill[state.dateStopField].clone();
        }

        if (ev.data.newRowId && ev.data.newRowId !== ev.data.oldRowId) {
            const groupValue = Object.assign({}, ...JSON.parse(ev.data.newRowId));

            // if the pill is dragged in a top level group, we only want to
            // write on fields linked to this top level group
            var fieldsToWrite = state.groupedBy.slice(0, ev.data.groupLevel + 1);
            _.each(fieldsToWrite, function (fieldName) {
                // TODO: maybe not write if the value hasn't changed?
                let valueToWrite = groupValue[fieldName];
                if (Array.isArray(valueToWrite)) {
                    const { type: fieldType } = state.fields[fieldName];
                    if (fieldType === "many2many") {
                        valueToWrite = [valueToWrite[0]];
                    } else if (fieldType === "many2one") {
                        valueToWrite = valueToWrite[0];
                    }
                }
                schedule[fieldName] = valueToWrite;
            });
        }
        if (ev.data.action === 'copy') {
            this._copy(ev.data.pillId, schedule);
        } else {
            this._reschedule(ev.data.pillId, schedule);
        }
    },
    /**
     * Save pill information when resized
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPillResized: function (ev) {
        ev.stopPropagation();
        var schedule = {};
        schedule[ev.data.field] = ev.data.date;
        this._reschedule(ev.data.id, schedule);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onPillUpdatingStarted: function (ev) {
        ev.stopPropagation();
        this._updating = true;
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onPillUpdatingStopped: function (ev) {
        ev.stopPropagation();
        this._updating = false;
    },
    /**
     * Opens a dialog to plan records.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCellPlanClicked: function (ev) {
        ev.stopPropagation();
        const context = this._getDialogContext(ev.data.date, ev.data.rowId);
        this._openPlanDialog(context);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPrevPeriodClicked: function (ev) {
        ev.preventDefault();
        var state = this.model.get();
        this.update({ date: state.focusDate.subtract(1, state.scale) });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onScaleClicked: function (ev) {
        ev.preventDefault();
        var $button = $(ev.currentTarget);
        if ($button.hasClass('active')) {
            return;
        }
        this.update({ scale: $button.data('value') });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onTodayClicked: function (ev) {
        ev.preventDefault();
        this.update({ date: moment() });
    },
});

return GanttController;

});
