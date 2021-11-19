odoo.define('stock_barcode.BatchPickingKanbanRecord', function (require) {
'use strict';

const KanbanRecord = require('web.KanbanRecord');

const StockBarcodePickingBatch = KanbanRecord.include({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'stock.picking.batch' && this.$el.parents('.o_stock_barcode_kanban').length) {
            this._rpc({
                model: 'stock.picking.batch',
                method: 'action_client_action',
                args: [this.id],
            }).then(action => {
                this.do_action(action);
            });
        } else {
            this._super.apply(this, arguments);
        }
    }
});

return StockBarcodePickingBatch;
});

odoo.define('stock_barcode.BatchPickingKanbanController', function (require) {
    "use strict";

const StockBarcodeKanbanController = require('stock_barcode.BarcodeKanbanController');

StockBarcodeKanbanController.include({
    // --------------------------------------------------------------------------
    // Handlers
    // ---------------------------------------------------------------------------

    /**
     * Add a new batch picking from barcode
     *
     * @private
     * @override
     */
    _onButtonNew: function (ev) {
        if (this.modelName === 'stock.picking.batch') {
            this._rpc({
                model: 'stock.picking.batch',
                method: 'open_new_batch_picking',
            }).then((result) => {
                this.do_action(result.action);
            });
        } else {
            this._super(...arguments);
        }
    },
});
});
