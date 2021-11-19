odoo.define('stock_barcode.BarcodeKanbanRenderer', function (require) {
"use strict";

var StockBarcodeKanbanRecord = require('stock_barcode.BarcodeKanbanRecord');
var {bus, qweb} = require('web.core');

var KanbanRenderer = require('web.KanbanRenderer');

var StockBarcodeListKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: StockBarcodeKanbanRecord,
    }),

    init: function (parent, state, params) {
        this._super(...arguments);
        this.model = state.model;
    },

    /**
     * @override
     */
    on_attach_callback: function () {
        this._switchBarcodeListener(true);
        this._super(...arguments);
    },

    /**
     * @override
     */
    on_detach_callback: function () {
        this._switchBarcodeListener(false);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _render: function () {
        return this._super(...arguments).then(() => {
            const scanProductTip = qweb.render('scan_product_tip', {
                display_protip: ['stock.picking'].includes(this.model),
            });
            this.$el.prepend(scanProductTip);
        });
    },

    /**
     * Add or remove the listener.
     *
     * @param {boolean} activate
     */
    _switchBarcodeListener: function (activate) {
        if (activate) {
            bus.on('barcode_scanned', this, this._onBarcodeScannedHandler);
        } else {
            bus.off('barcode_scanned', this, this._onBarcodeScannedHandler);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handle the barcode scanning event.
     *
     * @param {String} barcode
     */
    _onBarcodeScannedHandler: function (barcode) {
        this.trigger_up('kanban_scan_barcode', {barcode});
    },
});

return StockBarcodeListKanbanRenderer;

});
