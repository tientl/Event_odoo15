odoo.define('documents.DocumentsListController', function (require) {
'use strict';

const DocumentsControllerMixin = require('documents.controllerMixin');
const ListController = require('web.ListController');
const framework = require('web.framework');

const { qweb } = require('web.core');

const DocumentsListController = ListController.extend(DocumentsControllerMixin, {
    events: Object.assign({}, ListController.prototype.events, DocumentsControllerMixin.events),
    custom_events: Object.assign({}, ListController.prototype.custom_events, DocumentsControllerMixin.custom_events, {
        documents_view_rendered: '_onDocumentsViewRendered',
        toggle_all: '_onToggleAll',
    }),

    async _renderDocumentsInspector(state) {
        const existingRecordIds = new Set();
        for (const record of state.data) {
            existingRecordIds.add(record.res_id);
        }
        const missingRecordIds = this._selectedRecordIds.filter(e => !existingRecordIds.has(e));
        if (missingRecordIds.length > 0) {
            await this.model.loadMissingData({state, ids: missingRecordIds});
        }
        await DocumentsControllerMixin._renderDocumentsInspector.call(this, state);
    },

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
        this.$('.o_content').addClass('o_documents_content');
        await this._super(...arguments);
        DocumentsControllerMixin.start.apply(this, arguments);
    },

    /**
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDocumentsViewRendered() {
        this.$('.o_data_row').attr('draggable', true).addClass('o_document_draggable o_document_list_record');
        const localData = this.model.localData;
        for (const key in localData) {
            const $record = this.$(`.o_document_list_record[data-id="${key}"]`);
            $record.attr('data-res-id', localData[key].data.id);
            const lockLocalId = localData[key].data.lock_uid;
            if (lockLocalId) {
                const lockUidData = localData[lockLocalId].data;
                $record.find('.o_data_cell:nth(0)').append(qweb.render('documents.lockIcon', {
                    tooltip: lockUidData.display_name,
                }));
            }
        }
    },

    _onSelectDomain(ev) {
        this._super(...arguments);
        framework.blockUI();
        this.getSelectedIdsWithDomain()
            .then(ids => this._selectedRecordIds = ids)
            .then(() => {
                const state = this.model.get(this.handle);
                return Promise.all([
                    this._updateChatter(state),
                    this._renderDocumentsInspector(state)
                ])
            })
            .finally(() => framework.unblockUI());
    },

    /**
     *
     * @private
     * @param {OdooEvent} ev
     */
    async _onToggleAll(ev) {
        const state = this.model.get(this.handle);
        this._selectedRecordIds = ev.data.checked ? state.data.map(record => record.res_id) : [];
        await Promise.all([
            this._updateChatter(state),
            this._renderDocumentsInspector(state)
        ]);
        this._updateSelection();
    },

});

return DocumentsListController;

});
