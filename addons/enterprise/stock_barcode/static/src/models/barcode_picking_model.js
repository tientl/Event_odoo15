/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import {_t} from "web.core";
import { sprintf } from '@web/core/utils/strings';

export default class BarcodePickingModel extends BarcodeModel {
    constructor(params) {
        super(...arguments);
        this.formViewReference = 'stock_barcode.stock_picking_barcode';
        this.lineModel = 'stock.move.line';
        this.lineFormViewReference = 'stock_barcode.stock_move_line_product_selector';
        this.validateMessage = _t("The transfer has been validated");
        this.validateMethod = 'button_validate';
    }

    setData(data) {
        super.setData(...arguments);
        // Manage extra information for locations
        this.currentDestLocationId = this._defaultDestLocationId();
        if (this.pageLines.length > 0) {
            this.currentDestLocationId = this.pageLines[0].location_dest_id;
        }
        this.locationList = [];
        this.destLocationList = [];
        data.data.source_location_ids.forEach(id => {
            this.locationList.push(this.cache.getRecord('stock.location', id));
        });
        data.data.destination_locations_ids.forEach(id => {
            this.destLocationList.push(this.cache.getRecord('stock.location', id));
        });
        this._useReservation = this.initialState.lines.some(line => line.product_uom_qty);
    }

    async changeDestinationLocation(id, moveScannedLineOnly) {
        this.currentDestLocationId = id;
        if (moveScannedLineOnly && this.previousScannedLines.length) {
            this.currentDestLocationId = id;
            for (const line of this.previousScannedLines) {
                // If the line is complete, we move it...
                if (!line.product_uom_qty || line.qty_done >= line.product_uom_qty) {
                    line.location_dest_id = id;
                    this._markLineAsDirty(line);
                } else { // ... otherwise, we split it to a new line.
                    const newLine = Object.assign({}, line, this._getNewLineDefaultValues({}));
                    this.currentState.lines.push(newLine);
                    newLine.qty_done = line.qty_done;
                    line.qty_done = 0;
                    this._markLineAsDirty(newLine);
                }
            }
        } else {
            // If the button was used to change the location, if will change the
            // destination location of all the page's move lines.
            for (const line of this.pageLines) {
                line.location_dest_id = id;
                this._markLineAsDirty(line);
            }
        }
        // Forget what lines have been scanned.
        this.scannedLinesVirtualId = [];
        this.lastScannedPackage = false;

        await this.save();
        this._groupLinesByPage(this.currentState);
        for (let i = 0; i < this.pages.length; i++) {
            const page = this.pages[i];
            if (page.sourceLocationId === this.currentLocationId &&
                page.destinationLocationId === this.currentDestLocationId) {
                this.pageIndex = i;
                break;
            }
        }
        this.selectedLineVirtualId = false;
    }

    getIncrementQuantity(line) {
        return Math.max(this.getQtyDemand(line) - this.getQtyDone(line), 1);
    }

    getQtyDone(line) {
        return line.qty_done;
    }

    getQtyDemand(line) {
        return line.product_uom_qty;
    }

    nextPage() {
        this.highlightDestinationLocation = false;
        return super.nextPage(...arguments);
    }

    previousPage() {
        this.highlightDestinationLocation = false;
        return super.previousPage(...arguments);
    }

    async updateLine(line, args) {
        await super.updateLine(...arguments);
        let {result_package_id} = args;
        if (result_package_id) {
            if (typeof result_package_id === 'number') {
                result_package_id = this.cache.getRecord('stock.quant.package', result_package_id);
                if (result_package_id.package_type_id && typeof result_package_id === 'number') {
                    result_package_id.package_type_id = this.cache.getRecord('stock.package.type', result_package_id.package_type_id);
                }
            }
            line.result_package_id = result_package_id;
        }
    }

