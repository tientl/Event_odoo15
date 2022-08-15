/** @odoo-module */

import spreadsheet from "../../o_spreadsheet_loader";
import ListDataSource from "../../helpers/list_data_source";

import CommandResult from "../cancelled_reason";
import { getFirstListFunction } from "../../helpers/odoo_functions_helpers";
import { getMaxObjectId } from "../../helpers/helpers";

const { astToFormula } = spreadsheet;

/**
 * @typedef {Object} SpreadsheetList
 * @property {Array<string>} columns
 * @property {Object} context
 * @property {Array<Array<string>>} domain
 * @property {string} id The id of the list
 * @property {string} model The technical name of the model we are listing
 * @property {Array<string>} orderBy
 *
 * @typedef {Object} SpreadsheetListForRPC
 * @property {Array<string>} columns
 * @property {Object} context
 * @property {Array<Array<string>>} domain
 * @property {string} model
 * @property {Array<string>} orderBy
 */
export default class ListPlugin extends spreadsheet.CorePlugin {
    constructor(getters, history, range, dispatch, config) {
        super(getters, history, range, dispatch, config);
        this.lists = {};
        this.dataSources = config.dataSources;
        this.rpc = config.evalContext.env ? config.evalContext.env.delayedRPC : undefined;
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "ADD_ODOO_LIST":
                if (this.lists[cmd.list.id]) {
                    return CommandResult.ListIdDuplicated;
                }
                break;
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_ODOO_LIST": {
                const lists = { ...this.lists };
                lists[cmd.list.id] = cmd.list;
                this.history.update("lists", lists);
                this._createListSource(cmd.list.id);
                break;
            }

            case "ADD_ODOO_LIST_FORMULA":
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
     * Get the columns of the list
     * @param {string} listId Id of the list
     *
     * @returns {Array<string>} columns
     */
    getListColumns(listId) {
        return this._getList(listId).columns;
    }

    /**
     * Get the domain of a list
     * @param {string} listId Id of the list
     *
     * @returns {Array<Array<string>>} domain
     */
    getListDomain(listId) {
        return this._getList(listId).domain;
    }

    /**
     * Get the id of the list at the given position. Returns undefined if there
     * is no list at this position
     *
     * @param {string} sheetId Id of the sheet
     * @param {number} col Index of the col
     * @param {number} row Index of the row
     *
     * @returns {string|undefined}
     */
    getListIdFromPosition(sheetId, col, row) {
        const cell = this.getters.getCell(sheetId, col, row);
        if (cell && cell.isFormula()) {
            const listFunction = getFirstListFunction(cell.normalizedText);
            if (listFunction) {
                const dependencies = {
                    ...cell.dependencies,
                    references: cell.dependencies.references.map((range) => this.getters.getRangeString(range, range.sheetId))
                }
                const content = astToFormula(listFunction.args[0], dependencies);
                const formula = this.getters.buildFormulaContent(sheetId, content, cell.dependencies);
                return this.getters.evaluateFormula(formula).toString();
            }
        }
        return undefined;
    }

    /**
     * Retrieve all the list ids
     *
     * @returns {Array<string>} list ids
     */
    getListIds() {
        return Object.keys(this.lists);
    }

    /**
     * Retrieve the technical model name of a list
     * @param {string} listId Id of the list
     *
     * @returns {string} technical model name
     */
    getListModel(listId) {
        return this._getList(listId).model;
    }

    /**
     *
     * @param {string} listId Id of the list
     *
     * @returns {SpreadsheetListForRPC}
     */
    getListForRPC(listId) {
        const list = this._getList(listId);
        return {
            columns: list.columns,
            context: list.context,
            domain: list.domain,
            model: list.model,
            orderBy: list.orderBy,
        };
    }

    /**
     * Get the order by of a list
     * @param {string} listId Id of the list
     *
     * @returns {Array<string>} orderBy
     */
    getListOrderBy(listId) {
        return this._getList(listId).orderBy;
    }

    /**
     * Retrieve the next available id for a new list
     *
     * @returns {string} id
     */
    getNextListId() {
        return (getMaxObjectId(this.lists) + 1).toString();
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * Import the lists
     *
     * @param {Object} data
     */
    import(data) {
        if (data.lists) {
            this.lists = JSON.parse(JSON.stringify(data.lists));
        }
        for (const listId in this.lists) {
            this._createListSource(listId);
        }
    }
    /**
     * Export the lists
     *
     * @param {Object} data
     */
    export(data) {
        data.lists = JSON.parse(JSON.stringify(this.lists));
    }

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     * Retrieve the list associated to the given Id
     *
     * @param {string} listId Id of the list
     *
     * @returns {SpreadsheetList} List
     */
    _getList(listId) {
        if (!(listId in this.lists)) {
            throw new Error(`There is not list with the id "${listId}"`);
        }
        return this.lists[listId];
    }

    /**
     * Creates a list source for the newly inserted list
     * @param {number} listId Id of the list
     */
    _createListSource(listId) {
        const definition = this.getListForRPC(listId);
        this.dataSources.add(
            `LIST_${listId}`,
            new ListDataSource({
                rpc: this.rpc,
                definition,
                model: definition.model,
            })
        );
    }
}

ListPlugin.modes = ["normal", "headless"];
ListPlugin.getters = [
    "getListColumns",
    "getListDomain",
    "getListIdFromPosition",
    "getListIds",
    "getListForRPC",
    "getListModel",
    "getListOrderBy",
    "getNextListId",
];
