/** @odoo-module **/

import BarcodeParser from 'barcodes.BarcodeParser';
import { Mutex } from "@web/core/utils/concurrency";
import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';
import { _t } from 'web.core';
import { useService } from "@web/core/utils/hooks";
import { sprintf } from '@web/core/utils/strings';

export default class BarcodeModel extends owl.core.EventBus {
    constructor(params) {
        super();
        this.params = params;
        this.unfoldLineKey = false;
    }

    setData(data) {
        this.cache = new LazyBarcodeCache(data.data.records);
        const nomenclature = this.cache.getRecord('barcode.nomenclature', data.data.nomenclature_id);
        nomenclature.rules = [];
        for (const ruleId of nomenclature.rule_ids) {
            nomenclature.rules.push(this.cache.getRecord('barcode.rule', ruleId));
        }
        this.parser = new BarcodeParser({nomenclature: nomenclature});
        this.scannedLinesVirtualId = [];

        this.notification = useService('notification');
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        this.actionMutex = new Mutex();
        this.groups = data.groups;

        this.packageTypes = [];
        if (this.groups.group_tracking_lot) { // Get the package types by barcode.
            const packageTypes = this.cache.dbBarcodeCache['stock.package.type'] || {};
            for (const [barcode, ids] of Object.entries(packageTypes)) {
                this.packageTypes.push([barcode, ids[0]]);
            }
        }

        this._createState();
        this.linesToSave = [];
        this.selectedLineVirtualId = false;

        // UI stuff.
        this.name = this._getName();
        this.view = 'barcodeLines'; // Could be also 'printMenu' or 'editFormView'.
        // Manage pages
        this.pageIndex = 0;
        this._groupLinesByPage(this.currentState);
        this._defineLocationId();
        // Barcode's commands are returned by a method for override purpose.
        this.commands = this._getCommands();
    }

    // GETTER

    getQtyDone(line) {
        throw new Error('Not Implemented');
    }

    getQtyDemand(line) {
        throw new Error('Not Implemented');
    }

    getDisplayIncrementBtn(line) {
        return line.product_id.tracking !== 'serial' &&
            (!this.getQtyDemand(line) || this.getQtyDemand(line) > this.getQtyDone(line));
    }

    getDisplayDecrementBtn(line) {
        return false;
    }

    getActionRefresh(newId) {
        return {
            route: '/stock_barcode/get_barcode_data',
            params: {model: this.params.model, res_id: this.params.id || false},
        };
    }

    getIncrementQuantity(line) {
        return 1;
    }

    async apply() {
        throw new Error('Not Implemented');
    }

    get barcodeInfo() {
        let line = this.selectedLine;
        if (!line && this.lastScannedPackage) {
            const lines = this._moveEntirePackage() ? this.packageLines : this.pageLines;
            line = lines.find(l => l.package_id && l.package_id.id === this.lastScannedPackage);
        }

        // First page and the user didn't scan nothing yet -> We assume the operation was just started.
        if (this.pageIndex === 0 && !line) {
            this.messageType = this._getDefaultMessageType();
        } else if (line) { // Message depends of the selected line.
            const tracking = line.product_id.tracking;
            const trackingNumber = (line.lot_id && line.lot_id.name) || line.lot_name;
            if (this._lineIsNotComplete(line)) {
                if (tracking === 'lot') {
                    this.messageType = 'scan_lot';
                } else if (tracking === 'serial') {
                    this.messageType = 'scan_serial';
                } else {
                    this.messageType = 'scan_product';
                }
            } else { // Line's quantity is fulfilled.
                if (tracking !== 'none' && !trackingNumber) { // Line is waiting a tracking number.
                    if (tracking === 'lot') {
                        this.messageType = 'scan_lot';
                    } else {
                        this.messageType = 'scan_serial';
                    }
                } else {
                    this.messageType = this._getLocationMessage();
                }
            }
        } else { // Message depends of the operation.
            if (this.groups.group_stock_multi_locations) {
                this.messageType = this._getDefaultMessageType();
            } else {
                this.messageType = 'scan_product';
            }
        }

        const barcodeInformations = {
            class: this.messageType,
            warning: false,
        };
        switch (this.messageType) {
            case 'scan_product':
                barcodeInformations.message = _t("Scan a product"); break;
            case 'scan_src':
                barcodeInformations.message = _t("Scan the source location, or scan a product"); break;
            case 'scan_product_or_src':
                barcodeInformations.message = _t("Scan more products, or scan a new source location"); break;
            case 'scan_product_or_dest':
                barcodeInformations.message = _t("Scan more products, or scan the destination location"); break;
            case 'scan_lot':
                barcodeInformations.message = _t("Scan the lot number of the product"); break;
            case 'scan_serial':
                barcodeInformations.message = _t("Scan the serial number of the product"); break;
        }
        return barcodeInformations;
    }

    get canCreateNewLine() {
        return true;
    }

    get canCreateNewLot() {
        return true;
    }

    get canBeProcessed() {
        return true;
    }

    get canBeValidate() {
        return this.pages[this.pageIndex].lines.length;
    }

    get displayApplyButton() {
        return false;
    }

    get displayCancelButton() {
        return false;
    }

    get displayDestinationLocation() {
        return false;
    }

    get displayResultPackage() {
        return false;
    }

    get displaySourceLocation() {
        return this.groups.group_stock_multi_locations;
    }

    get displayValidateButton() {
        return false;
    }

