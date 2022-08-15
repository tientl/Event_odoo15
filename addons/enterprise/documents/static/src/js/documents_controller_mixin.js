odoo.define('documents.controllerMixin', function (require) {
'use strict';

const DocumentsInspector = require('documents.DocumentsInspector');
const DocumentViewer = require('documents.DocumentViewer');
const { computeMultiSelection } = require('documents.utils');

const { getMessagingComponent } = require('@mail/utils/messaging_component');

const { _t, qweb } = require('web.core');
const config = require('web.config');
const { Markup } = require('web.utils');
const fileUploadMixin = require('web.fileUploadMixin');
const session = require('web.session');
const { ComponentWrapper } = require('web.OwlCompatibility');
const Dialog = require('web.Dialog');

class ChatterContainerWrapperComponent extends ComponentWrapper {}


const DocumentsControllerMixin = Object.assign({}, fileUploadMixin, {

    events: {
        'click .o_documents_kanban_share_domain': '_onClickDocumentsShareDomain',
        'click .o_documents_kanban_upload': '_onClickDocumentsUpload',
        'click .o_documents_kanban_url': '_onClickDocumentsUploadFromUrl',
        'click .o_documents_kanban_request': '_onClickDocumentsRequest',
        'dragleave .o_documents_view': '_onDragleaveDocumentsView',
        'dragover .o_documents_view': '_onDragoverDocumentsView',
        'dragstart .o_document_draggable': '_onDragstartDocumentDraggable',
        'drop .o_documents_view': '_onDropDocumentsView',
    },
    custom_events: Object.assign({}, fileUploadMixin.custom_events, {
        archive_records: '_onArchiveRecords',
        delete_model: '_onDeleteModel',
        delete_records: '_onDeleteRecords',
        document_viewer_attachment_changed: '_onDocumentViewerAttachmentChanged',
        download: '_onDownload',
        edit_model: '_onEditModel',
        get_search_panel_tags: '_onGetSearchPanelTags',
        history_item_delete: '_onHistoryItemDelete',
        history_item_download: '_onHistoryItemDownload',
        history_item_restore: '_onHistoryItemRestore',
        kanban_image_clicked: '_onKanbanImageClicked',
        lock_attachment: '_onLockAttachment',
        // relates to owl custom event o-close-chatter
        o_close_chatter: '_onDocumentsCloseChatter',
        open_chatter: '_onOpenChatter',
        open_record: '_onOpenRecord',
        save_multi: '_onSaveMulti',
        select_record: '_onSelectRecord',
        set_focus_tag_input: '_onSetFocusTagInput',
        set_file: '_onSetFile',
        share_ids: '_onShareIds',
        trigger_rule: '_onTriggerRule',
    }),

    /**
     * @override
     */
    init(parent, model, renderer, params) {
        /**
         * The id of the record used as "anchor" for the multi selection.
         * Used to select records with ctrl/shift keys.
         */
        this._anchorId = null;
        this._chatterContainerComponent = undefined;
        this._documentsInspector = null;
        /**
         * This attribute sets the focus on the tag input of the inspector on mount.
         * Used to indicate that the tag input of the inspector has to regain focus at the next re-render
         */
        this._isInspectorTagInputFocusOnMount = false;
        /**
         * _selectedRecordIds is the list of the ids of all records that are currently selected and on which
         * most UI actions will take effect (drag & drop, Inspector).
         */
        this._selectedRecordIds = params.selectedRecordIds || [];
        fileUploadMixin.init.call(this);
        /**
         * _hasShareReadAccessRights defines whether or not the user has read access rights on the documents.share model.
         */
        this._hasShareReadAccessRights = undefined;
    },

    async willStart() {
        const parentPromise = this._super(...arguments);
        const readAccessRightsPromise = this._rpc({
            model: 'documents.share',
            method: 'check_access_rights',
            kwargs: {
                'operation': 'read',
                'raise_exception': false,
            },
        }).then((res) => {
            this._hasShareReadAccessRights = res;
        });
        return Promise.all([parentPromise, readAccessRightsPromise]);
    },

    /**
     * Used in the start() of the view controller,
     * the controller may be configured with pre-selected records, so this should be reflected visually.
     */
    start() {
        this._updateSelection();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Exporting this._selectedRecordIds to be able to keep selection when changing view.
     *
     * @override
     */
    exportState() {
        const state = this._super(...arguments) || {};
        state.selectedRecordIds = this._selectedRecordIds;
        return state;
    },
    /**
     * Called right after the reload of the view.
     */
    async reload() {
        this._updateSelection();
        await this._renderFileUploads();
        const folderIds = [
            ...new Set(Object.values(this._fileUploads).map(upload => upload.folderId))
        ];
        this._updateSearchPanel({ uploadingFolderIds: folderIds });
    },
    /**
     * @param {jQuery} [$node]
     */
    renderButtons($node) {
        this.$buttons = $(qweb.render('DocumentsViews.buttons'));
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _closeChatter() {
        this.$('.o_content').removeClass('o_chatter_open');
        this.$('.o_document_chatter_container').remove();
        if (this._chatterContainerComponent) {
            this._chatterContainerComponent.destroy();
            this._chatterContainerComponent = undefined;
        }
    },
    /**
     * Renders the inspector with a slight delay.
     * This is useful to let browser do some painting before, notably the record selection,
     * as the rendering of inspector may be quite slow (up to a few seconds).
     *
     * @private
     * @param {ev} event used for custom behaviour on override.
     */
    async _deferredRenderInspector(ev) {
        const state = this.model.get(this.handle);
        return new Promise((resolve) => {
            setTimeout(() => {
                this._renderDocumentsInspector(state);
                resolve();
            });
        });
    },
    /**
     * @override
     */
    _getFileUploadRenderOptions() {
        const currentFolderId = this.searchModel.get('selectedFolderId');
        return {
            predicate: fileUpload => {
                return !currentFolderId ||
                    fileUpload.recordId ||
                    currentFolderId === fileUpload.folderId;
            },
            targetCallback: fileUpload => {
                const $targetCard = this.$(`.o_documents_attachment[data-id="${fileUpload.recordId}"]`);
                $targetCard.find('.o_record_selector').addClass('o_hidden');
                return $targetCard;
            },
        };
    },
    /**
     * @override
     */
    _getFileUploadRoute() {
        return '/documents/upload_attachment';
    },
    /**
     * @private
     * @param {Object[]} documents
     * @return {Object[]} rules that are common to the given documents.
     */
    _getRules(documents) {
        const ruleIdsByRecord = documents.map(record => record.available_rule_ids.res_ids);
        const commonRuleIds = _.intersection.apply(_, ruleIdsByRecord);
        const record = documents[0];
        const rules = commonRuleIds.map(ruleId => {
            const rule = record.available_rule_ids.data.find(record => record.res_id === ruleId);
            return rule.data;
        });
        return rules.filter(rule => !rule.limited_to_single_record);
    },
    /**
     * @private
     * @returns {Object}
     */
    _makeChatterContainerProps() {
        return {
            // `documents.document` has `mail.activity.mixin`
            hasActivities: this.modelName === 'documents.document',
            hasFollowers: true,
            hasTopbarCloseButton: true,
            threadId: this._selectedRecordIds[0],
            threadModel: this.modelName,
        };
    },
    /**
     * Generates an drag icon near the cursor containing information on the dragged records.
     *
     * @private
     * @param {Object} param0
     * @param {Object} dataTransfer
     * @param {integer} lockedCount
     * @param {integer[]} draggedRecordIds
     */
    _makeDragIcon({ dataTransfer, lockedCount, draggedRecordIds }) {
        let dragIconContent;
         if (lockedCount > 0) {
            dragIconContent = _.str.sprintf(_t("%s Documents (%s locked)"), draggedRecordIds.length, lockedCount);
        } else {
            dragIconContent = _.str.sprintf(_t("%s Documents"), draggedRecordIds.length);
        }

        if (draggedRecordIds.length === 1) {
            const state = this.model.get(this.handle);
            const record = state.data.find(record => record.res_id === draggedRecordIds[0]);
            if (record) {
                dragIconContent = record.data.name ? record.data.display_name : _t("Unnamed");
            }
        }
        const $dragIcon = $(qweb.render('documents.dragIcon', {
            dragIconContent,
        })).appendTo($('body'));
        dataTransfer.setDragImage($dragIcon[0], -5, -5);

        // as the DOM render doesn't happen in the current call stack, the .remove() of the dragIcon has to be
        // moved back in the event queue so the setDragImage can use the dragIcon when it is in the DOM.
        setTimeout(() => $dragIcon.remove());
    },
    /**
     * @override
     */
    _makeFileUpload({ recordId }) {
        return Object.assign({
            folderId: this.searchModel.get('selectedFolderId'),
            tag_ids: this.searchModel.get('selectedTagIds'),
            recordId,
        },
        fileUploadMixin._makeFileUpload.apply(this, arguments));
    },
    /**
     * @override
     * @param {integer} param0.recordId
     */
    _makeFileUploadFormDataKeys({ recordId }) {
        const context = this.model.get(this.handle, { raw: true }).getContext();
        return {
            document_id: recordId,
            folder_id: this.searchModel.get('selectedFolderId'),
            tag_ids: this.searchModel.get('selectedTagIds'),
            owner_id: context && context.default_owner_id,
            partner_id: context && context.default_partner_id,
        };
    },
    /**
     * Used in the tests to mock the upload behaviour and to access the $uploadInput fragment.
     *
     * @private
     * @param {jQueryElement} $uploadInput
     */
    _promptFileInput($uploadInput) {
        $uploadInput.click();
    },
    /**
     * Opens the chatter of the given record.
     *
     * @private
     * @param {Object} record
     * @returns {Promise}
     */
    async _renderChatter() {
        if (this._selectedRecordIds.length !== 1) {
            return;
        }
        this._closeChatter();
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent = new ChatterContainerWrapperComponent(
            this,
            getMessagingComponent('ChatterContainer'),
            props
        );
        const $chatterContainer = $(qweb.render('documents.ChatterContainer'));
        this.$('.o_content').addClass('o_chatter_open');
        if (this.$('.o_documents_mobile_inspector').length) {
            this.$('.o_documents_mobile_inspector').append($chatterContainer);
        } else {
            this.$('.o_content').append($chatterContainer);
        }
        const target = $chatterContainer[0].querySelector(':scope .o_documents_chatter_placeholder');
        await this._chatterContainerComponent.mount(target);
    },
    /**
     * Renders and appends the documents inspector sidebar.
     *
     * @private
     */
    async _renderDocumentsInspector(state, shareAliases = []) {
        let localState;
        if (this._documentsInspector) {
            localState = this._documentsInspector.getLocalState();
            this._documentsInspector.destroy();
        }
        this._documentsInspector = new DocumentsInspector(this, {
            focusTagInput: this._isInspectorTagInputFocusOnMount,
            folderId: this.searchModel.get('selectedFolderId'),
            folders: this.searchModel.get('folders'),
            recordIds: this._selectedRecordIds,
            state,
            tags: this.searchModel.get('tags'),
            viewType: this.viewType,
            shareAliases: shareAliases,
        });
        this._isInspectorTagInputFocusOnMount = false;
        await this._documentsInspector.insertAfter(this.renderer.$el);
        if (localState) {
            this._documentsInspector.setLocalState(localState);
        }
    },
    /**
     * Open the share wizard with the given context, containing either the
     * 'attachment_ids' or the 'active_domain'.
     *
     * @private
     * @param {Object} vals (ORM create dict)
     * @returns {Promise}
     */
    async _shareDocuments(vals) {
        if (!vals.folder_id) {
            return;
        }
        const result = await this._rpc({
            model: 'documents.share',
            method: 'open_share_popup',
            args: [vals],
        });
        this.do_action(result, {
            fullscreen: config.device.isMobile,
        });
    },
    /**
     * Apply rule's actions for the specified attachments.
     *
     * @private
     * @param {string} ruleId
     * @param {string[]} recordIds
     * @param {Object} param2
     * @param {boolean} param2.preventReload
     * @return {Promise}
     */
    async _triggerRule(ruleId, recordIds, { preventReload } = {}) {
        const result = await this._rpc({
            model: 'documents.workflow.rule',
            method: 'apply_actions',
            args: [[ruleId], recordIds],
        });
        if (preventReload) {
            return;
        }
        if (_.isObject(result)) {
            if (result.hasOwnProperty('warning')) {
                let documents = Markup(result['warning']['documents'].map((d) => Markup`<li>${d}</li>`).join(''));
                this.displayNotification({
                    title: result['warning']['title'],
                    message: Markup`<ul>${documents}</ul>`,
                    type: 'danger',
                });
                this.reload();
            } else {
                await this.do_action(result, { on_close: () => this.reload() });
            }
        } else {
            await this.reload();
        }
    },
    /**
     * Override to render the documents selector and inspector sidebars and
     * update the record selection based on the available records and the controller state.
     *
     * @private
     * @param {Object} state
     * @param {Object} [param1={}]
     * @param {Object} [param1.controllerState={}]
     * @param {integer[]} [param1.controllerState.selectedRecordIds]
     */
    async _update(state, { controllerState: { selectedRecordIds, }={}, }={}) {
        if (selectedRecordIds) {
            this._selectedRecordIds = selectedRecordIds;
        }
        const recordIds = state.data.map(record => record.res_id);
        this._selectedRecordIds = _.intersection(this._selectedRecordIds, recordIds);
        await this._updateChatter();
        const shareAliases = await this._updateHelper(state.getDomain());
        await this._renderDocumentsInspector(state, shareAliases);
    },
    /**
     * Disables the control panel buttons if there is no selected folder.
     *
     * @private
     */
    updateButtons() {
        const selectedFolderId = this.searchModel.get('selectedFolderId');
        this.$buttons.find('.o_documents_kanban_upload').prop('disabled', !selectedFolderId);
        this.$buttons.find('.o_documents_kanban_url').prop('disabled', !selectedFolderId);
        this.$buttons.find('.o_documents_kanban_request').prop('disabled', !selectedFolderId);
        this.$buttons.find('.o_documents_kanban_share_domain').prop('disabled', !selectedFolderId);
    },
    /**
     * Update chatter part visually. Chatter only exists in single selection, and it is always open in that case.
     *
     * @private
     * @returns {Promise}
     */
    async _updateChatter() {
        if (!this._chatterContainerComponent) {
            return;
        }
        if (this._selectedRecordIds.length === 1) {
            const props = this._makeChatterContainerProps();
            this._chatterContainerComponent.update(props);
            const chatterContainer = this.el.querySelector(':scope .o_document_chatter_container');
            const target = chatterContainer.querySelector(':scope .o_documents_chatter_placeholder');
            await this._chatterContainerComponent.mount(target);
        } else {
            this._closeChatter();
        }
    },
    /**
     * Update helper text of list/kanban's renderer if the current folder has a related
     * document.shares record.
     * @private
     * @param {Object} searchDomain
     */
    async _updateHelper(searchDomain) {
        var self = this;
        const rpcDomain = searchDomain.filter(elem => Array.isArray(elem) && elem.includes('folder_id'))
        // Avoid updating the Helper when the "All folder" is selected in the search panel or
        // if the user does not have the rights to read documents shares.
        if (rpcDomain.length && this._hasShareReadAccessRights) {
            return await this._rpc({
                model: 'documents.share',
                method: 'search_read',
                kwargs: {
                    domain: rpcDomain,
                    fields: ['id', 'alias_id'],
                },
            }).then((shares) => {
                if (shares.length) {
                    const shareAliases = _.map(_.pluck(shares, 'alias_id'), (vals) => _.object(['alias_id', 'aliasName'], vals));
                    this.renderer.updateHelper(shareAliases);
                    return shareAliases;
                }
            });
        }
    },

    /**
     * Calls the renderer updateSelection to display which records are selected.
     *
     * @private
     */
    _updateSelection() {
        this.renderer.updateSelection(this._selectedRecordIds);
    },
    /**
     * Generates a handler for uploading one or multiple file(s)
     *
     * @private
     * @param {boolean} multiple allow to upload a single file or multiple files
     * @returns {Function}
     */
    _uploadFilesHandler(multiple) {
        return (ev) => {
            const recordId = ev.data ? ev.data.id : undefined;
            const $uploadInput = this.hiddenUploadInputFile
                ? this.hiddenUploadInputFile.off('change')
                : (this.hiddenUploadInputFile = $('<input>', { type: 'file', name: 'files[]', class: 'o_hidden' }).appendTo(this.$el));
            $uploadInput.attr('multiple', multiple ? true : null);
            const cleanup = $.prototype.remove.bind($uploadInput);
            $uploadInput.on('change', async changeEv => {
                await this._uploadFiles(changeEv.target.files, { recordId }).finally(cleanup);
            });
            this._promptFileInput($uploadInput);
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * FIXME: build a more complete archive system:
     * currently, it checks the archive state of the first record of the selection and supposes that
     * all the selected records have the same active state (since archived attachments should always be viewed
     * separately). The current system could technically cause unexpected results if the selection contains
     * records of both states.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object[]} ev.data.records objects with keys 'id' (the localId)
     *   and 'res_id'
     */
    async _onArchiveRecords(ev) {
        ev.stopPropagation();
        const recordIds = ev.data.records.map(record => record.id);
        await this.model.toggleActive(recordIds, this.handle);
        await this.update({}, { reload: false }); // the reload is done by toggleActive

    },
    /**
     * @private
     */
    async _onBeforeUpload() {
        fileUploadMixin._onBeforeUpload.apply(this, arguments);
        const folderIds = [
            ...new Set(Object.values(this._fileUploads).map(upload => upload.folderId))
        ];
        this._updateSearchPanel({ uploadingFolderIds: folderIds });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDocumentsRequest(ev) {
        ev.preventDefault();
        const context = this.model.get(this.handle, {raw: true}).getContext();
        this.do_action('documents.action_request_form', {
            additional_context: {
                default_partner_id: context.default_partner_id || false,
                default_folder_id: this.searchModel.get('selectedFolderId'),
                default_tag_ids: [[6, 0, this.searchModel.get('selectedTagIds')]],
            },
            fullscreen: config.device.isMobile,
            on_close: () => this.reload(),
        });
    },
    /**
     * Share the current domain.
     *
     * @private
     */
    _onClickDocumentsShareDomain() {
        const state = this.model.get(this.handle, { raw: true });
        this._shareDocuments({
            domain: state.domain,
            folder_id: this.searchModel.get('selectedFolderId'),
            tag_ids: [[6, 0, this.searchModel.get('selectedTagIds')]],
            type: this._selectedRecordIds.length ? 'ids' : 'domain',
            document_ids: this._selectedRecordIds.length ? [[6, 0, this._selectedRecordIds]] : false,
        });
    },
    /**
     * @private
     */
    _onClickDocumentsUpload(ev) {
        this._uploadFilesHandler(true)(ev);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDocumentsUploadFromUrl(ev) {
        ev.preventDefault();
        const context = this.model.get(this.handle, {raw: true}).getContext();
        this.do_action('documents.action_url_form', {
            additional_context: {
                default_partner_id: context.default_partner_id || false,
                default_folder_id: this.searchModel.get('selectedFolderId'),
                default_tag_ids: [[6, 0, this.searchModel.get('selectedTagIds')]],
            },
            fullscreen: config.device.isMobile,
            on_close: async () => await this.reload()
        });
    },
    /**
     * Remove the link between the document (documentId) and its record.
     * @param {OdooEvent} ev
     * @param {Object} ev.data.documentId link to remove for the document with this id
     */
    _onDeleteModel: function (ev) {
        Dialog.confirm(this, _t("Are you confirm deletion ?"), {
            confirm_callback: () => {
                var documentIds = [ev.data.documentId];
                this._rpc({
                    model: 'documents.workflow.rule',
                    method: 'unlink_record',
                    args: [documentIds]
                }).then(() => {
                    this.reload();
                });
            },
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object[]} ev.data.records objects with keys 'id' (the localId)
     *   and 'res_id'
     */
    async _onDeleteRecords(ev) {
        ev.stopPropagation();
        const recordIds = ev.data.records.map(record => record.id);
        await this.model.deleteRecords(recordIds, this.modelName);
        const resIds = ev.data.records.map(record => record.res_id);
        this._selectedRecordIds = _.difference(this._selectedRecordIds, resIds);
        await this.reload();
    },
    /**
     * @private
     */
    _onDocumentsCloseChatter() {
        this._closeChatter();
    },
    /**
     * @private
     * @param {DragEvent} ev
     */
    async _onDropDocumentsView(ev) {
        if (!ev.originalEvent.dataTransfer.types.includes('Files')) {
            return;
        }
        ev.preventDefault();
        this.renderer.$el.removeClass('o_documents_drop_over');
        this.$('.o_documents_upload_text').remove();
        await this._uploadFiles(ev.originalEvent.dataTransfer.files);
    },
    /**
     * Update the controller when the DocumentViewer has modified an attachment
     *
     * @private
     * @param {OdooEvent} ev
     */
    async _onDocumentViewerAttachmentChanged(ev) {
        ev.stopPropagation();
        if (ev.data.documentIds) {
            // If document ids are given, the view is reloaded with the new
            // documents being pre-selected.
            this._selectedRecordIds = ev.data.documentIds;
            await this.reload();
        } else {
            await this.update({});
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer[]} ev.data.resIds
     */
    _onDownload(ev) {
        ev.stopPropagation();
        const resIds = ev.data.resIds;
        if (resIds.length === 1) {
            window.location = `/documents/content/${resIds[0]}`;
        } else {
            session.get_file({
                url: '/document/zip',
                data: {
                    file_ids: resIds,
                    zip_name: `documents-${moment().format('YYYY-MM-DD')}.zip`
                },
            });
        }
    },
    /**
     * @private
     * @param {DragEvent} ev
     */
    _onDragoverDocumentsView(ev) {
        if (
            !this.searchModel.get('selectedFolderId') ||
            !ev.originalEvent.dataTransfer.types.includes('Files')
        ) {
            return;
        }
        ev.preventDefault();
        this.renderer.$el.addClass('o_documents_drop_over');
        if (this.$('.o_documents_upload_text').length === 0) {
            this.$('.o_content').append($(qweb.render('documents.uploadText')));
        }
    },
    /**
     * @private
     * @param {DragEvent} ev
     */
    _onDragleaveDocumentsView(ev) {
        if (
            $(ev.target).closest(this.renderer.$el) &&
            ev.target !== this.renderer.el
        ) {
            return;
        }
        this.renderer.$el.removeClass('o_documents_drop_over');
        this.$('.o_documents_upload_text').remove();
    },
    /**
     * Adds the selected documents to the data of the drag event and
     * creates a custom drag icon to represent the dragged documents.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragstartDocumentDraggable(ev) {
        let isTargetSelected;
        let resId;
        switch (this.viewType) {
            case 'kanban':
                isTargetSelected = ev.currentTarget.classList.contains('o_record_selected');
                resId = $(ev.currentTarget).data('id')
                break;
            case 'list':
                isTargetSelected = $(ev.currentTarget).find('.o_list_record_selector input').prop('checked');
                resId = $(ev.currentTarget).closest('.o_data_row').data('res-id');
                break;
        }

        if (!isTargetSelected) {
            this.trigger_up('select_record', {
                isKeepSelection: false,
                originalEvent: ev,
                resId,
            });
        }
        const unlockedRecordIds = this.model.get(this.handle, {raw: true}).data
            .filter(record => !record.data.lock_uid || record.data.lock_uid === session.uid)
            .map(record => record.res_id);
        const draggedRecordIds = _.intersection(this._selectedRecordIds, unlockedRecordIds);
        if (draggedRecordIds.length === 0) {
            ev.preventDefault();
            return;
        }
        const lockedCount = this._selectedRecordIds.length - draggedRecordIds.length;
        ev.originalEvent.dataTransfer.setData('o_documents_data', JSON.stringify({
            recordIds: draggedRecordIds,
            lockedCount,
        }));

        this._makeDragIcon({
            dataTransfer: ev.originalEvent.dataTransfer,
            lockedCount,
            draggedRecordIds,
        });
    },
    /**
     * Opens a wizard to edit the record linked to the document.
     * @param {OdooEvent} ev
     * @param {Object} ev.data.document document to edit
     */
    _onEditModel: function (ev) {
        ev.stopPropagation();
        const document = ev.data.document;
        let defaultResourceRef = `${document['res_model']},${document['res_id']}`;
        if (defaultResourceRef.includes('undefined')) {
            defaultResourceRef = false;
        }
        this._rpc({
            model: 'ir.model',
            method: 'search_read',
            domain: [
                ['model', '=', document['res_model']],
            ],
            fields: ['id'],
            limit: 1,
        }).then((models) => {
            let action = {
                    name: _t('Edit the linked Record'),
                    type: 'ir.actions.act_window',
                    res_model: 'documents.link_to_record_wizard',
                    views: [[false, 'form']],
                    target: 'new',
                    context:{
                        'default_document_ids': [document['id']],
                        'default_resource_ref': defaultResourceRef,
                        'default_is_readonly_model': true,
                        'default_model_id': models[0].id,
                        }
                    };
            this.do_action(action, {
                on_close: () => {
                    this.reload();
                }
            });
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {callback} ev.data.callback
     */
    _onGetSearchPanelTags(ev) {
         ev.data.callback(this.searchModel.get('tags'));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.attachmentId
     */
    async _onHistoryItemDelete(ev) {
        ev.stopPropagation();
        await this._rpc({
            model: 'ir.attachment',
            method: 'unlink',
            args: [[ev.data.attachmentId]],
        });
        await this.reload();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.attachmentId
     */
    _onHistoryItemDownload(ev) {
        ev.stopPropagation();
        window.location = `/web/content/${ev.data.attachmentId}?download=true`;
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.attachmentId
     * @param {integer} ev.data.resId
     */
    async _onHistoryItemRestore(ev) {
        ev.stopPropagation();
        await this._rpc({
            model: 'documents.document',
            method: 'write',
            args: [[ev.data.resId], {attachment_id: ev.data.attachmentId}],
        });
        await this.reload();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.recordId
     * @param {boolean} ev.data.openPdfManager
     * @param {Array<Object>} ev.data.recordList
     */
    async _onKanbanImageClicked(ev) {
        ev.stopPropagation();
        const documents = ev.data.recordList;
        const recordId = ev.data.recordId;
        const rules = this._getRules(documents);
        const documentViewer = new DocumentViewer(this, documents, recordId, {
            openPdfManager: ev.data.openPdfManager,
            rules,
        });
        await documentViewer.appendTo(this.$('.o_documents_view'));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.resId
     */
    async _onLockAttachment(ev) {
        ev.stopPropagation();
        try {
            await this._rpc({
                model: 'documents.document',
                method: 'toggle_lock',
                args: [ev.data.resId],
            });
        } catch (err) {
            // silently ignore RPC errors
        }
        await this.reload();
    },
    /**
     * Open the chatter of the given document.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.id localId of the document
     */
    async _onOpenChatter(ev) {
        ev.stopPropagation();
        await this._renderChatter();
    },
    /**
     * Open a record in form view given a model and an id.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer} [ev.data.resId] opens the form view in create mode if
     *   not given
     * @param {string} ev.data.resModel
     */
    async _onOpenRecord(ev) {
        ev.stopPropagation();
        let viewId = false;
        try {
            viewId = await this._rpc({
                model: ev.data.resModel,
                method: 'get_formview_id',
                args: [ev.data.resId],
            });
        } catch (err) {
            // ignores error
        }
        this.do_action({
            res_id: ev.data.resId,
            res_model: ev.data.resModel,
            type: 'ir.actions.act_window',
            views: [[viewId, 'form']],
        });
    },
    /**
     * Save the changes done in the DocumentsInspector and re-render the view.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {function} [ev.data.callback]
     * @param {Object} ev.data.changes
     * @param {string[]} ev.data.dataPointsIds
     */
    async _onSaveMulti(ev) {
        ev.stopPropagation();
        try {
            await this.model.saveMulti(ev.data.dataPointIds, ev.data.changes, this.handle);
            await this.reload({});
        } finally {
            ev.data.callback && ev.data.callback();
        }
    },
    /**
     * React to records selection changes to update the DocumentInspector with
     * the current selected records.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {boolean} ev.data.isKeepSelection if true, conserves the current selection
     * equivalent to using the control key.
     * @param {MouseEvent} ev.data.originalEvent the event catched by the child
     *   element triggering up the OdooEvent
     * @param {string} ev.data.resId the resId of the record updating its status
     */
    async _onSelectRecord(ev) {
        const state = this.model.get(this.handle);
        const recordIds = state.data.map(record => record.res_id);

        const { newSelection, anchor } = computeMultiSelection(recordIds, ev.data.resId, {
            anchor: this._anchorId,
            isKeepSelection: ev.data.isKeepSelection || ev.data.originalEvent.ctrlKey || ev.data.originalEvent.metaKey,
            isRangeSelection: ev.data.originalEvent.shiftKey && this._anchorId,
            selected: this._selectedRecordIds,
         });
        this._selectedRecordIds = [...new Set(newSelection)];
        this._anchorId = anchor;
        await this._updateChatter();
        this._deferredRenderInspector(ev);
        this._updateSelection();
    },
    /**
     * Sets the focus on the tag input for the next render of document inspector.
     *
     * @private
     */
    _onSetFocusTagInput() {
        this._isInspectorTagInputFocusOnMount = true;
    },
    /**
     * Set/Replace the file of the document by prompting an input file.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.id
     */
    _onSetFile(ev) {
        this._uploadFilesHandler(false)(ev);
    },
    /**
     * Share the given records.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer[]} ev.data.resIds
     */
    _onShareIds(ev) {
        ev.stopPropagation();
        this._shareDocuments({
            document_ids: [[6, 0, ev.data.resIds]],
            folder_id: this.searchModel.get('selectedFolderId'),
            type: 'ids',
        });
    },
    /**
     * Apply rule's actions for the given records in a mutex, and reload
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     */
    async _onTriggerRule(ev) {
        ev.stopPropagation();
        if (ev.data.recordIds) {
            this._selectedRecordIds = ev.data.recordIds;
        }
        const recordIds = ev.data.recordIds
            ? ev.data.recordIds
            : ev.data.records.map(record => record.res_id);
        await this._triggerRule(ev.data.ruleId, recordIds, {
            preventReload: ev.data.preventReload
        });
    },
    /**
     * @override
     * @param {Object} param0
     * @param {XMLHttpRequest} param0.xhr
     */
    _onUploadLoad({ xhr }) {
        const result = xhr.status === 200
            ? JSON.parse(xhr.response)
            : {
                error: _.str.sprintf(_t("status code: %s, message: %s"), xhr.status, xhr.response)
            };
        if (result.error) {
            this.displayNotification({ title: _t("Error"), message: result.error, sticky: true });
        } else if (result.ids && result.ids.length > 0) {
            this._selectedRecordIds = result.ids;
        }
        fileUploadMixin._onUploadLoad.apply(this, arguments);
    },
});

return DocumentsControllerMixin;

});
