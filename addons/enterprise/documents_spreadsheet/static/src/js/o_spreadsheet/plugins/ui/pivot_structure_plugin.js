/** @odoo-module */
/* global _ */

import { _t } from "web.core";
import Domain from "web.Domain";
import pyUtils from "web.py_utils";

import spreadsheet from "../../o_spreadsheet_loader";
import PivotDataSource from "../../helpers/pivot_data_source";

import { HEADER_STYLE, TOP_LEVEL_STYLE, MEASURE_STYLE } from "../../constants";
import PivotCache from "../../helpers/pivot_cache"; //Used for types
import { PERIODS, formatDate } from "../../helpers/pivot_helpers";

/**
 * @typedef {import("../core/pivot_plugin").SpreadsheetPivot} SpreadsheetPivot
 * @typedef {import("../../helpers/basic_data_source").Field} Field
 */
export default class PivotStructurePlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        this.dataSources = config.dataSources;
        /** @type {string} */
        this.selectedPivotId = undefined;
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "BUILD_PIVOT":
                this._handleBuildPivot(cmd.sheetId, cmd.anchor, cmd.pivot, cmd.cache);
                break;
            case "REBUILD_PIVOT":
                this._rebuildPivot(cmd.id, cmd.anchor);
                break;
            case "SELECT_PIVOT":
                this._selectPivot(cmd.pivotId);
                break;
            case "ADD_PIVOT_DOMAIN":
                this._addDomain(cmd.id, cmd.domain, cmd.refresh);
                break;
            case "START":
                this._refreshOdooPivots();
                break;
            case "REFRESH_PIVOT":
                this._refreshOdooPivot(cmd.id);
                break;
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooPivots();
                break;
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Format the given group by
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} groupBy Group by
     *
     * @returns {string}
     */
    getFormattedGroupBy(pivotId, groupBy) {
        let [name, period] = groupBy.split(":");
        period = PERIODS[period];
        return this.getPivotFieldName(pivotId, name) + (period ? ` (${period})` : "");
    }

    /**
     * Format a header value
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName field
     * @param {string} value Value
     *
     * @returns {string}
     */
    getFormattedHeader(pivotId, fieldName, value) {
        if (fieldName === "measure") {
            return value === "__count" ? _t("Count") : this.getPivotFieldName(pivotId, value);
        }
        const undef = _t("(Undefined)");
        const pivotData = this.getPivotStructureData(pivotId);
        const dataSource = this._getDataSource(pivotId);
        const field = dataSource.getField(fieldName.split(":")[0])
        if (
            field && field.relation &&
            !pivotData.isGroupLabelLoaded(fieldName, value) &&
            value !== "false"
        ) {
            dataSource._fetchLabel(field, value).then(() => dataSource.trigger("data-loaded"));
            return undefined;
        }
        if (this.getters.isPivotFieldDate(pivotId, fieldName.split(":")[0])) {
            return formatDate(fieldName, value);
        }
        const result = pivotData.getGroupLabel(fieldName, value) || undef;
        if (result instanceof Error) {
            throw result;
        }
        return result;
    }

    /**
     * Get the computed domain of a pivot
     *
     * @param {string} pivotId Id of the pivot
     * @returns {Array}
     */
    getPivotComputedDomain(pivotId) {
        return this._getDataSource(pivotId).getComputedDomain();
    }

    /**
     * Get the display name of the pivot
     *
     * @param {number} pivotId Pivot Id
     *
     * @returns {string}
     */
    getPivotDisplayName(pivotId) {
        const model =
            this._getDataSource(pivotId).getModelName() || this.getters.getPivotModel(pivotId);
        return `(#${pivotId}) ${model}`;
    }

    /**
     * Get the field with the given field name
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName Field name
     *
     * @returns {Field|undefined}
     */
    getPivotField(pivotId, fieldName) {
        return this._getDataSource(pivotId).getField(fieldName);
    }

    /**
     * Get the display name of a field. If the display name is not yet available,
     * returns the technical name
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName Technical name of the field
     *
     * @returns {string}
     */
    getPivotFieldName(pivotId, fieldName) {
        return this._getDataSource(pivotId).getFieldName(fieldName) || fieldName;
    }

    /**
     * Get the field definitions of a pivot
     * @param {string} pivotId Id of the pivot
     * @returns {Object.<string, Field>}
     */
    getPivotFields(pivotId) {
        return this._getDataSource(pivotId).getFields();
    }

    /**
     * Return all possible values in the pivot for a given field.
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName
     * @returns {Array<string>}
     */
    getPivotFieldValues(pivotId, fieldName) {
        return this.getPivotStructureData(pivotId).getFieldValues(fieldName);
    }

    /**
     * Get the value of a pivot header
     *
     * @param {string} pivotId Id of a pivot
     * @param {Array<string>} domain Domain
     */
    getPivotHeaderValue(pivotId, domain) {
        const pivotData = this.getPivotStructureData(pivotId);
        if (!pivotData) {
            this.waitForPivotDataReady(pivotId);
            return _t("Loading...");
        }
        pivotData.markAsHeaderUsed(domain);
        const len = domain.length;
        if (len === 0) {
            return _t("Total");
        }
        const field = domain[len - 2];
        const value = domain[len - 1];
        return this.getFormattedHeader(pivotId, field, value);
    }

    /**
     * Get the last update date of the pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {number|undefined}
     */
    getPivotLastUpdate(pivotId) {
        return this._getDataSource(pivotId).getLastUpdate();
    }

    /**
     * Get all the relational fields of all the pivot
     *
     * @returns {Array<string>}
     */
    getPivotRelationalFields() {
        return [
            ...new Set(
                this.getters
                    .getPivotIds()
                    .map((pivotId) => Object.values(this.getPivotFields(pivotId)))
                    .flat()
                    .filter((field) => field.type === "many2one")
                    .map((field) => field.relation)
            ),
        ];
    }

    /**
     * Get the display name of the model of a pivot. If the display name is not
     * available, returns the technical name
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {string}
     */
    getPivotModelDisplayName(pivotId) {
        return this._getDataSource(pivotId).getModelName() || this.getters.getPivotModel(pivotId);
    }

    /**
     * Get the structure data of the pivot
     * @param {string} pivotId Id of the pivot
     *
     * @returns {PivotCache|undefined}
     */
    getPivotStructureData(pivotId) {
        return this._getDataSource(pivotId).getSync();
    }

    /**
     * Get the value for a pivot cell
     *
     * @param {string} pivotId Id of a pivot
     * @param {string} measure Field name of the measures
     * @param {Array<string>} domain Domain
     *
     * @returns {string|number|undefined}
     */
    getPivotValue(pivotId, measure, domain) {
        const pivotData = this.getPivotStructureData(pivotId);
        if (!pivotData) {
            this.waitForPivotDataReady(pivotId);
            return "Loading...";
        }
        const measures = this.getters.getPivotMeasures(pivotId);
        const operator = measures.filter((m) => m.field === measure)[0].operator;
        pivotData.markAsValueUsed(domain, measure);
        return pivotData.getMeasureValue(measure, operator, domain);
    }

    /**
     * Retrieve the pivotId of the current selected cell
     *
     * @returns {string}
     */
    getSelectedPivotId() {
        return this.selectedPivotId;
    }

    /**
     * Returns true if the type of the field with the given name is a date
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName Name of the field
     *
     * @returns {boolean}
     */
    isPivotFieldDate(pivotId, fieldName) {
        const field = this.getPivotField(pivotId, fieldName);
        return field ? ["date", "datetime"].includes(field.type) : false;
    }

    /**
     * Validate the arguments of a pivot function
     *
     * @param {string} pivotId Id of a pivot
     * @param {string} measure Field name of the measures
     * @param {Array<string>} domain Domain
     */
    validatePivotArguments(pivotId, measure, domain) {
        this.getters.validatePivotHeaderArguments(pivotId, domain);
        const measures = this.getters.getPivotMeasures(pivotId).map((elt) => elt.field);
        if (!measures.includes(measure)) {
            const validMeasures = `(${measures})`;
            throw new Error(
                _.str.sprintf(
                    _t("The argument %s is not a valid measure. Here are the measures: %s"),
                    measure,
                    validMeasures
                )
            );
        }
    }

    /**
     * Validate the arguments of a pivot header function
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} domain Domain
     */
    validatePivotHeaderArguments(pivotId, domain) {
        if (!this.getters.isExistingPivot(pivotId)) {
            throw new Error(_.str.sprintf(_t('There is no pivot with id "%s"'), pivotId));
        }
        if (domain.length % 2 !== 0) {
            throw new Error(_t("Function PIVOT takes an even number of arguments."));
        }
    }
    /**
     * Wait for the pivotData to be loaded
     *
     * @param {string} pivotId
     * @param {Object} params
     * @param {boolean} params.force=false Force to refresh the cache
     * @param {boolean} params.initialDomain=false only refresh the data with the domain of the pivot,
     *                                      without the global filters
     */
    async waitForPivotDataReady(pivotId, params = {}) {
        if (params.initialDomain) {
            params.force = true;
        }
        await this._getDataSource(pivotId).get({
            forceFetch: params.force,
            initialDomain: params.initialDomain,
        });
    }

    /**
     * Wait for the metadata to be loaded
     *
     * @param {string} pivotId Id of the pivot
     */
    async waitForPivotMetaData(pivotId) {
        await this._getDataSource(pivotId).loadMetadata();
    }

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     * Get the data source of a pivot
     *
     * @private
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {PivotDataSource}
     */
    _getDataSource(pivotId) {
        return this.dataSources.get(`PIVOT_${pivotId}`);
    }

    /**
     * Add a pivot to the local state and build it at the given anchor
     *
     * @param {string} sheetId
     * @param {[number,number]} anchor
     * @param {SpreadsheetPivot} pivot
     * @param {PivotCache} cache
     *
     * @private
     */
    _handleBuildPivot(sheetId, anchor, pivot, cache) {
        this.dispatch("ADD_PIVOT", { pivot });
        this._buildPivot(sheetId, pivot.id, anchor, cache);
        const cols = [];
        for (let col = anchor[0]; col <= anchor[0] + cache.getTopHeaderCount(); col++) {
            cols.push(col);
        }
        const dataSource = this._getDataSource(pivot.id);
        dataSource.on("data-loaded", this, () => {
            this.dispatch("EVALUATE_CELLS", { sheetId: this.getters.getActiveSheetId() });
            this.dispatch("AUTORESIZE_COLUMNS", {
                sheetId,
                cols,
            });
            dataSource.off("data-loaded", this);
        });
    }
    /**
     * Rebuild a specific pivot and build it at the given anchor
     *
     * @param {string} pivotId Id of the pivot to rebuild
     * @param {Array<number>} anchor
     *
     * @private
     */
    _rebuildPivot(pivotId, anchor) {
        const sheetId = this.getters.getActiveSheetId();
        const cache = this._getDataSource(pivotId).getSync();
        this._buildPivot(sheetId, pivotId, anchor, cache);
    }
    /**
     * Select the given pivot id. If the id is undefined, it unselect the pivot.
     * @param {string|undefined} pivotId Id of the pivot, or undefined to remove
     *                                  the selected pivot
     */
    _selectPivot(pivotId) {
        this.selectedPivotId = pivotId;
    }

    /**
     * Refresh the cache of a pivot
     *
     * @param {string} pivotId Id of the pivot
     */
    _refreshOdooPivot(pivotId) {
        this.waitForPivotDataReady(pivotId, { force: true });
    }

    /**
     * Refresh the cache of all the lists
     */
    _refreshOdooPivots() {
        for (const pivotId of this.getters.getPivotIds()) {
            this._refreshOdooPivot(pivotId);
        }
    }

    /**
     * Add an additional domain to a pivot
     *
     * @private
     *
     * @param {string} pivotId pivot id
     * @param {Array<Array<any>>} domain
     * @param {boolean} refresh whether the cache should be reloaded or not
     */
    _addDomain(pivotId, domain, refresh = true) {
        domain = pyUtils.assembleDomains(
            [
                Domain.prototype.arrayToString(this.getters.getPivotDomain(pivotId)),
                Domain.prototype.arrayToString(domain),
            ],
            "AND"
        );
        const computedDomain = pyUtils.eval("domain", domain, {});
        this._getDataSource(pivotId).setComputedDomain(computedDomain);
        if (refresh) {
            this._refreshOdooPivot(pivotId);
        }
    }

    // ---------------------------------------------------------------------
    // Build Pivot
    // ---------------------------------------------------------------------

    /**
     * Build a pivot at the given anchor
     *
     * @param {string} sheetId Id of the sheet
     * @param {string} pivotId Id of the pivot
     * @param {[number,number]} anchor
     * @param {PivotCache} cache
     *
     * @private
     */
    _buildPivot(sheetId, pivotId, anchor, cache) {
        this._resizeSheet(sheetId, pivotId, anchor, cache);
        this._buildColHeaders(sheetId, pivotId, anchor, cache);
        this._buildRowHeaders(sheetId, pivotId, anchor, cache);
        this._buildValues(sheetId, pivotId, anchor, cache);
    }
    /**
     * Build the headers of the columns
     *  1) Apply style on the top-left cells
     *  2) Create the column headers
     *  3) Create the total measures
     *  4) Merge the consecutive titles
     *  5) Apply the style of titles
     *  6) Apply the style of headers
     *
     * @param {string} sheetId Id of the sheet
     * @param {string} pivotId Id of the pivot
     * @param {[number,number]} anchor
     * @param {PivotCache} cache
     *
     * @private
     */
    _buildColHeaders(sheetId, pivotId, anchor, cache) {
        const [colAnchor, rowAnchor] = anchor;
        const bold = [];
        const levels = cache.getColGroupByLevels();
        const measures = this.getters.getPivotMeasures(pivotId);
        // 1) Apply style on the top-left cells
        this._applyStyle(sheetId, HEADER_STYLE, [
            {
                top: rowAnchor,
                bottom: rowAnchor + levels,
                left: colAnchor,
                right: colAnchor,
            },
        ]);

        // 2) Create the column headers
        let col = colAnchor + 1;

        // Do not take the last measures into account here
        let length = cache.getTopHeaderCount() - measures.length;
        if (length === 0) {
            length = cache.getTopHeaderCount();
        }

        for (let i = 0; i < length; i++) {
            let row = rowAnchor;
            for (let level = 0; level <= levels; level++) {
                const args = [pivotId];
                const values = cache.getColGroupHierarchy(i, level);
                for (const index in values) {
                    args.push(cache.getColLevelIdentifier(index));
                    args.push(values[index]);
                }
                this._applyFormula(sheetId, col, row, args, true);
                if (level <= levels - 1) {
                    bold.push({ top: row, bottom: row, left: col, right: col });
                }
                row++;
            }
            col++;
        }

        // 3) Create the total for measures
        let row = rowAnchor + levels - 1;
        for (let i = length; i < cache.getTopHeaderCount(); i++) {
            this._applyFormula(sheetId, col, row, [pivotId], true);
            bold.push({ top: row, bottom: row, left: col, right: col });
            const args = [pivotId, "measure", cache.getColGroupHierarchy(i, 1)[0]];
            this._applyFormula(sheetId, col, row + 1, args, true);
            col++;
        }

        // 4) Merge the same headers
        col = colAnchor + 1;
        let value;
        let first;
        for (let index = 0; index < cache.getColGroupByLevels(); index++) {
            let row = rowAnchor + index;
            for (let i = 0; i < length; i++) {
                const next = JSON.stringify(cache.getColGroupHierarchy(i, index));
                if (!value) {
                    value = next;
                    first = col + i;
                } else if (value !== next) {
                    this._merge(sheetId, {
                        top: row,
                        bottom: row,
                        left: first,
                        right: col + i - 1,
                    });
                    value = next;
                    first = col + i;
                }
            }
            if (first && first !== col + length - 1) {
                this._merge(sheetId, {
                    top: row,
                    bottom: row,
                    left: first,
                    right: col + length - 1,
                });
            }
            first = undefined;
            value = undefined;
        }

        for (let index = 0; index < cache.getColGroupByLevels(); index++) {
            const row = rowAnchor + index;
            const colStart = cache.getTopHeaderCount() - measures.length + 1;
            this._merge(sheetId, {
                top: row,
                bottom: row,
                left: colStart,
                right: colStart + measures.length - 1,
            });
        }

        // 5) Apply formatting on headers
        this._applyStyle(sheetId, HEADER_STYLE, [
            {
                top: rowAnchor,
                bottom: rowAnchor + cache.getColGroupByLevels() - 1,
                left: colAnchor,
                right: colAnchor + cache.getTopHeaderCount(),
            },
        ]);

        for (let zone of bold) {
            this._applyStyle(sheetId, TOP_LEVEL_STYLE, [zone]);
        }

        // 6) Apply formatting on measures
        this._applyStyle(sheetId, MEASURE_STYLE, [
            {
                top: rowAnchor + cache.getColGroupByLevels(),
                bottom: rowAnchor + cache.getColGroupByLevels(),
                left: colAnchor + 1,
                right: colAnchor + cache.getTopHeaderCount(),
            },
        ]);
    }
    /**
     * Build the row headers
     * 1) Create rows
     * 2) Apply style
     *
     * @param {string} sheetId Id of the sheet
     * @param {string} pivotId Id of the pivot
     * @param {[number,number]} anchor
     * @param {PivotCache} cache
     *
     * @private
     */
    _buildRowHeaders(sheetId, pivotId, anchor, cache) {
        const col = anchor[0];
        const anchorRow = anchor[1] + cache.getColGroupByLevels() + 1;
        const levelOne = [];
        const levelTwo = [];
        const rowCount = cache.getRowCount();
        const rowGroupBys = this.getters.getPivotRowGroupBys(pivotId);
        for (let index = 0; index < rowCount; index++) {
            const args = [pivotId];
            const row = anchorRow + parseInt(index, 10);
            const current = cache.getRowValues(index);
            for (let i in current) {
                args.push(rowGroupBys[i]);
                args.push(current[i]);
            }
            this._applyFormula(sheetId, col, row, args, true);
            if (current.length <= 1) {
                levelOne.push({ top: row, bottom: row, left: col, right: col });
            }
            if (current.length == 2) {
                levelTwo.push({ top: row, bottom: row, left: col, right: col });
            }
        }
        this._applyStyle(sheetId, TOP_LEVEL_STYLE, levelOne);
        this._applyStyle(sheetId, HEADER_STYLE, levelTwo);
    }
    /**
     * Build the values of the pivot
     *  1) Create the values for all cols and rows
     *  2) Create the values for total measure
     *  3) Apply format
     *
     * @param {string} sheetId Id of the sheet
     * @param {string} pivotId Id of the pivot
     * @param {[number,number]} anchor
     * @param {PivotCache} cache
     *
     * @private
     */
    _buildValues(sheetId, pivotId, anchor, cache) {
        const anchorCol = anchor[0] + 1;
        const anchorRow = anchor[1] + cache.getColGroupByLevels() + 1;
        const measures = this.getters.getPivotMeasures(pivotId);
        const rowGroupBys = this.getters.getPivotRowGroupBys(pivotId);
        // 1) Create the values for all cols and rows
        let col = anchorCol;
        let row = anchorRow;

        const length = cache.getTopHeaderCount() - measures.length;

        for (let i = 0; i < length; i++) {
            const colElement = [...cache.getColumnValues(i), cache.getMeasureName(i)];
            row = anchorRow;
            for (let rowElement of cache.getRows()) {
                const args = [];
                for (let index in rowElement) {
                    args.push(rowGroupBys[index]);
                    args.push(rowElement[index]);
                }
                for (let index in colElement) {
                    const field = cache.getColLevelIdentifier(index);
                    if (field === "measure") {
                        args.unshift(colElement[index]);
                    } else {
                        args.push(cache.getColLevelIdentifier(index));
                        args.push(colElement[index]);
                    }
                }
                args.unshift(pivotId);
                this._applyFormula(sheetId, col, row, args, false);
                row++;
            }
            col++;
        }

        // 2) Create the total for measures
        row = anchorRow;
        for (let i = length; i < cache.getTopHeaderCount(); i++) {
            const colElement = [...cache.getColumnValues(i), cache.getMeasureName(i)];
            row = anchorRow;
            for (let rowElement of cache.getRows()) {
                const args = [];
                for (let index in rowElement) {
                    args.push(rowGroupBys[index]);
                    args.push(rowElement[index]);
                }
                args.unshift(colElement[0]);
                args.unshift(pivotId);
                this._applyFormula(sheetId, col, row, args, false);
                row++;
            }
            col++;
        }

        // 3) Apply format
        this._applyFormat(sheetId, "#,##0.00", [
            {
                top: anchorRow,
                bottom: anchorRow + cache.getRowCount() - 1,
                left: anchorCol,
                right: anchorCol + cache.getTopHeaderCount() - 1,
            },
        ]);
    }

    /**
     * Extend the columns and rows to fit the pivot
     * @param {string} sheetId Id of the sheet
     * @param {string} pivotId Id of the pivot
     * @param {[number,number]} anchor
     * @param {PivotCache} cache
     */
    _resizeSheet(sheetId, pivotId, anchor, cache) {
        const measures = this.getters.getPivotMeasures(pivotId);
        const colLimit = cache.getTopHeaderCount() + measures.length + 1;
        const sheet = this.getters.getSheet(sheetId);
        const numberCols = sheet.cols.length;
        const deltaCol = numberCols - anchor[0];
        if (deltaCol < colLimit) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "COL",
                base: numberCols - 1,
                sheetId: sheetId,
                quantity: colLimit - deltaCol,
                position: "after",
            });
        }
        const rowLimit = cache.getRowCount() + cache.getColGroupByLevels() + 2;
        const numberRows = sheet.rows.length;
        const deltaRow = numberRows - anchor[1];
        if (deltaRow < rowLimit) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "ROW",
                base: numberRows - 1,
                sheetId: sheetId,
                quantity: rowLimit - deltaRow,
                position: "after",
            });
        }
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    /**
     * Build a formula and update the cell with this formula
     *
     * @param {string} sheetId
     * @param {number} col
     * @param {number} row
     * @param {Array<string>} args
     * @param {boolean} isHeader
     *
     * @private
     */
    _applyFormula(sheetId, col, row, args, isHeader) {
        this.dispatch("ADD_PIVOT_FORMULA", {
            sheetId,
            col,
            row,
            formula: isHeader ? "PIVOT.HEADER" : "PIVOT",
            args,
        });
    }
    /**
     * Apply the given format to the given target
     *
     * @param {string} sheetId
     * @param {string} format
     * @param {Object} target
     *
     * @private
     */
    _applyFormat(sheetId, format, target) {
        this.dispatch("SET_FORMATTING", { sheetId, target, format });
    }
    /**
     * Apply the given formatter to the given target
     *
     * @param {string} sheetId
     * @param {Object} style
     * @param {Object} target
     *
     * @private
     */
    _applyStyle(sheetId, style, target) {
        this.dispatch("SET_FORMATTING", { sheetId, target, style });
    }
    /**
     * Merge a zone
     *
     * @param {string} sheetId
     * @param {Object} zone
     *
     * @private
     */
    _merge(sheetId, zone) {
        // Some superfluous values are set in cells that end up "beneath"
        // merges. Those non-empty cells prevent the merge, unless forced.
        // TODO remove those useless cell updates and/or merge zones first.
        this.dispatch("ADD_MERGE", { sheetId, target: [zone], force: true });
    }
}

PivotStructurePlugin.modes = ["normal", "headless"];
PivotStructurePlugin.getters = [
    "getPivotComputedDomain",
    "getPivotDisplayName",
    "getPivotField",
    "getPivotFieldName",
    "getPivotFields",
    "getPivotHeaderValue",
    "getPivotValue",
    "getFormattedGroupBy",
    "getFormattedHeader",
    "getPivotModelDisplayName",
    "getPivotStructureData",
    "isPivotFieldDate",
    "validatePivotArguments",
    "validatePivotHeaderArguments",
    "waitForPivotDataReady",
    "waitForPivotMetaData",
    "getSelectedPivotId",
    "getPivotLastUpdate",
    "getPivotFieldValues",
    "getPivotRelationalFields",
];
