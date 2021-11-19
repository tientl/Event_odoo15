odoo.define('timesheet_grid.timesheet_list_view', function (require) {
"use strict";

const ListController = require('web.ListController');
const ListView = require('web.ListView');
const ListRenderer = require('web.ListRenderer');
const QRCodeMixin = require('hr_timesheet.res.config.form');
const viewRegistry = require('web.view_registry');

/**
 * @override the ListController to add a trigger when the timer is launched or stopped
 */
const TimesheetListController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
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

const TimesheetListRenderer = ListRenderer.extend(QRCodeMixin.TimesheetConfigQRCodeMixin);

const TimesheetListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: TimesheetListController,
        Renderer: TimesheetListRenderer
    })
});

viewRegistry.add('timesheet_tree', TimesheetListView);

return { TimesheetListController, TimesheetListView, TimesheetListRenderer };

});
