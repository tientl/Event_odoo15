odoo.define('industry_fsm_sale.ProductKanbanController', function (require) {
"use strict";

const KanbanController = require('web.KanbanController');

return KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        'fsm_add_quantity': '_onActionFSMQuantity',
        'fsm_remove_quantity': '_onActionFSMQuantity',
    }),

    /**
     * Change the product quantity when the user clicks on the fsm_add_quantity or fsm_remove_button button.
     *
     * To do this, we call the save method in the model to update the fsm quantity of the product in which the user clicks on the button.
     *
     * @param {OdooEvent} e
     * @param {string} e.name the method to call in the product.product model.
     * @param {string} e.data.dataPointID the record id stored in the localData of the model.
     */
    _onActionFSMQuantity: async function (e) {
        e.stopPropagation();
        return this.model.save(e.data.dataPointID, {fsm_quantity_action: e.name})
            .then(() => this._confirmSave(e.data.dataPointID))
            .guardedCatch(() => this._rejectSave(e.data.dataPointID));
    },
});

});