    groupKey(line) {
        return `${line.product_id.id}`;
    }

    /**
     * Returns the page's lines but with tracked products grouped by product id.
     *
     * @returns
     */
     get groupedLines() {
        if (!this.groups.group_production_lot) {
            return this._sortLine(this.pageLines);
        }

        const lines = [...this.pageLines];
        const groupedLinesByKey = {};
        for (let index = lines.length - 1; index >= 0; index--) {
            const line = lines[index];
            if (line.product_id.tracking === 'none' || line.lines) {
                // Don't try to group this line if it's not tracked or already grouped.
                continue;
            }
            const key = this.groupKey(line);
            if (!groupedLinesByKey[key]) {
                groupedLinesByKey[key] = [];
            }
            groupedLinesByKey[key].push(...lines.splice(index, 1));
        }
        for (const [key, sublines] of Object.entries(groupedLinesByKey)) {
            if (sublines.length === 1) {
                lines.push(...sublines);
                continue;
            }
            const ids = [];
            const virtual_ids = [];
            let [qtyDemand, qtyDone] = [0, 0];
            for (const subline of sublines) {
                ids.push(subline.id);
                virtual_ids.push(subline.virtual_id);
                qtyDemand += this.getQtyDemand(subline);
                qtyDone += this.getQtyDone(subline);
            }
            const groupedLine = this._groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone);
            lines.push(groupedLine);
        }
        // Before to return the line, we sort them to have new lines always on
        // top and complete lines always on the bottom.
        return this._sortLine(lines);
    }

    get highlightNextButton() {
        return false;
    }

    get highlightValidateButton() {
        return false;
    }

    get informationParams() {
        return false;
    }

    get isDone() {
        return false;
    }

    get isCancelled() {
        return false;
    }

    /**
     * Say if the line quantity is not set. Only useful for the inventory adjustment.
     *
     * @param {Object} line
     * @returns {boolean}
     */
    IsNotSet(line) {
        return false;
    }

    get lastScannedLine() {
        if (this.scannedLinesVirtualId.length) {
            const virtualId = this.scannedLinesVirtualId[this.scannedLinesVirtualId.length - 1];
            return this.currentState.lines.find(l => l.virtual_id === virtualId);
        }
        return false;
    }

    lineIsFaulty(line) {
        throw new Error('Not Implemented');
    }

    get location() {
        return this.cache.getRecord('stock.location', this.currentLocationId);
    }

    /**
     * Retuns the current page if it exists, or a new empty page if it doesn't.
     *
     * @returns {Object}
     */
    get page() {
        const page = this.pages[this.pageIndex];
        if (!page) {
            const emptyPage = {
                index: this.pages.length,
                lines: [],
                sourceLocationId: this.currentLocationId,
            };
            this.pages.push(emptyPage);
            return emptyPage;
        }
        return page;
    }

    /**
     * Returns only the lines from the current page.
     *
     * @returns {Array<Object>}
     */
    get pageLines() {
        let lines = this.page.lines;
        // If we show entire package, we don't return lines with package (they
        // will be treated as "package lines").
        if (this.record.picking_type_entire_packs) {
            lines = lines.filter(line => !line.package_id);
        }
        return this._sortLine(lines);
    }

    get packageLines() {
        if (!this.record.picking_type_entire_packs) {
            return [];
        }
        const lines = this.page.lines;
        const linesWithPackage = lines.filter(line => line.package_id);
        // Groups lines by package.
        const groupedLines = {};
        for (const line of linesWithPackage) {
            const packageId = line.package_id.id;
            if (!groupedLines[packageId]) {
                groupedLines[packageId] = [];
            }
            groupedLines[packageId].push(line);
        }
        const packageLines = [];
        for (const key in groupedLines) {
            // Check if the package is reserved.
            const reservedPackage = groupedLines[key].every(line => line.product_uom_qty);
            groupedLines[key][0].reservedPackage = reservedPackage;
            packageLines.push(groupedLines[key][0]);
        }
        return this._sortLine(packageLines);
    }

    get previousScannedLines() {
        const lines = [];
        const alreadyDone = [];
        for (const virtualId of this.scannedLinesVirtualId) {
            if (alreadyDone.indexOf(virtualId) != -1) {
                continue;
            }
            alreadyDone.push(virtualId);
            lines.push(this.currentState.lines.find(l => l.virtual_id === virtualId));
        }
        if (this.lastScannedPackage) {
            lines.push(...this.currentState.lines.filter(l => l.package_id.id === this.lastScannedPackage));
        }
        return lines;
    }

    get printButtons() {
        throw new Error('Not Implemented');
    }

    get recordIds() {
        return [this.params.id];
    }

    get selectedLine() {
        const selectedLine = this.selectedLineVirtualId && this.currentState.lines.find(
            l => (l.dummy_id || l.virtual_id) === this.selectedLineVirtualId
        );
        // Returns the selected line only if it is in the current location.
        if (selectedLine && selectedLine.location_id === this.currentLocationId) {
            return selectedLine;
        }
        return false;
    }

    get useExistingLots() {
        return true;
    }

    get viewsWidgetData() { // shouldn't be override by the child model instead of set lineModel and viewReference
        return {
            model: this.lineModel,
            view: this.lineFormViewReference,
            additionalContext: this._getNewLineDefaultContext(),
        };
    }

    // ACTIONS

    async changeSourceLocation(id, applyChangeToPageLines = false) {
        this.scannedLinesVirtualId = [];
        this.currentLocationId = id;
        let pageFound = false;
        let emptyPage = false;
        const currentPage = this.pages[this.pageIndex];
        // We take either the current dest. location (if we move barcode line),
        // either the default dest. location (if we just want to create/change
        // page without move lines) to use while searching for an existing page.
        const refDestLocationId = applyChangeToPageLines ? this.currentDestLocationId : this._defaultDestLocationId();
        // If the scanned location is the current want, keep it.
        if (currentPage && this.currentLocationId === currentPage.sourceLocationId) {
            pageFound = currentPage;
        } else { // Otherwise, searches for a page with these src./dest. locations.
            for (let i = 0; i < this.pages.length; i++) {
                const page = this.pages[i];
                if (page.sourceLocationId === this.currentLocationId &&
                    page.destinationLocationId === refDestLocationId) {
                    this.pageIndex = i;
                    pageFound = page;
                    break;
                }
                if (page.lines.length === 0) {
                    emptyPage = page;
                }
            }
        }
        // Resets highlighting.
        this.selectedLineVirtualId = false;
        this.highlightDestinationLocation = false;
        await this.save();
        if (pageFound) {
            await this._changePage(pageFound.index);
        } else {
            if (emptyPage) {
                // If no matching page was found but an empty page was, reuses it.
                emptyPage.sourceLocationId = this.currentLocationId;
                emptyPage.destinationLocationId = this._defaultDestLocationId();
                pageFound = emptyPage;
            } else {
                // Otherwise, creates a new one.
                pageFound = {
                    index: this.pages.length,
                    lines: [],
                    sourceLocationId: this.currentLocationId,
                    destinationLocationId: this._defaultDestLocationId(),
                };
                this.pages.push(pageFound);
            }
            await this._changePage(pageFound.index);
        }
    }

    /**
     * Must be overridden to make something when the user selects a specific destination location.
     *
     * @param {int} id location's id
     */
    changeDestinationLocation(id) {
        throw new Error('Not Implemented');
    }

    displayBarcodeActions() {
        this.view = 'actionsView';
        this.trigger('update');
    }

    /**
     * @param {integer} [recordId] if provided, it will define the record's page as current page
     */
    displayBarcodeLines(recordId) {
        this.view = 'barcodeLines';
        if (recordId) { // If we pass a record id...
            if (this.pages.length > 1) { // ... looks to go to this record's page...
                for (let i = 0; i < this.pages.length; i++) {
                    const lineIds = this.pages[i].lines.map(line => line.id);
                    if (lineIds.includes(recordId)) {
                        this.pageIndex = i;
                        break;
                    }
                }
            }
            // ... and add this record on the scanned lines list.
            const line = this.currentState.lines.find(line => line.id === recordId);
            if (line) {
                this.selectLine(line);
                if (this.record.picking_type_code === 'incoming') {
                    // TODO ? SVS: highlight the destination if coming from the edit form view (see
                    // `test_reload_flow` tour) but I don't get the reason why ? I would like to remove that
                    // and only highlight the src/dest location only when they are actually changed by something.
                    this.highlightDestinationLocation = true;
                }
            }
        }
        this._defineLocationId();
        this.trigger('update');
    }

    displayInformation() {
        this.view = 'infoFormView';
        this.trigger('update');
    }

    displayPackagePage() {
        this.view = 'packagePage';
        this.trigger('update');
    }

    displayProductPage() {
        this.view = 'productPage';
        this.trigger('update');
    }

    async nextPage() {
        let pageIndex = this.pageIndex + 1;
        if (pageIndex >= this.pages.length) {
            pageIndex = 0;
        }
        this.highlightSourceLocation = false;
        await this._changePage(pageIndex);
        this.trigger('update');
    }

    async previousPage() {
        let pageIndex = this.pageIndex - 1;
        if (pageIndex < 0) {
            pageIndex = this.pages.length - 1;
        }
        this.highlightSourceLocation = false;
        await this._changePage(pageIndex);
        this.trigger('update');
    }

    async refreshCache(records) {
        this.cache.setCache(records);
        this._createState();
        // Creates the pages as they are bound to the state.
        await this._groupLinesByPage(this.currentState);
        // Changes the current page index if a page was removed.
        // if (this.pageIndex >= this.pages.length) {
        //     this.pageIndex = this.pages.length - 1;
        // }
    }

    async save() {
        const { route, params } = this._getSaveCommand();
        if (route) {
            const res = await this.rpc(route, params);
            this.linesToSave = [];
            await this.refreshCache(res.records);
        }
    }

    selectLine(line) {
        const virtualId = line.virtual_id;
        if (this.selectedLineVirtualId === virtualId) {
            return;
        }
        this._selectLine(line);
    }

    selectPackageLine(packageId) {
        this.lastScannedPackage = packageId;
    }

    toggleSublines(line) {
        const productId = line.product_id.id;
        const lineKey = this.groupKey(line);
        this.unfoldLineKey = this.unfoldLineKey === lineKey ? false : lineKey;
        this.trigger('update');
    }

    async updateLine(line, args) {
        let {lot_id, owner_id, package_id} = args;
        if (!line) {
            throw new Error('No line found');
        }
        if (!line.product_id && args.product_id) {
            line.product_id = args.product_id;
            line.product_uom_id = this.cache.getRecord('uom.uom', args.product_id.uom_id);
        }
        if (lot_id) {
            if (typeof lot_id === 'number') {
                lot_id = this.cache.getRecord('stock.production.lot', args.lot_id);
            }
            line.lot_id = lot_id;
        }
        if (owner_id) {
            if (typeof owner_id === 'number') {
                owner_id = this.cache.getRecord('res.partner', args.owner_id);
            }
            line.owner_id = owner_id;
        }
        if (package_id) {
            if (typeof package_id === 'number') {
                package_id = this.cache.getRecord('stock.quant.package', args.package_id);
            }
            line.package_id = package_id;
        }
        if (args.lot_name) {
            await this.updateLotName(line, args.lot_name);
        }
        this._updateLineQty(line, args);
        this._markLineAsDirty(line);
    }

    /**
     * Can be called by the user from the application. As the quantity field hasn't
     * the same name for all models, this method must be overridden by each model.
     *
     * @param {number} virtualId
     * @param {number} qty Quantity to increment (1 by default)
     */
    updateLineQty(virtualId, qty = 1) {
        throw new Error('Not Implemented');
    }

    async updateLotName(line, lotName) {
        // Checks if the tracking number isn't already used.
        for (const l of this.pageLines) {
            if (line.virtual_id === l.virtual_id ||
                line.product_id.tracking !== 'serial' || line.product_id.id !== l.product_id.id) {
                continue;
            }
            if (lotName === l.lot_name || (l.lot_id && lotName === l.lot_id.name)) {
                this.notification.add(_t("This serial number is already used."), { type: 'warning' });
                return Promise.reject();
            }
        }
        await this._updateLotName(line, lotName);
    }

    async validate() {
        await this.save();
        const action = await this.orm.call(
            this.params.model,
            this.validateMethod,
            [this.recordIds]
        );
        const options = {
            on_close: ev => {
                if (ev === undefined) {
                    // If all is OK, displays a notification and goes back to the previous page.
                    this.notification.add(this.validateMessage, { type: 'success' });
                    this.trigger('history-back');
                }
            },
        };
        if (action && action.res_model) {
            return this.trigger('do-action', { action, options });
        }
        return options.on_close();
    }

    async processBarcode(barcode) {
        this.actionMutex.exec(() => this._processBarcode(barcode));
    }

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _canOverrideTrackingNumber(line) {
        return false;
    }

    async _changePage(pageIndex) {
        if (this.pageIndex === pageIndex) {
            return;
        }
        this.pageIndex = pageIndex;
        this.currentLocationId = this.page.sourceLocationId;
        // Forgets which lines was scanned as the user isn't on the same page anymore.
        this.scannedLinesVirtualId = [];
        this.lastScannedPackage = false;
        await this.save();
    }

    _convertDataToFieldsParams(args) {
        throw new Error('Not Implemented');
    }

    /**
     * Creates a new line with passed parameters, adds it to the barcode app and
     * to the list of lines to save, then refresh the page.
     *
     * @param {Object} params
     * @param {Object} params.copyOf line to copy fields' value from
     * @param {Object} params.fieldsParams fields' value to override
     * @returns {Object} the newly created line
     */
    async _createNewLine(params) {
        const newLine = Object.assign(
            {},
            params.copyOf,
            this._getNewLineDefaultValues(params.fieldsParams)
        );
        await this.updateLine(newLine, params.fieldsParams);
        this.currentState.lines.push(newLine);
        this._groupLinesByPage(this.currentState);
        return newLine;
    }

    _defaultLocationId() {
        throw new Error('Not Implemented');
    }

    _defaultDestLocationId() {
        throw new Error('Not Implemented');
    }

    /**
     * Defines the page's location ID (get it from the lines or get the default one).
     *
     * @private
     */
    _defineLocationId() {
        if (this.page.lines.length) {
            this.currentLocationId = this.page.lines[0].location_id;
        } else {
            this.currentLocationId = this.page.sourceLocationId || this._defaultLocationId();
        }
    }

    _getCommands() {
        return {
            'O-CMD.PREV': this.previousPage.bind(this),
            'O-CMD.NEXT': this.nextPage.bind(this),
            'O-CMD.PAGER-FIRST': this._changePage.bind(this, 0),
            'O-CMD.PAGER-LAST': this._changePage.bind(this, () => this.pages.length - 1),
            'O-CMD.MAIN-MENU': this._goToMainMenu.bind(this),
            'O-BTN.validate': this.validate.bind(this),
        };
    }

    _getDefaultMessageType() {
        return this.groups.group_stock_multi_locations ? 'scan_src' : 'scan_product';
    }

    /**
     * Depending of the config, says if the user can scan a location or a product only.
     *
     * @returns {string}
     */
    _getLocationMessage() {
        if (this.groups.group_stock_multi_locations) {
            return 'scan_product_or_src';
        }
        return 'scan_product';
    }

    _getModelRecord() {
        return false;
    }

    _getNewLineDefaultValues(fieldsParams) {
        return {
            id: (fieldsParams && fieldsParams.id) || false,
            virtual_id: this._uniqueVirtualId,
            location_id: this.location.id,
        };
    }

    _getNewLineDefaultContext() {
        throw new Error('Not Implemented');
    }

    _getFieldToWrite() {
        throw new Error('Not Implemented');
    }

    _fieldToValue(fieldValue) {
        return typeof fieldValue === 'object' ? fieldValue.id : fieldValue;
    }

    _getSaveLineCommand() {
        const commands = [];
        const fields = this._getFieldToWrite();
        for (const virtualId of this.linesToSave) {
            const line = this.currentState.lines.find(l => l.virtual_id === virtualId);
            if (line.id) { // Update an existing line.
                const initialLine = this.initialState.lines.find(l => l.virtual_id === line.virtual_id);
                const changedValues = {};
                let somethingToSave = false;
                for (const field of fields) {
                    const fieldValue = line[field];
                    const initialValue = initialLine[field];
                    if (fieldValue !== undefined && (
                        (['boolean', 'number', 'string'].includes(typeof fieldValue) && fieldValue !== initialValue) ||
                        (typeof fieldValue === 'object' && fieldValue.id !== initialValue.id)
                    )) {
                        changedValues[field] = this._fieldToValue(fieldValue);
                        somethingToSave = true;
                    }
                }
                if (somethingToSave) {
                    commands.push([1, line.id, changedValues]);
                }
            } else { // Create a new line.
                commands.push([0, 0, this._createCommandVals(line)]);
            }
        }
        return commands;
    }

    _getSaveCommand() {
        throw new Error('Not Implemented');
    }

    /**
     * Groups the lines by their locations and will create a page for each ones.
     * If there is no lines, it will create at least one page for the default location.
     *
     * @param {Object} state record's data fetched from the server.
     */
    _groupLinesByPage(state) {
        const groups = {};
        for (const line of state.lines) { // Groups the barcode lines by src/dest locations.
            const key = `${line.location_id}_${line.location_dest_id}`;
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(line);
        }
        const pages = [];
        for (const [key, lines] of Object.entries(groups)) {
            const page = {
                index: pages.length,
                lines,
                sourceLocationId: lines[0].location_id,
                destinationLocationId: lines[0].location_dest_id,
            };
            pages.push(page);
        }
        if (pages.length === 0) { // If no pages, creates a default one.
            const page = {
                index: pages.length,
                lines: [],
                sourceLocationId: this.currentLocationId,
                destinationLocationId: this.currentLocationId,
            };
            pages.push(page);
        }
        this.pages = pages;
    }

    _groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        return Object.assign({}, sublines[0], {
            ids,
            lines: this._sortLine(sublines),
            opened: false,
            virtual_ids,
        });
    }

    async _goToMainMenu() {
        await this.save();
        this.trigger('do-action', {
            action: 'stock_barcode.stock_barcode_action_main_menu',
            options: {
                clear_breadcrumbs: true,
            },
        });
    }

    _createLinesState() {
        /* Basic lines structure */
        throw new Error('Not Implemented');
    }

    /**
     * Says if a tracked line can be incremented even if there is no tracking number on it.
     *
     * @returns {boolean}
     */
    _incrementTrackedLine() {
        return false;
    }

    _lineIsNotComplete(line) {
        throw new Error('Not Implemented');
    }

    /**
     * Keeps the track of a modified lines to save them later.
     *
     * @param {Object} line
     */
    _markLineAsDirty(line) {
        if (!this.linesToSave.includes(line.virtual_id)) {
            this.linesToSave.push(line.virtual_id);
        }
    }

    _moveEntirePackage() {
        return false;
    }

    /**
     * Will parse the given barcode according to the used nomenclature and return
     * the retrieved data as an object.
     *
     * @param {string} barcode
     * @param {Object} filters For some models, different records can have the same barcode
     *      (`stock.production.lot` for example). In this case, these filters can help to get only
     *      the wanted record by filtering by record's field's value.
     * @returns {Object} Containing following data:
     *      - {string} barcode: the scanned barcode
     *      - {boolean} match: true if the barcode match an existing record
     *      - {Object} data type: an object for each type of data/record corresponding to the
     *                 barcode. It could be 'action', 'location', 'product', ...
     */
    async _parseBarcode(barcode, filters) {
        const result = {
            barcode,
            match: false,
        };
        // First, simply checks if the barcode is an action.
        if (this.commands[barcode]) {
            result.action = this.commands[barcode];
            result.match = true;
            return result; // Simple barcode, no more information to retrieve.
        }
        // Then, parses the barcode through the nomenclature.
        await this.parser.is_loaded();
        try {
            const parsedBarcode = this.parser.parse_barcode(barcode);
            if (parsedBarcode.length) { // With the GS1 nomenclature, the parsed result is a list.
                for (const data of parsedBarcode) {
                    const { rule, value } = data;
                    if (['location', 'location_dest'].includes(rule.type)) {
                        const location = await this.cache.getRecordByBarcode(value, 'stock.location');
                        if (!location) {
                            continue;
                        }
                        // TODO: should be overrided, as location dest make sense only for pickings.
                        if (rule.type === 'location_dest' || this.messageType === 'scan_product_or_dest') {
                            result.destLocation = location;
                        } else {
                            result.location = location;
                        }
                        result.match = true;
                    } else if (rule.type === 'lot') {
                        if (this.useExistingLots) {
                            result.lot = await this.cache.getRecordByBarcode(value, 'stock.production.lot');
                        }
                        if (!result.lot) { // No existing lot found, set a lot name.
                            result.lotName = value;
                        }
                        if (result.lot || result.lotName) {
                            result.match = true;
                        }
                    } else if (rule.type === 'package') {
                        const stockPackage = await this.cache.getRecordByBarcode(value, 'stock.quant.package');
                        if (stockPackage) {
                            result.package = stockPackage;
                        } else {
                            // Will be used to force package's name when put in pack.
                            result.packageName = value;
                        }
                        result.match = true;
                    } else if (rule.type === 'package_type') {
                        const packageType = await this.cache.getRecordByBarcode(value, 'stock.package.type');
                        if (packageType) {
                            result.packageType = packageType;
                            result.match = true;
                        } else {
                            const message = _t("An unexisting package type was scanned. This part of the barcode can't be processed.");
                            this.notification.add(message, { type: 'warning' });
                        }
                    } else if (rule.type === 'product') {
                        const product = await this.cache.getRecordByBarcode(value, 'product.product');
                        if (product) {
                            result.product = product;
                            result.match = true;
                        }
                    } else if (rule.type === 'quantity') {
                        result.quantity = value;
                        // The quantity is usually associated to an UoM, but we
                        // ignore this info if the UoM setting is disabled.
                        if (this.groups.group_uom) {
                            result.uom = await this.cache.getRecord('uom.uom', rule.associated_uom_id);
                        }
                        result.match = result.quantity ? true : false;
                    }
                }
                if(result.match) {
                    return result;
                }
            } else if (parsedBarcode.type === 'weight') {
                result.weight = parsedBarcode;
                result.match = true;
                barcode = parsedBarcode.base_code;
            }
        } catch (err) {
            // The barcode can't be parsed but the error is caught to fallback
            // on the classic way to handle barcodes.
            console.log(`%cWarning: error about ${barcode}`, 'text-weight: bold;');
            console.log(err.message);
        }
        const recordByData = await this.cache.getRecordByBarcode(barcode, false, false, filters);
        if (recordByData.size > 1) {
            const message = sprintf(
                _t("Barcode scan is ambiguous with several model: %s. Use the most likely."),
                Array.from(recordByData.keys()));
            this.notification.add(message, { type: 'warning' });
        }

        if (this.groups.group_stock_multi_locations) {
            const location = recordByData.get('stock.location');
            if (location) {
                this._setLocationFromBarcode(result, location);
                result.match = true;
            }
        }

        if (this.groups.group_tracking_lot) {
            const packageType = recordByData.get('stock.package.type');
            const stockPackage = recordByData.get('stock.quant.package');
            if (stockPackage) {
                // TODO: should take packages only in current (sub)location.
                result.package = stockPackage;
                result.match = true;
            }
            if (packageType) {
                result.packageType = packageType;
                result.match = true;
            }
        }

        const product = recordByData.get('product.product');
        if (product) {
            result.product = product;
            result.match = true;
        }
        if (this.useExistingLots) {
            const lot = recordByData.get('stock.production.lot');
            if (lot) {
                result.lot = lot;
                result.match = true;
            }
        }
        const quantPackage = recordByData.get('stock.quant.package');
        if (this.groups.group_tracking_lot && quantPackage) {
            result.package = quantPackage;
            result.match = true;
        }

        if (!result.match && this.packageTypes.length) {
            // If no match, check if the barcode begins with a package type's barcode.
            for (const [packageTypeBarcode, packageTypeId] of this.packageTypes) {
                if (barcode.indexOf(packageTypeBarcode) === 0) {
                    result.packageType = await this.cache.getRecord('stock.package.type', packageTypeId);
                    result.packageName = barcode;
                    result.match = true;
                    break;
                }
            }
        }
        return result;
    }

    /**
     * Starts by parse the barcode and then process each type of barcode data.
     *
     * @param {string} barcode
     * @returns {Promise}
     */
    async _processBarcode(barcode) {
        let barcodeData = {};
        let currentLine = false;
        // Creates a filter if needed, which can help to get the right record
        // when multiple records have the same model and barcode.
        const filters = {};
        if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
            filters['stock.production.lot'] = {
                product_id: this.selectedLine.product_id.id,
            };
        }
        try {
            barcodeData = await this._parseBarcode(barcode, filters);
        } catch (parseErrorMessage) {
            barcodeData.error = parseErrorMessage;
        }

        // Process each data in order, starting with non-ambiguous data type.
        if (barcodeData.action) { // As action is always a single data, call it and do nothing else.
            return await barcodeData.action();
        }

        if (barcodeData.lot && !barcode.product) {
            barcodeData.product = this.cache.getRecord('product.product', barcodeData.lot.product_id);
        }

        await this._processLocation(barcodeData);
        await this._processPackage(barcodeData);
        if (barcodeData.stopped) {
            // TODO: Sometime we want to stop here instead of keeping doing thing,
            // but it's a little hacky, it could be better to don't have to do that.
            return;
        }

        if (barcodeData.weight) { // Convert the weight into quantity.
            barcodeData.quantity = barcodeData.weight.value;
        }

        // If no product found, take the one from last scanned line if possible.
        if (!barcodeData.product) {
            if (barcodeData.quantity) {
                currentLine = this.selectedLine || this.lastScannedLine;
            } else if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
                currentLine = this.selectedLine;
            } else if (this.lastScannedLine && this.lastScannedLine.product_id.tracking !== 'none') {
                currentLine = this.lastScannedLine;
            }
            if (currentLine) { // If we can, get the product from the previous line.
                const previousProduct = currentLine.product_id;
                // If the current product is tracked and the barcode doesn't fit
                // anything else, we assume it's a new lot/serial number.
                if (previousProduct.tracking !== 'none' &&
                    !barcodeData.match && this.canCreateNewLine) {
                    barcodeData.lotName = barcode;
                }
                if (currentLine.lot_id || currentLine.lot_name ||
                    barcodeData.lot || barcodeData.lotName ||
                    barcodeData.quantity) {
                    barcodeData.product = previousProduct;
                }
            }
        }
        const {product} = barcodeData;
        if (!product) { // Product is mandatory, if no product, raises a warning.
            if (!barcodeData.error) {
                if (this.groups.group_tracking_lot) {
                    barcodeData.error = _t("You are expected to scan one or more products or a package available at the picking location");
                } else {
                    barcodeData.error = _t("You are expected to scan one or more products.");
                }
            }
            return this.notification.add(barcodeData.error, { type: 'danger' });
        }

        // Default quantity set to 1 by default if the product is untracked or
        // if there is a scanned tracking number.
        if (product.tracking === 'none' || barcodeData.lot || barcodeData.lotName || this._incrementTrackedLine()) {
            barcodeData.quantity = barcodeData.quantity || 1;
            if (product.tracking === 'serial' && barcodeData.quantity > 1 && (barcodeData.lot || barcodeData.lotName)) {
                barcodeData.quantity = 1;
                this.notification.add(
                    _t(`A product tracked by serial numbers can't have multiple quantities for the same serial number.`),
                    { type: 'danger' }
                );
            }
        }

        // Searches and selects a line if needed.
        if (!currentLine || this._shouldSearchForAnotherLine(currentLine, barcodeData)) {
            currentLine = this._findLine(barcodeData);
        }

        if ((barcodeData.lotName || barcodeData.lot) && product) {
            const lotName = barcodeData.lotName || barcodeData.lot.name;
            for (const line of this.currentState.lines) {
                if (line.product_id.tracking === 'serial' && this.getQtyDone(line) !== 0 &&
                    ((line.lot_id && line.lot_id.name) || line.lot_name) === lotName) {
                    return this.notification.add(
                        _t("The scanned serial number is already used."),
                        { type: 'danger' }
                    );
                }
            }
            // Prefills `owner_id` and `package_id` if possible.
            const prefilledOwner = (!currentLine || (currentLine && !currentLine.owner_id)) && this.groups.group_tracking_owner && !barcodeData.owner;
            const prefilledPackage = (!currentLine || (currentLine && !currentLine.package_id)) && this.groups.group_tracking_lot && !barcodeData.package;
            if (this.useExistingLots && (prefilledOwner || prefilledPackage)) {
                const lotId = (barcodeData.lot && barcodeData.lot.id) || (currentLine && currentLine.lot_id && currentLine.lot_id.id) || false;
                const res = await this.orm.call(
                    'product.product',
                    'prefilled_owner_package_stock_barcode',
                    [product.id],
                    {
                        lot_id: lotId,
                        lot_name: (!lotId && barcodeData.lotName) || false,
                    }
                );
                this.cache.setCache(res.records);
                if (prefilledPackage && res.quant && res.quant.package_id) {
                    barcodeData.package = this.cache.getRecord('stock.quant.package', res.quant.package_id);
                }
                if (prefilledOwner && res.quant && res.quant.owner_id) {
                    barcodeData.owner = this.cache.getRecord('res.partner', res.quant.owner_id);
                }
            }
        }

        // Updates or creates a line based on barcode data.
        if (currentLine) { // If line found, can it be incremented ?
            let exceedingQuantity = 0;
            if (this.canCreateNewLine) {
                // Checks the quantity doesn't exceed the line's remaining quantity.
                if (currentLine.product_uom_qty && product.tracking === 'none') {
                    const remainingQty = currentLine.product_uom_qty - currentLine.qty_done;
                    if (barcodeData.quantity > remainingQty) {
                        // In this case, lowers the increment quantity and keeps
                        // the excess quantity to create a new line.
                        exceedingQuantity = barcodeData.quantity - remainingQty;
                        barcodeData.quantity = remainingQty;
                    }
                }
            }
            if (barcodeData.quantity > 0) {
                const fieldsParams = this._convertDataToFieldsParams({
                    qty: barcodeData.quantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: barcodeData.package,
                    owner: barcodeData.owner,
                });
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                await this.updateLine(currentLine, fieldsParams);
            }
            if (exceedingQuantity) { // Creates a new line for the excess quantity.
                const fieldsParams = this._convertDataToFieldsParams({
                    product,
                    qty: exceedingQuantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: barcodeData.package,
                    owner: barcodeData.owner,
                });
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                currentLine = await this._createNewLine({
                    copyOf: currentLine,
                    fieldsParams,
                });
            }
        } else if (this.canCreateNewLine) { // No line found. If it's possible, creates a new line.
            const fieldsParams = this._convertDataToFieldsParams({
                product,
                qty: barcodeData.quantity,
                lotName: barcodeData.lotName,
                lot: barcodeData.lot,
                package: barcodeData.package,
                owner: barcodeData.owner,
            });
            if (barcodeData.uom) {
                fieldsParams.uom = barcodeData.uom;
            }
            currentLine = await this._createNewLine({fieldsParams});
        }

        // And finally, if the scanned barcode modified a line, selects this line.
        if (currentLine) {
            this.selectLine(currentLine);
        }
        this.trigger('update');
    }

    async _processLocation(barcodeData) {
        if (barcodeData.location) {
            await this._processLocationSource(barcodeData);
            this.trigger('update');
        }
    }

    async _processLocationSource(barcodeData) {
        this.highlightSourceLocation = true;
        this.highlightDestinationLocation = false;
        await this.changeSourceLocation(barcodeData.location.id);
        barcodeData.stopped = true;
    }

    async _processPackage(barcodeData) {
        throw new Error('Not Implemented');
    }

    _selectLine(line) {
        const virtualId = line.virtual_id;
        this.selectedLineVirtualId = virtualId;
        this.scannedLinesVirtualId.push(virtualId);
        // Unfolds the group where the line is, folds other lines' group.
        this.unfoldLineKey = this.groupKey(line);
    }

    _setLocationFromBarcode(result, location) {
        result.location = location;
        return result;
    }

    _sortingMethod(l1, l2) {
        // New lines always on top.
        if (!l1.id && l2.id) {
            return -1;
        } else if (l1.id && !l2.id) {
            return 1;
        } else if (l1.id && l2.id) {
            // Sort by display name of product.
            const product1 = l1.product_id.display_name;
            const product2 = l2.product_id.display_name;
            if (product1 < product2) {
                return -1;
            } else if (product1 > product2) {
                return 1;
            }
            // Sort by picking name.
            const picking1 = l1.picking_id && l1.picking_id.name || '';
            const picking2 = l2.picking_id && l2.picking_id.name || '';
            if (picking1 < picking2) {
                return -1;
            } else if (picking1 > picking2) {
                return 1;
            }

            if (l1.id < l2.id) {
                return -1;
            } else if (l1.id > l2.id) {
                return 1;
            }
        }
        // Sort by id and/or virtual_id (creation of the line).
        if (l1.virtual_id > l2.virtual_id) {
            return -1;
        } else if (l1.virtual_id < l2.virtual_id) {
            return 1;
        }
        return 0;
    }

    /**
     * Sorts the lines to have new lines always on top and complete lines always on the bottom.
     *
     * @param {Array<Object>} lines
     * @returns {Array<Object>}
     */
    _sortLine(lines) {
        return lines.sort(this._sortingMethod.bind(this));
    }

    _findLine(barcodeData) {
        let foundLine = false;
        const {lot, lotName, product} = barcodeData;
        const quantPackage = barcodeData.package;
        const dataLotName = lotName || (lot && lot.name) || false;
        for (const line of this.pageLines) {
            const lineLotName = line.lot_name || (line.lot_id && line.lot_id.name) || false;
            if (line.product_id.id !== product.id) {
                continue; // Not the same product.
            }
            if (quantPackage && (!line.package_id || line.package_id.id !== quantPackage.id)) {
                continue; // Not the expected package.
            }
            if (dataLotName && lineLotName && dataLotName !== lineLotName && !this._canOverrideTrackingNumber(line)) {
                continue; // Not the same lot.
            }
            if (line.product_id.tracking === 'serial') {
                if (this.getQtyDone(line) >= 1 && lineLotName) {
                    continue; // Line tracked by serial numbers with quantity & SN.
                } else if (dataLotName && this.getQtyDone(line) > 1) {
                    continue; // Can't add a SN on a line where multiple qty. was previously added.
                }
            }
            if ((
                    !dataLotName || !lineLotName || dataLotName !== lineLotName
                ) && (
                    line.qty_done && line.qty_done > line.product_uom_qty &&
                    line.virtual_id != this.selectedLine.virtual_id
            )) {
                continue;
            }
            if (this._lineIsNotComplete(line)) {
                // Found a uncompleted compatible line, stop searching.
                foundLine = line;
                break;
            }
            // The line matches but there could be a better candidate, so keep searching.
            // If multiple lines can match, prioritises the selected line if relevant.
            foundLine = this.selectedLine && this.selectedLine.virtual_id === line.virtual_id ? line : foundLine || line;
        }
        return foundLine;
    }

    _shouldSearchForAnotherLine(line, barcodeData) {
        if (line.product_id.id !== barcodeData.product.id) {
            return true;
        }
        if (barcodeData.product.tracking === 'serial' && this.getQtyDone(line) > 0) {
            return true;
        }
        const {lot, lotName} = barcodeData;
        const dataLotName = lotName || (lot && lot.name) || false;
        const lineLotName = line.lot_name || (line.lot_id && line.lot_id.name) || false;
        if (dataLotName && lineLotName && dataLotName !== lineLotName) {
            return true;
        }
        // If the line is a part of a group, we check if the group is fulfilled.
        const groupLines = this.groupedLines.filter(gl => gl.lines);
        const parentLine = groupLines.find(gl => gl.virtual_ids.indexOf(line.virtual_id) !== -1);
        if (parentLine) {
            return this.getQtyDone(parentLine) >= this.getQtyDemand(parentLine);
        }
        return false;
    }

    get _uniqueVirtualId() {
        this._lastVirtualId = this._lastVirtualId || 0;
        return ++this._lastVirtualId;
    }

    _updateLineQty(line, qty) {
        throw new Error('Not Implemented');
    }

    _updateLotName(line, lotName) {
        throw new Error('Not Implemented');
    }

    _getName() {
        return this.cache.getRecord(this.params.model, this.params.id).name;
    }

    // Response -> UI State
    _createState() {
        this.record = this._getModelRecord();
        this.initialState = {
            lines: this._createLinesState(), // object lines to show {product_id: {<product_record>}}
        };
        this.currentState = JSON.parse(JSON.stringify(this.initialState)); // Deep copy
    }
}
