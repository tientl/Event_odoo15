odoo.define('timesheet_grid.timesheet_pivot_view', function (require) {
    "use strict";
    
    const PivotView = require('web.PivotView');
    const PivotRenderer = require('web.PivotRenderer');
    const TimesheetConfigQRCodeMixin = require('timesheet_grid.TimesheetConfigQRCodeMixin');
    const viewRegistry = require('web.view_registry');
    const { onMounted, onPatched } = owl.hooks;

    class TimesheetGridRenderer extends PivotRenderer {
        constructor() {
            super(...arguments);
            onMounted(() => this._bindPlayStoreIcon());
            onPatched(() => this._bindPlayStoreIcon());
        }
    }

    // QRCode mixin to bind event on play store icon
    Object.assign(PivotRenderer.prototype, TimesheetConfigQRCodeMixin);

    const TimesheetPivotView = PivotView.extend({
        config: _.extend({}, PivotView.prototype.config, {
            Renderer: TimesheetGridRenderer
        })
    });

    viewRegistry.add('timesheet_pivot_view', TimesheetPivotView);

    return { TimesheetPivotView, TimesheetGridRenderer };

});
