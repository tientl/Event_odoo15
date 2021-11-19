odoo.define('timesheet_grid.timesheet_kanban_view', function (require) {
"use strict";

const KanbanController = require('web.KanbanController');
const KanbanView = require('web.KanbanView');
const KanbanRenderer = require('web.KanbanRenderer');
const viewRegistry = require('web.view_registry');
const QRCodeMixin = require('hr_timesheet.res.config.form');

/**
 * @override the KanbanController to add a trigger when a timer is launched or stopped
 */
const TimesheetKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        'timer_changed': '_onTimerChanged',
    }),
    /**
     * When a timer is launched or stopped, we reload the view to see the updating.
     * @private
     * @param {Object} event
     */
    _onTimerChanged: function (event) {
        this.reload();
    }
});

const TimesheetKanbanRenderer = KanbanRenderer.extend(QRCodeMixin.TimesheetConfigQRCodeMixin);

const TimesheetKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: TimesheetKanbanController,
        Renderer: TimesheetKanbanRenderer,
    })
});

viewRegistry.add('timesheet_kanban_view', TimesheetKanbanView);

return { TimesheetKanbanController, TimesheetKanbanView, TimesheetKanbanRenderer };

});
