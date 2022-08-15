/** @odoo-module **/

import MainMenu from "@stock_barcode/stock_barcode_menu";

MainMenu.include({
    events: Object.assign({}, MainMenu.prototype.events, {
        'click .button_batch_transfer': '_onClickBatchTransfer',
    }),

    // --------------------------------------------------------------------------
    // Handlers
    // --------------------------------------------------------------------------

    /**
     * Open batch picking's kanban view with all batch picking in progress.
     *
     * @private
     */
    _onClickBatchTransfer: function () {
        this.do_action('stock_barcode_picking_batch.stock_barcode_batch_picking_action_kanban');
    },
});
