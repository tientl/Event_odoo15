odoo.define('documents.component.PdfManager', function (require) {
'use strict';

const PdfGroupName = require('documents.component.PdfGroupName');
const PdfPage = require('documents.component.PdfPage');
const { computeMultiSelection } = require('documents.utils');
const { isEventHandled, markEventHandled } = require('@mail/utils/utils');

const ajax = require('web.ajax');
const { csrf_token, _t } = require('web.core');

const { useState } = owl.hooks;

class PdfManager extends owl.Component {

    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.state = useState({
            // Disables upload button if currently uploading.
            uploadingLock: false,
            /*
             * Will be sent to the backend.
             * object groupData[groupId] = { groupId, name, pageIds }
             */
            groupData: {},
            // Ordered list of groups (should be set)
            groupIds: [],
            /*
             * Will be sent to the backend.
             *  object pages[pageId] = { pageId, groupId, isSelected, fileId, localPageNumber }
             */
            pages: {},
            // The page that is open as large preview.
            viewedPage: undefined,
            // whether to archive the original documents.
            archive: true,
            // the anchor of the page selection, used to determine the record from which record selections should occur
            anchorId: undefined,
            // shift keys held down.
            lShiftKeyDown: false,
            rShiftKeyDown: false,
        });
        /*
         * This object will be processed and sent to the backend.
         * object _newFiles[fileId] = { type, file, documentId, pageIds, activePageIds }
         */
        this._newFiles = {};
        // object _pageCanvas[pageId] = pageObject from PDFJS
        this._pageCanvas = {};
        this._onGlobalKeydown = this._onGlobalKeydown.bind(this);
        this._onGlobalCaptureKeyup = this._onGlobalCaptureKeyup.bind(this);
    }

    async willStart() {
        await this._loadAssets();
    }

    mounted() {
        document.addEventListener('keydown', this._onGlobalKeydown);
        document.addEventListener('keyup', this._onGlobalCaptureKeyup, true);
        for (const pdf_document of this.props.documents) {
            this._addFile(pdf_document.name, {
                url: `/documents/content/${pdf_document.id}`,
                documentId: pdf_document.id,
            });
        }
    }

    willUnmount() {
        document.removeEventListener('keydown', this._onGlobalKeydown);
        document.removeEventListener('keyup', this._onGlobalCaptureKeyup);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {number[]}
     */
    get ignoredPageIds() {
        return Object.keys(this.state.pages).filter(
            key => !this.state.pages[key].isSelected && this.state.pages[key].groupId
        );
    }

    /**
     * @return {number[]}
     */
    get activePageIds() {
        return Object.keys(this.state.pages).filter(
            key => this.state.pages[key].isSelected && this.state.pages[key].groupId
        );
    }

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @public
     * @param {String} name
     * @param {Object} param1
     * @param {number} [param1.documentId] the id of the `documents.document` record.
     * @param {Object} [param1.file]
     * @param {String} [param1.url]
     */
    async _addFile(name, { documentId, file, url }) {
        if (!url) {
            if (!file && !documentId) {
                return;
            }
            url = URL.createObjectURL(file);
        }
        this.state.uploadingLock = true;
        const fileId = _.uniqueId('file');
        const pdf = await this._getPdf(url);

        if (file) {
            this._newFiles[fileId] = { type: 'file', file };
        } else if (documentId) {
            this._newFiles[fileId] = { type: 'document', documentId };
        }
        name = name || _t("New File");
        const extIndex = name.indexOf('.pdf');
        if (extIndex >= 0) {
            name = name.substring(0, extIndex);
        }
        const pageCount = pdf.numPages;
        const { pageIds, newPages } = this._createPages({ fileId, name, pageCount });
        await this._loadCanvases({ newPages, pageCount, pdf });

        this._newFiles[fileId].pageIds = this._newFiles[fileId].activePageIds = pageIds;
        this.state.uploadingLock = false;
    }

    /**
     * Adds a page to a group (also removes the page from its former group).
     *
     * @private
     * @param {String} pageId
     * @param {String} groupId
     * @param {Object} param2
     * @param {String} [param2.index]
     */
    _addPage(pageId, groupId, { index } = {}) {
        if (!this.state.groupData[groupId]) {
            return;
        }
        this._removePage(pageId);
        if (index !== undefined) {
            this.state.groupData[groupId].pageIds.splice(index, 0, pageId);
        } else {
            this.state.groupData[groupId].pageIds.push(pageId);
        }
        this.state.pages[pageId].groupId = groupId;
    }
    /**
     * Ignored pages are not committed but are instead kept in the
     * PDF Manager. If no ignored page remain, the PDF Manager closes and the
     * view is reloaded.
     *
     * @private
     * @param {number} [ruleId]
     */
    async _applyChanges(ruleId) {
        const processedPageIds = this.activePageIds;
        if (processedPageIds.length === 0) {
            this.trigger('pdf-manager-error', { message: _t("No document has been selected") });
            return;
        }
        const pageIds = this.ignoredPageIds;

        for (const pageId of pageIds) {
            this._removePage(pageId);
        }
        const exit = !pageIds.length;


        try {
            const result = await this._sendChanges({ exit, ruleId });
            const documentIds = JSON.parse(result);
            this.trigger('process-documents', { documentIds, ruleId, exit });
            if (!exit) {
                for (const pageId of processedPageIds) {
                this._removePage(pageId, { fromFile: true });
                }
                this._createGroup({ name: _t("Remaining Pages"), pageIds, isSelected: true });
            }
        } catch (error) {
            this.trigger('pdf-manager-error', { message: error.message || error });
            if (pageIds.length) {
                this._createGroup({ name: _t("Remaining Pages"), pageIds: pageIds, isSelected: true });
            }
        } finally {
            this.state.uploadingLock = false;
            this.state.anchorId = undefined;
        }
    }
    /**
     * @private
     * @param {Object} [param0]
     * @param {String} [param0.name]
     * @param {number[]} [param0.pageIds]
     * @param {number} [param0.index]
     * @param {boolean} [param0.isSelected] true if pages should be selected
     * @return {String} groupId (unique)
     */
    _createGroup({ name, pageIds, index, isSelected } = {}) {
        const groupId = _.uniqueId('group');
        pageIds = pageIds || [];
        this.state.groupData[groupId] = {
            groupId,
            name: name || _t("New Group"),
            pageIds,
        };
        for (const pageId of pageIds) {
            this.state.pages[pageId].groupId = groupId;
            if (isSelected !== undefined) {
                this.state.pages[pageId].isSelected = isSelected;
            }
        }
        if (index) {
            this.state.groupIds.splice(index, 0, groupId);
        } else {
            this.state.groupIds.push(groupId);
        }
        return groupId;
    }
    /**
     * @private
     * @param {Object} [param0]
     * @param {String} [param0.name]
     * @param {String} [param0.fileId]
     * @param {number} [param0.pageCount]
     * @return {Object} { pageIds, newPages }
     * @return {Array<String>} pageIds
     * @return {Object} newPages
     */
    _createPages({ fileId, name, pageCount }) {
        let groupId;
        let groupName = name;
        let groupLock = false;
        //returns:
        const pageIds = [];
        const newPages = {};
        // creating page and groups
        for (let pageNumber = 1; pageNumber <= pageCount; pageNumber++) {
            // creating multiple groups if single file
            if (!groupLock) {
                groupId = this._createGroup({ name: groupName });
                groupLock = this.props.documents.length > 1;
                groupName = `${name}-p${pageNumber + 1}`;
            }
            const pageId = _.uniqueId('page');
            this.state.pages[pageId] = {
                pageId,
                groupId,
                fileId,
                localPageNumber: pageNumber,
                isSelected: true,
            };
            newPages[pageNumber] = pageId;
            this._pageCanvas[pageId] = {};
            this.state.groupData[groupId].pageIds.push(pageId);
            pageIds.push(pageId);
        }
        return { pageIds, newPages };
    }
    /**
     * Used to use a mocked version of Xhr in the tests.
     *
     * @private
     * @return {XMLHttpRequest}
     */
    _createXhr() {
        return new window.XMLHttpRequest();
    }
    /**
     * To be overwritten in tests (along with _renderCanvas()).
     *
     * @private
     * @param {String} url
     * @return {PdfJsObject} pdf
     *    should be constructed as follow:
     *        pdf.getPage(pageNumber) {function} return {pageObject}
     *        pdf.numPages {number}
     */
    async _getPdf(url) {
        return window.pdfjsLib.getDocument(url).promise;
    }
    /**
     * To be overwritten in tests.
     *
     * @private
     */
    async _loadAssets() {
        let asset;
        try {
            asset = await ajax.loadAsset('documents.pdf_js_assets');
        } catch (error) {
            asset = await ajax.loadAsset('web.pdf_js_lib');
        } finally {
            await ajax.loadLibs(asset);
        }
    }
    /**
     * @private
     * @param {Object} [param0]
     * @param {Object} [param0.newPages]
     * @param {number} [param0.pageCount]
     * @param {PdfjsObject} [param0.pdf]
     */
    async _loadCanvases({ newPages, pageCount, pdf }) {
        for (let pageNumber = 1; pageNumber <= pageCount; pageNumber++) {
            const pageId = newPages[pageNumber];
            const page = await pdf.getPage(pageNumber);
            const canvas = await this._renderCanvas(page, {
                width: 160,
                height: 230,
            });
            this._pageCanvas[pageId] = { page, canvas };
            const pdfPage = this.__owl__.refs[`PdfPage_${pageId}`];
            if (pdfPage) {
                pdfPage.renderPage(canvas);
            }
        }
    }
    /**
     * @private
     * @param {String} groupId
     */
    _removeGroup(groupId) {
        if (this.state.groupData[groupId].pageIds.length > 0) {
            return;
        }
        for (const pageId in this.state.pages) {
            const page = this.state.pages[pageId];
            if (page.groupId === groupId) {
                page.groupId = false;
            }
        }
        this.state.groupIds = this.state.groupIds.filter(
            listedGroupId => listedGroupId !== groupId
        );
        delete this.state.groupData[groupId];
    }
    /**
     * @private
     * @param {String} pageId
     * @param {Object} [param1]
     * @param {boolean} [param1.fromFile] whether to remove page from the file, in which case
     * the file will be removed if none of its pages are used.
     */
    _removePage(pageId, { fromFile } = {}) {
        const page = this.state.pages[pageId];
        if (!page) {
            return;
        }

        // set not supported?
        const pageIds = this.state.groupData[page.groupId].pageIds;
        this.state.groupData[page.groupId].pageIds = pageIds.filter(
            number => number !== pageId
        );
        // if pageIds.length === 0, delete group or leave empty group?
        if (page.groupId) {
            this._removeGroup(page.groupId);
        }
        page.groupId = false;
        if (fromFile) {
            const activePageIds = this._newFiles[page.fileId].activePageIds;
            this._newFiles[page.fileId].activePageIds = activePageIds.filter(
                number => number !== pageId
            );
            if (this._newFiles[page.fileId].activePageIds.length === 0) {
                this._removeFile(page.fileId);
            }
            page.fileId = false;
        }
    }
    /**
     * @private
     * @param {String} fileId
     */
    _removeFile(fileId) {
        for (const pageId of this._newFiles[fileId].pageIds) {
            delete this._pageCanvas[pageId];
            delete this.state.pages[pageId];
        }
        delete this._newFiles[fileId];
    }
    /**
     * @private
     * @param {Object} page
     * @param {Object} param1
     * @param {number} param1.width
     * @param {number} param1.height
     * @return {DomElement} canvas
     */
    async _renderCanvas(page, { width, height }) {
        const viewPort = page.getViewport({ scale: 1 });
        const canvas = document.createElement("canvas");
        canvas.className = "o_documents_pdf_canvas";
        canvas.width = width;
        canvas.height = height;
        const scale = Math.min(canvas.width / viewPort.width, canvas.height / viewPort.height);
        await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport: page.getViewport({ scale }),
        }).promise;
        return canvas;
    }
    /**
     * Endpoint of the manager, sends the page structure to be split to the
     * server and closes the manager.
     *
     * @private
     * @param {Object} [param0]
     * @param {boolean} [param0.exit] whether to exit the PdfManager.
     * @param {number} [param0.ruleId] the rule to apply to the new records.
     * @private
     */
    async _sendChanges({ exit, ruleId } = {}) {
        this.state.uploadingLock = true;
        const data = new FormData();

        const fileIds = [];
        const files = [];
        for (const key in this._newFiles) {
            if (this._newFiles[key].type === 'file') {
                files.push(this._newFiles[key].file);
                fileIds.push(key);
            }
        }
        const fileGroups = JSON.parse(JSON.stringify(this.state.groupData));
        const newFiles = Object.values(fileGroups);
        newFiles.forEach((newFile) => {
            newFile.new_pages = [];
            for (const pageId of newFile.pageIds) {
                const fileId = this.state.pages[pageId].fileId;
                const file = this._newFiles[fileId];
                const old_file_type = file.type;
                const old_file_index = old_file_type === 'file'
                    ? fileIds.indexOf(fileId)
                    : file.documentId;
                newFile.new_pages.push({
                    old_file_type,
                    old_file_index,
                    old_page_number: this.state.pages[pageId].localPageNumber,
                });
            }
            delete newFile.pageIds;
        });

        return new Promise((resolve, reject) => {
            const xhr = this._createXhr();
            xhr.open('POST', '/documents/pdf_split');
            data.append('csrf_token', csrf_token);
            for (const file of files) {
                data.append('ufile', file);
            }
            data.append('new_files', JSON.stringify(newFiles));
            data.append('archive', this.state.archive);

            const document = this.props.documents[0];
            data.append('vals', JSON.stringify({
                folder_id: document.folder_id.res_id,
                tag_ids: document.tag_ids.res_ids,
                owner_id: document.owner_id.res_id,
                partner_id: document.partner_id.res_id,
            }));

            xhr.send(data);
            xhr.onload = () => {
                if (xhr.status === 200) {
                    resolve(xhr.response);
                } else {
                    reject(xhr.response);
                }
            };
            xhr.onerror = () => {
                reject();
            };
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickArchive(ev) {
        ev.stopPropagation;
        ev.target.blur();
        this.state.archive = !this.state.archive;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDropdown(ev) {
        markEventHandled(ev, 'PdfManager.toggleDropdown');
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGlobalAdd(ev) {
        ev.stopPropagation();
        const $uploadInput = $('<input/>', {
            type: 'file',
            name: 'files[]',
            multiple: 'multiple',
            accept: 'application/pdf',
        });
        $uploadInput.on('change', async e => {
            const files = $uploadInput[0].files;
            $uploadInput.remove();
            for (const file of files) {
                await this._addFile(file.name, { file });
            }
        });
        $uploadInput.click();
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGlobalClose(ev) {
        ev.stopPropagation();
        this.trigger('process-documents', { exit: true });
    }
    /**
     * @private
     * @param {customEvent} ev
     * @param {String} ev.detail
     */
    _onSelectClicked(ev) {
        const { pageId, isCheckbox, isRangeSelection, isKeepSelection } = ev.detail;
        const selectedPageIds = this.activePageIds;
        const anchorId = this.state.anchorId || selectedPageIds[0];
        const recordIds = [];

        for (const groupId of this.state.groupIds) {
            recordIds.push(...this.state.groupData[groupId].pageIds);
        }
        const { newSelection, anchor } = computeMultiSelection(recordIds, pageId, {
            anchor: anchorId,
            isCheckbox,
            isKeepSelection,
            isRangeSelection: isRangeSelection && anchorId,
            selected: selectedPageIds,
        });
        const selectionSet = new Set(newSelection);
        this.state.anchorId = anchor;
        for (const pageId in this.state.pages) {
            this.state.pages[pageId].isSelected = selectionSet.has(pageId);
        }
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickManager(ev) {
        if (isEventHandled(ev, 'PdfManager.toggleDropdown')) {
            return;
        }
        ev.stopPropagation();
        this.previewCanvas = undefined;
        this.state.viewedPage = undefined;
    }
    /**
     * @private
     * @param {customEvent} ev
     * @param {String} ev.detail
     */
    async _onClickPage(ev) {
        ev.stopPropagation();
        const pageId = ev.detail;
        const page = this._pageCanvas[pageId].page;
        if (!page) {
            return;
        }
        this.previewCanvas = await this._renderCanvas(page, {
            width: 1300,
            height: 1800,
        });
        this.state.viewedPage = pageId;
    }
    /**
     * @private
     * @param {String} pageId
     * @param {String} groupId
     * @param {MouseEvent} ev
     */
    _onClickPageSeparator(pageId, groupId, ev) {
        ev.stopPropagation();
        const page = this.state.pages[pageId];
        const groupPageIds = this.state.groupData[groupId].pageIds;
        const pageIndex = groupPageIds.indexOf(pageId);
        const groupIndex = this.state.groupIds.indexOf(groupId);
        const isLastPage = pageIndex === groupPageIds.length - 1;

        if (isLastPage) {
            // merging the following group into the current one.
            const targetGroupId = this.state.groupIds[groupIndex + 1];
            if (targetGroupId) {
                const pageIds = this.state.groupData[targetGroupId].pageIds;
                for (const pageId of pageIds) {
                    this._addPage(pageId, page.groupId);
                }
            }
        } else {
            // making a new group with all the following pages.
            const newGroupPages = groupPageIds.slice(pageIndex + 1);
            const name = this.state.groupData[groupId].name;
            const newGroupId = this._createGroup({
                name,
                index: groupIndex + 1,
            });
            for (const page of newGroupPages) {
                this._addPage(page, newGroupId);
            }
        }
    }
    /**
     * @private
     * @param {customEvent} ev
     */
    _onClickPreview(ev) {
        ev.stopPropagation();
        this.previewCanvas = undefined;
        this.state.viewedPage = undefined;
    }
    /**
     * @private
     * @param {number} ruleId
     * @param {MouseEvent} ev
     */
    _onClickRule(ruleId, ev) {
        ev.stopPropagation();
        this._applyChanges(ruleId);
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSplit(ev) {
        ev.stopPropagation();
        this._applyChanges();
    }
    /**
     * @private
     * @param {customEvent} ev
     * @param {String} ev.detail.groupId
     * @param {String} ev.detail.name
     */
    _onEditName(ev) {
        ev.stopPropagation();
        const groupId = ev.detail.groupId;
        this.state.groupData[groupId].name = ev.detail.name || _t("unnamed");
    }
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onGlobalCaptureKeyup(ev) {
        if (ev.code === 'ShiftLeft') {
            this.state.lShiftKeyDown = false;
        } else if (ev.code === 'ShiftRight') {
            this.state.rShiftKeyDown = false;
        }
    }
    /**
     * @private
     * @param {KeyboardEvent} ev
     * @param {boolean} ev.altKey
     * @param {string} ev.key
     */
    _onGlobalKeydown(ev) {
        if ($(ev.target).is('input')) {
            return;
        }
        if (ev.key === 'A') {
            for (const pageId in this.state.pages) {
                this.state.pages[pageId].isSelected = true;
            }
        } else if (ev.code === 'ShiftLeft') {
            this.state.lShiftKeyDown = true;
        } else if (ev.code === 'ShiftRight') {
            this.state.rShiftKeyDown = true;
        }
    }
    /**
     * @private
     * @param {customEvent} ev
     */
    _onPageDragStart(ev) {
        ev.stopPropagation();
    }
    /**
     * @private
     * @param {customEvent} ev
     * @param {Object} ev.detail
     * @param {number} ev.detail.targetPageId
     * @param {number} ev.detail.pageId
     */
    _onPageDrop(ev) {
        ev.stopPropagation();
        const targetPageId = ev.detail.targetPageId;
        const pageId = ev.detail.pageId;
        const targetGroupId = this.state.pages[targetPageId].groupId;
        const index = this.state.groupData[targetGroupId].pageIds.indexOf(targetPageId);
        this._addPage(pageId, targetGroupId, { index });
    }
}

PdfManager.components = { PdfPage, PdfGroupName };

PdfManager.defaultProps = {
    rules: [],
};

PdfManager.props = {
    documents: Array,
    rules: Array,
};

PdfManager.template = 'documents.component.PdfManager';

return PdfManager;

});
