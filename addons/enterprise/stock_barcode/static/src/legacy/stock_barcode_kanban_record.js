odoo.define('stock_barcode.BarcodeKanbanRecord', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

var StockBarcodeKanbanRecord = KanbanRecord.extend({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'stock.picking' && $('.modal-dialog').length === 0) {
            this.$('button').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    }
});

return StockBarcodeKanbanRecord;

});

odoo.define('stock_barcode.BarcodeKanbanController', function (require) {
"use strict";
var KanbanController = require('web.KanbanController');

var StockBarcodeKanbanController = KanbanController.extend({
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, {
        kanban_scan_barcode: '_onBarcodeScannedHandler',
    }),

    // --------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called by the kanban renderer when the user scans a barcode.
     *
     * @param {OdooEvent} ev
     */
    _onBarcodeScannedHandler: function (ev) {
        if (!['stock.picking'].includes(this.modelName)) {
            return;
        }
        const {barcode} = ev.data;
        this._rpc({
            model: this.modelName,
            method: 'filter_on_product',
            kwargs: {
                barcode,
                context: this.initialState.context,
            }
        }).then(result => {
            if (result.action) {
                this.do_action(result.action, {
                    replace_last_action: true,
                });
            } else if (result.warning) {
                this.displayNotification({ title: result.warning.title, message: result.warning.message, type: 'danger' });
            }
        });
    },

    /**
     * Do not add a record but open new barcode views.
     *
     * @private
     * @override
     */
    _onButtonNew: async function (ev) {
        // Keep `_super` into a variable as the reference will be lost after the RPC.
        const superOnButtonNew = this._super.bind(this);
        if (this.modelName === 'stock.picking') {
            const action = await this._rpc({
                model: 'stock.picking',
                method: 'action_open_new_picking',
                context: this.initialState.context,
            });
            if (action) {
                return this.do_action(action);
            }
        }
        return superOnButtonNew(...arguments);
    },
});
return StockBarcodeKanbanController;

});