    updateLineQty(virtualId, qty = 1) {
        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, {qty_done: qty});
            this.trigger('update');
        });
    }

    get barcodeInfo() {
        if (this.isCancelled || this.isDone) {
            return {
                class: this.isDone ? 'picking_already_done' : 'picking_already_cancelled',
                message: this.isDone ?
                    _t("This picking is already done") :
                    _t("This picking is cancelled"),
                warning: true,
            };
        }
        return super.barcodeInfo;
    }

    get canBeProcessed() {
        return !['cancel', 'done'].includes(this.record.state);
    }

    get canCreateNewLot() {
        return this.record.use_create_lots;
    }

    async changeSourceLocation(id, applyChangeToPageLines = false) {
        // For the pickings, changes the location will change the source
        // location of all the page's move lines.
        if (applyChangeToPageLines) {
            for (const moveLine of this.pageLines) {
                moveLine.location_id = id;
                this._markLineAsDirty(moveLine);
            }
            this._groupLinesByPage(this.currentState);
        }
        return super.changeSourceLocation(...arguments);
    }

    get destLocation() {
        return this.cache.getRecord('stock.location', this.currentDestLocationId);
    }

    get displayCancelButton() {
        return !['done', 'cancel'].includes(this.record.state);
    }

    get displayDestinationLocation() {
        return this.groups.group_stock_multi_locations &&
            ['incoming', 'internal'].includes(this.record.picking_type_code);
    }

    get displayResultPackage() {
        return true;
    }

    get displaySourceLocation() {
        return super.displaySourceLocation &&
            ['internal', 'outgoing'].includes(this.record.picking_type_code);
    }

    get displayValidateButton() {
        return (this.pageIndex + 1) === this.pages.length;
    }

    get highlightNextButton() {
        if (!this.pageLines.length) {
            return false;
        }
        for (const line of this.pageLines) {
            if (line.product_uom_qty && line.qty_done < line.product_uom_qty) {
                return false;
            }
        }
        return Boolean(this.pageLines.length);
    }

    get highlightValidateButton() {
        return this.highlightNextButton;
    }

    get informationParams() {
        return {
            model: this.params.model,
            view: this.formViewReference,
            params: { currentId: this.params.id },
        };
    }

    get isDone() {
        return this.record.state === 'done';
    }

    get isCancelled() {
        return this.record.state === 'cancel';
    }

    lineIsFaulty(line) {
        return this._useReservation && line.qty_done > line.product_uom_qty;
    }

    get printButtons() {
        return [
            {
                name: _t("Print Picking Operations"),
                class: 'o_print_picking',
                method: 'do_print_picking',
            }, {
                name: _t("Print Delivery Slip"),
                class: 'o_print_delivery_slip',
                method: 'action_print_delivery_slip',
            }, {
                name: _t("Print Barcodes PDF"),
                class: 'o_print_barcodes_pdf',
                method: 'action_print_barcode_pdf',
            },
        ];
    }

    get selectedLine() {
        const selectedLine = super.selectedLine;
        if (selectedLine && selectedLine.location_dest_id === this.currentDestLocationId) {
            return selectedLine;
        }
        return false;
    }

    get useExistingLots() {
        return this.record.use_existing_lots;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    _getNewLineDefaultContext() {
        const picking = this.cache.getRecord(this.params.model, this.params.id);
        return {
            default_company_id: picking.company_id,
            default_location_id: this.location.id,
            default_location_dest_id: this.destLocation.id,
            default_picking_id: this.params.id,
            default_qty_done: 1,
        };
    }

    async _cancel() {
        await this.save();
        await this.orm.call(
            this.params.model,
            'action_cancel',
            [[this.params.id]]
        );
        this._cancelNotification();
        this.trigger('history-back');
    }

    _cancelNotification() {
        this.notification.add(_t("The transfer has been cancelled"));
    }

    async _changePage(pageIndex) {
        await super._changePage(...arguments);
        this.currentDestLocationId = this.page.destinationLocationId;
        this.highlightDestinationLocation = false;
    }

    _convertDataToFieldsParams(args) {
        const params = {
            lot_name: args.lotName,
            product_id: args.product,
            qty_done: args.qty,
        };
        if (args.lot) {
            params.lot_id = args.lot;
        }
        if (args.package) {
            params.package_id = args.package;
        }
        if (args.resultPackage) {
            params.result_package_id = args.resultPackage;
        }
        if (args.owner) {
            params.owner_id = args.owner;
        }
        return params;
    }

    _createCommandVals(line) {
        const values = {
            dummy_id: line.virtual_id,
            location_id: line.location_id,
            location_dest_id: line.location_dest_id,
            lot_name: line.lot_name,
            lot_id: line.lot_id,
            package_id: line.package_id,
            picking_id: line.picking_id,
            product_id: line.product_id,
            product_uom_id: line.product_uom_id,
            owner_id: line.owner_id,
            qty_done: line.qty_done,
            result_package_id: line.result_package_id,
            state: 'assigned',
        };
        for (const [key, value] of Object.entries(values)) {
            values[key] = this._fieldToValue(value);
        }
        return values;
    }

    _createLinesState() {
        const lines = [];
        const picking = this.cache.getRecord(this.params.model, this.params.id);
        for (const id of picking.move_line_ids) {
            const smlData = this.cache.getRecord('stock.move.line', id);
            // Checks if this line is already in the picking's state to get back
            // its `virtual_id` (and so, avoid to set a new `virtual_id`).
            const prevLine = this.currentState && this.currentState.lines.find(l => l.id === id);
            const previousVirtualId = prevLine && prevLine.virtual_id;
            smlData.virtual_id = Number(smlData.dummy_id) || previousVirtualId || this._uniqueVirtualId;
            smlData.product_id = this.cache.getRecord('product.product', smlData.product_id);
            smlData.product_uom_id = this.cache.getRecord('uom.uom', smlData.product_uom_id);
            smlData.lot_id = smlData.lot_id && this.cache.getRecord('stock.production.lot', smlData.lot_id);
            smlData.owner_id = smlData.owner_id && this.cache.getRecord('res.partner', smlData.owner_id);
            smlData.package_id = smlData.package_id && this.cache.getRecord('stock.quant.package', smlData.package_id);
            const resultPackage = smlData.result_package_id && this.cache.getRecord('stock.quant.package', smlData.result_package_id);
            if (resultPackage) { // Fetch the package type if needed.
                smlData.result_package_id = resultPackage;
                const packageType = resultPackage && resultPackage.package_type_id;
                resultPackage.package_type_id = packageType && this.cache.getRecord('stock.package.type', packageType);
            }
            lines.push(Object.assign({}, smlData));
        }
        // Sorts lines by source location (important to have a deterministic pages' order).
        lines.sort((l1, l2) => l1.location_id < l2.location_id ? -1 : 0);
        return lines;
    }

    _defaultLocationId() {
        return this.record.location_id;
    }

    _defaultDestLocationId() {
        return this.record.location_dest_id;
    }

    /**
     * @override
     */
    _defineLocationId() {
        super._defineLocationId();
        if (this.page.lines.length) {
            this.currentDestLocationId = this.page.lines[0].location_dest_id;
        } else {
            this.currentDestLocationId = this._defaultDestLocationId();
        }
    }

    _getCommands() {
        return Object.assign(super._getCommands(), {
            'O-BTN.pack': this._putInPack.bind(this),
            'O-CMD.cancel': this._cancel.bind(this),
        });
    }

    _getDefaultMessageType() {
        if (this.groups.group_stock_multi_locations && (
            !this.highlightSourceLocation || this.highlightDestinationLocation
            ) && ['outgoing', 'internal'].includes(this.record.picking_type_code)) {
            return 'scan_src';
        }
        return 'scan_product';
    }

    _getLocationMessage() {
        if (this.groups.group_stock_multi_locations) {
            if (this.record.picking_type_code === 'outgoing') {
                return 'scan_product_or_src';
            } else {
                return 'scan_product_or_dest';
            }
        }
        return 'scan_product';
    }

    _getModelRecord() {
        return this.cache.getRecord(this.params.model, this.params.id);
    }

    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        return Object.assign(defaultValues, {
            location_dest_id: this.destLocation.id,
            product_uom_qty: false,
            qty_done: 0,
            picking_id: this.params.id,
        });
    }

    _getFieldToWrite() {
        return [
            'location_id',
            'location_dest_id',
            'lot_id',
            'lot_name',
            'package_id',
            'owner_id',
            'qty_done',
            'result_package_id',
        ];
    }

    _getSaveCommand() {
        const commands = this._getSaveLineCommand();
        if (commands.length) {
            return {
                route: '/stock_barcode/save_barcode_data',
                params: {
                    model: this.params.model,
                    res_id: this.params.id,
                    write_field: 'move_line_ids',
                    write_vals: commands,
                },
            };
        }
        return {};
    }

    _groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        return Object.assign(super._groupSublines(...arguments), {
            product_uom_qty: qtyDemand,
            qty_done: qtyDone,
        });
    }

    _incrementTrackedLine() {
        return !(this.record.use_create_lots || this.record.use_existing_lots);
    }

    _lineIsNotComplete(line) {
        return line.product_uom_qty && line.qty_done < line.product_uom_qty;
    }

    _moveEntirePackage() {
        return this.record.picking_type_entire_packs;
    }

    async _processLocation(barcodeData) {
        await super._processLocation(...arguments);
        if (barcodeData.destLocation) {
            await this._processLocationDestination(barcodeData);
            this.trigger('update');
        }
    }

    async _processLocationDestination(barcodeData) {
        this.highlightDestinationLocation = true;
        await this.changeDestinationLocation(barcodeData.destLocation.id, true);
        this.trigger('update');
        barcodeData.stopped = true;
    }

    async _processPackage(barcodeData) {
        const { packageName } = barcodeData;
        const recPackage = barcodeData.package;
        this.lastScannedPackage = false;
        if (barcodeData.packageType && !recPackage) {
            // Scanned a package type and no existing package: make a put in pack (forced package type).
            barcodeData.stopped = true;
            return await this._processPackageType(barcodeData);
        } else if (packageName && !recPackage) {
            // Scanned a non-existing package: make a put in pack.
            barcodeData.stopped = true;
            return await this._putInPack({ default_name: packageName });
        } else if (!recPackage || (
            recPackage.location_id && recPackage.location_id != this.currentLocationId
        )) {
            return; // No package, package's type or package's name => Nothing to do.
        }
        // Scanned a package: fetches package's quant and creates a line for
        // each of them, except if the package is already scanned.
        // TODO: can check if quants already in cache to avoid to make a RPC if
        // there is all in it (or make the RPC only on missing quants).
        const res = await this.orm.call(
            'stock.quant',
            'get_stock_barcode_data_records',
            [recPackage.quant_ids]
        );
        const quants = res.records['stock.quant'];
        if (!quants.length) { // Empty package => Assigns it to the last scanned line.
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id && !currentLine.result_package_id) {
                const fieldsParams = this._convertDataToFieldsParams({
                    resultPackage: recPackage,
                });
                await this.updateLine(currentLine, fieldsParams);
                barcodeData.stopped = true;
                this.selectedLineVirtualId = false;
                this.lastScannedPackage = recPackage.id;
                this.trigger('update');
            }
            return;
        }
        this.cache.setCache(res.records);

        // Checks if the package is already scanned.
        let alreadyExisting = 0;
        for (const line of this.pageLines) {
            if (line.package_id && line.package_id.id === recPackage.id &&
                this.getQtyDone(line) > 0) {
                alreadyExisting++;
            }
        }
        if (alreadyExisting === quants.length) {
            barcodeData.error = _t("This package is already scanned.");
            return;
        }
        // For each quants, creates or increments a barcode line.
        for (const quant of quants) {
            const product = this.cache.getRecord('product.product', quant.product_id);
            const searchLineParams = Object.assign({}, barcodeData, { product });
            const currentLine = this._findLine(searchLineParams);
            if (currentLine) { // Updates an existing line.
                const fieldsParams = this._convertDataToFieldsParams({
                    qty: quant.quantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: recPackage,
                    owner: barcodeData.owner,
                });
                await this.updateLine(currentLine, fieldsParams);
            } else { // Creates a new line.
                const fieldsParams = this._convertDataToFieldsParams({
                    product,
                    qty: quant.quantity,
                    lot: quant.lot_id,
                    package: quant.package_id,
                    resultPackage: quant.package_id,
                    owner: quant.owner_id,
                });
                await this._createNewLine({ fieldsParams });
            }
        }
        barcodeData.stopped = true;
        this.selectedLineVirtualId = false;
        this.lastScannedPackage = recPackage.id;
        this.trigger('update');
    }

    async _processPackageType(barcodeData) {
        const { packageType } = barcodeData;
        const line = this.selectedLine;
        if (!line || !line.qty_done) {
            barcodeData.stopped = true;
            const message = _t("You can't apply a package type. First, scan product or select a line");
            return this.notification.add(message, { type: 'warning' });
        }
        const resultPackage = line.result_package_id;
        if (!resultPackage) { // No package on the line => Do a put in pack.
            const additionalContext = { default_package_type_id: packageType.id };
            if (barcodeData.packageName) {
                additionalContext.default_name = barcodeData.packageName;
            }
            await this._putInPack(additionalContext);
        } else if (resultPackage.package_type_id.id !== packageType.id) {
            // Changes the package type for the scanned one.
            await this.orm.write('stock.quant.package', [resultPackage.id], {
                package_type_id: packageType.id,
            });
            const message = sprintf(
                _t("Package type %s was correctly applied to the package %s"),
                packageType.name, resultPackage.name
            );
            this.notification.add(message, { type: 'success' });
            this.trigger('refresh');
        }
    }

    async _putInPack(additionalContext = {}) {
        const context = Object.assign({ barcode_view: true }, additionalContext);
        if (!this.groups.group_tracking_lot) {
            return this.notification.add(
                _t("To use packages, enable 'Packages' in the settings"),
                { type: 'danger'}
            );
        }
        await this.save();
        const result = await this.orm.call(
            this.params.model,
            'action_put_in_pack',
            [[this.params.id]],
            { context }
        );
        if (typeof result === 'object') {
            this.trigger('process-action', result);
        } else {
            this.trigger('refresh');
        }
    }

    _setLocationFromBarcode(result, location) {
        if (this.record.picking_type_code === 'outgoing') {
            result.location = location;
        } else if (this.record.picking_type_code === 'incoming') {
            result.destLocation = location;
        } else if (this.previousScannedLines.length) {
            result.destLocation = location;
        } else {
            result.location = location;
        }
        return result;
    }

    _sortingMethod(l1, l2) {
        const l1QtyDemand = this.getQtyDemand(l1);
        const l2QtyDemand = this.getQtyDemand(l2);
        const l1IsCompleted = l1QtyDemand && this.getQtyDone(l1) >= l1QtyDemand;
        const l2IsCompleted = l2QtyDemand && this.getQtyDone(l2) >= l2QtyDemand;
        // Complete lines always on the bottom.
        if (!l1IsCompleted && l2IsCompleted) {
            return -1;
        } else if (l1IsCompleted && !l2IsCompleted) {
            return 1;
        }
        return super._sortingMethod(...arguments);
    }

    _updateLineQty(line, args) {
        if (line.product_id.tracking === 'serial' && line.qty_done > 0 && (this.record.use_create_lots || this.record.use_existing_lots)) {
            return;
        }
        if (args.qty_done) {
            if (args.uom) {
                // An UoM was passed alongside the quantity, needs to check it's
                // compatible with the product's UoM.
                const productUOM = this.cache.getRecord('uom.uom', line.product_id.uom_id);
                if (args.uom.category_id !== productUOM.category_id) {
                    // Not the same UoM's category -> Can't be converted.
                    const message = sprintf(
                        _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the product's one (%s)."),
                        args.uom.name, productUOM.name
                    );
                    return this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'danger' });
                } else if (args.uom.id !== productUOM.id) {
                    // Compatible but not the same UoM => Need a conversion.
                    args.qty_done = (args.qty_done / args.uom.factor) * productUOM.factor;
                }
            }
            line.qty_done += args.qty_done;
        }
    }

    _updateLotName(line, lotName) {
        line.lot_name = lotName;
    }
}
