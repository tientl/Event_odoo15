odoo.define('stock_enterprise.ReportGridController', function (require) {
"use strict";

var GridController = require('web_grid.GridController');
var utils = require('web.utils');
var core = require('web.core');
var _t = core._t;

var ReportGridController = GridController.extend({
    /**
     * @override
     * @return {Promise} Override magnifying glass click function in order to
     * excute an action that display the stock.move for the selected grid
     * cell.
     *
     */
    _onOpenCellInformation: function (ev) {
        var self = this;
        var state = this.model.get();
        var cellPath = ev.data.path.split('.');
        var rowPath = cellPath.slice(0, -3).concat(['rows'], cellPath.slice(-2, -1));
        var row = utils.into(state.data, rowPath);
        var colPath = cellPath.slice(0, -3).concat(['cols'], cellPath.slice(-1));
        var col = utils.into(state.data, colPath);
        if (!row.values.product_id) {
            this.displayNotification({ message: _t("Only grouping by product is supported"), type: 'danger' });
            return;
        }
        return this._rpc({
            model: 'report.stock.quantity',
            method: 'action_open_moves',
            args: [
                row.values.product_id[0],
                row.values.state.data,
                col.values.date[0].split('/')[0],
            ]
        }).then(function (action) {
            return self.do_action(action);
        });
    },
});

return ReportGridController;

});
