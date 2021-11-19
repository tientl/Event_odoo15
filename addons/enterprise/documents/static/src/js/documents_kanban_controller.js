odoo.define('documents.DocumentsKanbanController', function (require) {
'use strict';

/**
 * This file defines the Controller for the Documents Kanban view, which is an
 * override of the KanbanController.
 */

const DocumentsControllerMixin = require('documents.controllerMixin');

const KanbanController = require('web.KanbanController');

var DocumentsKanbanController = KanbanController.extend(DocumentsControllerMixin, {
    events: Object.assign({}, KanbanController.prototype.events, DocumentsControllerMixin.events),
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, DocumentsControllerMixin.custom_events),

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        DocumentsControllerMixin.init.apply(this, arguments);
    },
    /**
     * @override
     */
    async start() {
        this.$('.o_content').addClass('o_documents_content o_documents_kanban');
        await this._super(...arguments);
        DocumentsControllerMixin.start.apply(this, arguments);
    },
    /**
     * Override to update the records selection.
     *
     * @override
     */
    async reload() {
        await this._super(...arguments);
        await DocumentsControllerMixin.reload.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async _update() {
        await this._super(...arguments);
        await DocumentsControllerMixin._update.apply(this, arguments);
    },
    /**
     * @override
     * @private
     */
    updateButtons() {
        this._super(...arguments);
        DocumentsControllerMixin.updateButtons.apply(this, arguments);
    },
});

return DocumentsKanbanController;

});
