odoo.define('documents.DocumentsKanbanControllerMobile', function (require) {
"use strict";

const config = require('web.config');
if (!config.device.isMobile) {
    return;
}

const DocumentsKanbanController = require('documents.DocumentsKanbanController');
const DocumentsListController = require('documents.DocumentsListController');

const { qweb } = require('web.core');

const DocumentControllerMobileMixin = {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Group ControlPanel's buttons into a dropdown.
     *
     * @override
     */
    renderButtons() {
        this._super(...arguments);
        const $buttons = this.$buttons.find('button');
        const $dropdownButton = $(qweb.render('documents.ControlPanelButtonsMobile'));
        $buttons.addClass('dropdown-item').appendTo($dropdownButton.find('.dropdown-menu'));
        this.$buttons = $dropdownButton;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {MouseEvent} ev
     */
    async _deferredRenderInspector(ev) {
        await this._super(...arguments);
        if (!ev.data.isKeepSelection && this._selectedRecordIds.length === 1) {
            this._documentsInspector.open();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the DocumentsInspector when a record is directly selected.
     *
     * @override
     * @private
     * @param {OdooEvent} ev
     * @param {boolean} ev.data.isKeepSelection if true, unselect other records
     * @param {string} ev.data.resId the resId of the record updating its status
     */
    async _onSelectRecord(ev) {
        // don't update the selection if the record is currently the only selected one
        if (
            ev.data.isKeepSelection ||
            this._selectedRecordIds.length !== 1 ||
            this._selectedRecordIds[0] !== ev.data.resId
        ) {
            await this._super(...arguments);
        }
    },
};

DocumentsKanbanController.include(DocumentControllerMobileMixin);
DocumentsListController.include(DocumentControllerMobileMixin);

});
