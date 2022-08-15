odoo.define('industry_fsm_sale.ProductKanbanModel', function (require) {
"use strict";

const KanbanModel = require('web.KanbanModel');

return KanbanModel.extend({

    /**
     * Handles the field `fsm_quantity`.
     * Saving this field cannot be done as any regular field
     * since it might require additional actions from the user.
     * e.g. set product serial numbers
     * @param {string} recordID
     * @param {object} options
     * @returns {Promise<string>} Changed fields
     * @override
     */
    async save(recordID, options) {
        const record = this.localData[recordID];
        const changes = record._changes;
        let rpc = null;

        if (changes && changes.fsm_quantity !== undefined) {
            const quantity = changes.fsm_quantity;
            delete changes.fsm_quantity;
            rpc = this._getEditFSMQuantityRpc(record, quantity);
        } else if (options && options.fsm_quantity_action) {
            rpc = this._getFSMQuantityButtonRpc(record, options.fsm_quantity_action);
        }

        if (rpc) {
            const changedFields = await Promise.all([
                this._super(...arguments),
                this._saveFSMQuantity(rpc),
            ]);
            await this._fetchRecord(record);
            return changedFields.flat();
        }
        return this._super(...arguments);
    },

    /**
     * Saves the FSM quantity.
     * @param {object} rpc the rpc to call to update the product quantity.
     * @returns {Promise<string>} changed field
     */
    async _saveFSMQuantity(rpc) {
        const action = await this._rpc(rpc);
        if (typeof action === 'object') {
            await new Promise((resolve) => {
                this.do_action(action, { on_close: resolve });
            });
        }
        return ['fsm_quantity'];
    },

    /**
     * Get the rpc to send to edit manually the FSM quantity.
     *
     * @param {object} record the product to update the quantity.
     * @param {number} quantity the fsm quantity to set in the product.
     */
    _getEditFSMQuantityRpc(record, quantity) {
        return {
            model: 'product.product',
            method: 'set_fsm_quantity',
            args: [record.data.id, quantity],
            context: record.getContext(),
        };
    },

    /**
     * Get the rpc based on the action given in parameter.
     *
     * @param {object} record the record to update.
     * @param {string} action this action is the button clicked by the user in the FSMProductQuantity widget.
     * @returns {object} the rpc to call.
     */
    _getFSMQuantityButtonRpc(record, action) {
        return {
            model: 'product.product',
            method: action,
            args: [record.data.id],
            context: record.getContext(),
        };
    }
});

});
