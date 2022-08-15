/** @odoo-module */

/**
 * @typedef {Object} SpreadsheetPivot
 * @property {Array<string>} colGroupBys
 * @property {Object} context
 * @property {Array} domain
 * @property {string} id
 * @property {Array<string>} measures
 * @property {string} model
 * @property {Array<string>} rowGroupBys
 *
 * @typedef {Object} SpreadsheetPivotForRPC
 * @property {Array<string>} colGroupBys
 * @property {Object} context
 * @property {Array} domain
 * @property {Array<string>} measures
 * @property {string} model
 * @property {Array<string>} rowGroupBys
 */

import spreadsheet from "../../o_spreadsheet_loader";
import PivotDataSource from "../../helpers/pivot_data_source";

import { getFirstPivotFunction } from "../../helpers/odoo_functions_helpers";
import { getMaxObjectId } from "../../helpers/helpers";

const { astToFormula } = spreadsheet;

export default class PivotPlugin extends spreadsheet.CorePlugin {
    constructor(getters, history, range, dispatch, config) {
        super(getters, history, range, dispatch, config);
        /** @type {Object.<string, SpreadsheetPivot>} */
        this.pivots = {};
        this.dataSources = config.dataSources;
        this.rpc = config.evalContext.env ? config.evalContext.env.delayedRPC : undefined;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_PIVOT": {
                const pivots = { ...this.pivots };
                pivots[cmd.pivot.id] = cmd.pivot;
                this.history.update("pivots", pivots);
                this._addPivotSource(cmd.pivot.id);
                break;
            }
            case "ADD_PIVOT_FORMULA":
                this.dispatch("UPDATE_CELL", {
                    sheetId: cmd.sheetId,
                    col: cmd.col,
                    row: cmd.row,
                    content: `=${cmd.formula}("${cmd.args
                        .map((arg) => arg.toString().replace(/"/g, '\\"'))
                        .join('","')}")`,
                });
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Retrieve the next available id for a new pivot
     *
     * @returns {string} id
     */
    getNextPivotId() {
        return (getMaxObjectId(this.pivots) + 1).toString();
    }

    /**
     * Get the colGroupBys of a pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {Array<string>}
     */
    getPivotColGroupBys(pivotId) {
        return this._getPivot(pivotId).colGroupBys;
    }

    /**
     * Get the domain of a pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {Array}
     */
    getPivotDomain(pivotId) {
        return this._getPivot(pivotId).domain;
    }

    /**
     * Get the pivot definition
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {SpreadsheetPivotForRPC}
     */
    getPivotForRPC(pivotId) {
        const pivot = this._getPivot(pivotId);
        return {
            colGroupBys: pivot.colGroupBys,
            context: pivot.context,
            domain: pivot.domain,
            measures: pivot.measures,
            model: pivot.model,
            rowGroupBys: pivot.rowGroupBys,
        };
    }

    /**
     * Get the id of the pivot at the given position. Returns undefined if there
     * is no pivot at this position
     *
     * @param {string} sheetId Id of the sheet
     * @param {number} col Index of the col
     * @param {number} row Index of the row
     *
     * @returns {string|undefined}
     */
    getPivotIdFromPosition(sheetId, col, row) {
        const cell = this.getters.getCell(sheetId, col, row);
        if (cell && cell.isFormula()) {
            const pivotFunction = getFirstPivotFunction(cell.normalizedText);
            if (pivotFunction) {
                const dependencies = {
                    ...cell.dependencies,
                    references: cell.dependencies.references.map((range) => this.getters.getRangeString(range, range.sheetId))
                }
                const content = astToFormula(pivotFunction.args[0], dependencies);
                const formula = this.getters.buildFormulaContent(sheetId, content, cell.dependencies);
                return this.getters.evaluateFormula(formula).toString();
            }
        }
        return undefined;
    }

    /**
     * Retrieve all the pivot ids
     *
     * @returns {Array<string>}
     */
    getPivotIds() {
        return Object.keys(this.pivots);
    }

    /**
     * Get the measures of a pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {Array<string>}
     */
    getPivotMeasures(pivotId) {
        return this._getPivot(pivotId).measures;
    }

    /**
     * Get the technical name of the model of a pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {string}
     */
    getPivotModel(pivotId) {
        return this._getPivot(pivotId).model;
    }

    /**
     * Get the rowGroupBys of a pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {Array<string>}
     */
    getPivotRowGroupBys(pivotId) {
        return this._getPivot(pivotId).rowGroupBys;
    }

    /**
     * Check if an id is an id of an existing pivot
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {boolean}
     */
    isExistingPivot(pivotId) {
        return pivotId in this.pivots;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Retrieve the pivot associated to the given Id
     *
     * @param {string} pivotId Id of the pivot
     *
     * @returns {SpreadsheetPivot} Pivot
     */
    _getPivot(pivotId) {
        return this.pivots[pivotId];
    }

    /**
     * Adds the data source information to the local state
     *
     * @param {string} pivotId Id of the pivot
     *
     * @private
     */
     _addPivotSource(pivotId) {
        const definition = this.getPivotForRPC(pivotId);
        this.dataSources.add(
            `PIVOT_${pivotId}`,
            new PivotDataSource({
                rpc: this.rpc,
                definition,
                model: definition.model,
            })
        );
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * Import the pivots
     *
     * @param {Object} data
     */
    import(data) {
        if (data.pivots) {
            this.pivots = JSON.parse(JSON.stringify(data.pivots));
        }
        for (const pivotId in this.pivots){
            this._addPivotSource(pivotId);
        }
    }
    /**
     * Export the pivots
     *
     * @param {Object} data
     */
    export(data) {
        data.pivots = JSON.parse(JSON.stringify(this.pivots));
    }
}

PivotPlugin.modes = ["normal", "headless"];
PivotPlugin.getters = [
    "getNextPivotId",
    "getPivotColGroupBys",
    "getPivotDomain",
    "getPivotForRPC",
    "getPivotIdFromPosition",
    "getPivotIds",
    "getPivotModel",
    "getPivotMeasures",
    "getPivotRowGroupBys",
    "isExistingPivot",
];
