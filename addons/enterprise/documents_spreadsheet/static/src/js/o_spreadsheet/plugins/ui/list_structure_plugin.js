/** @odoo-module */
import spreadsheet from "../../o_spreadsheet_loader";
import Domain from "web.Domain";
import pyUtils from "web.py_utils";
import ListDataSource from "../../helpers/list_data_source";

import { TOP_LEVEL_STYLE } from "../../constants";

/**
 * @typedef {import("../core/list_plugin").SpreadsheetListForRPC} SpreadsheetListForRPC
 * @typedef {import("../core/list_plugin").SpreadsheetList} SpreadsheetList
 * @typedef {import("../../helpers/basic_data_source").Field} Field
 */

export default class ListStructurePlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        this.rpc = config.evalContext.env ? config.evalContext.env.delayedRPC : undefined;
        this.dataSources = config.dataSources;
        /** @type {string} */
        this.selectedListId = undefined;
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "START":
                this._refreshOdooLists();
                break;
            case "BUILD_ODOO_LIST":
                this._handleBuildList(
                    cmd.sheetId,
                    cmd.anchor,
                    cmd.linesNumber,
                    cmd.list,
                    cmd.types
                );
                break;
            case "REBUILD_ODOO_LIST": {
                let types = {};
                const dataSource = this._getDataSource(cmd.listId);
                if (dataSource.getMetadataSync()) {
                    types = this.getters.getListColumns(cmd.listId).reduce((acc, current) => {
                        const field = dataSource.getField(current);
                        acc[current] = field.type;
                        return acc;
                    }, {});
                }
                this._buildList(cmd.sheetId, cmd.anchor, cmd.listId, cmd.linesNumber, types);
                break;
            }
            case "SELECT_ODOO_LIST":
                this._selectList(cmd.listId);
                break;
            case "REFRESH_ODOO_LIST":
                this._refreshOdooList(cmd.listId);
                break;
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooLists();
                break;
            case "ADD_LIST_DOMAIN":
                this._addDomain(cmd.id, cmd.domain, cmd.refresh);
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Add an additional domain to a pivot
     *
     * @private
     *
     * @param {string} listId pivot id
     * @param {Array<Array<any>>} domain
     * @param {boolean} refresh whether the cache should be reloaded or not
     */
    _addDomain(listId, domain, refresh = true) {
        domain = pyUtils.assembleDomains(
            [
                Domain.prototype.arrayToString(this.getters.getListDomain(listId)),
                Domain.prototype.arrayToString(domain),
            ],
            "AND"
        );
        const computedDomain = pyUtils.eval("domain", domain, {});
        this._getDataSource(listId).setComputedDomain(computedDomain);
        if (refresh) {
            this._refreshOdooList(listId);
        }
    }
    /**
     * Build an Odoo List
     * @param {string} sheetId Sheet id on which the list is built
     * @param {[number,number]} anchor [col,row], the top-left of the list
     * @param {number} linesNumber Number of lines of the list
     * @param {SpreadsheetList} list
     * @param {Object.<string, Field>} types Types of the columns name, used to
     * format
     */
    _handleBuildList(sheetId, anchor, linesNumber, list, types) {
        this.dispatch("ADD_ODOO_LIST", { list });
        this._buildList(sheetId, anchor, list.id, linesNumber, types);
        const cols = [];
        for (let col = anchor[0]; col < anchor[0] + list.columns.length; col++) {
            cols.push(col);
        }
        this.dispatch("EVALUATE_CELLS", { sheetId: this.getters.getActiveSheetId() });
        const dataSource = this._getDataSource(list.id);
        dataSource.on("data-loaded", this, () => {
            this.dispatch("AUTORESIZE_COLUMNS", {
                sheetId,
                cols,
            });
            dataSource.off("data-loaded", this);
        });
    }

    /**
     * Refresh the cache of a list
     * @param {string} listId Id of the list
     */
    _refreshOdooList(listId) {
        this.dataSources.get(`LIST_${listId}`).get({ forceFetch: true });
    }

    /**
     * Refresh the cache of all the lists
     */
    _refreshOdooLists() {
        for (const listId of this.getters.getListIds()) {
            this._refreshOdooList(listId);
        }
    }

    /**
     * Select the given list id. If the id is undefined, it unselect the list.
     * @param {number|undefined} listId Id of the list, or undefined to remove
     *                                  the selected list
     */
    _selectList(listId) {
        this.selectedListId = listId;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get the computed domain of a list
     *
     * @param {string} listId Id of the list
     * @returns {Array}
     */
    getListComputedDomain(listId) {
        return this._getDataSource(listId).getComputedDomain();
    }

    /**
     * Get the display name of the list
     *
     * @param {string} listId List Id
     *
     * @returns {string}
     */
    getListDisplayName(listId) {
        const model = this.getListModelDisplayName(listId);
        return `(#${listId}) ${model}`;
    }

    /**
     * Get the field with the given field name
     *
     * @param {string} listId Id of the list
     * @param {string} fieldName Field name
     *
     * @returns {Field|undefined}
     */
    getListField(listId, fieldName) {
        return this._getDataSource(listId).getField(fieldName);
    }

    /**
     * Get the display name of a field. If the display name is not yet available,
     * returns the technical name
     * @param {string} listId Id of the list
     * @param {string} fieldName Technical name of the field
     *
     * @returns {string}
     */
    getListFieldName(listId, fieldName) {
        return this._getDataSource(listId).getFieldName(fieldName) || fieldName;
    }

    /**
     * Get the field definitions of a list
     * @param {string} listId Id of the list
     * @returns {Object.<string, Field>}
     */
    getListFields(listId) {
        return this._getDataSource(listId).getFields();
    }

    /**
     * Get the header name of a field
     * @param {string} listId Id of the list
     * @param {string} fieldName Field Name
     *
     * @returns {string|undefined}
     */
    getListHeader(listId, fieldName) {
        return this._getDataSource(listId).getFieldName(fieldName);
    }

    /**
     * Get the last update date of the list
     * @param {string} listId Id of the list
     *
     * @returns {number|undefined}
     */
    getListLastUpdate(listId) {
        return this._getDataSource(listId).getLastUpdate();
    }

    /**
     * Get the display name of the model of a list. If the display name is not
     * available, returns the technical name
     * @param {string} listId Id of the list
     *
     * @returns {string}
     */
    getListModelDisplayName(listId) {
        return this._getDataSource(listId).getModelName() || this.getters.getListModel(listId);
    }

    /**
     * Get the value for a field of a record in the list
     * @param {string} listId Id of the list
     * @param {number} position Position of the record in the list
     * @param {string} fieldName Field Name
     *
     * @returns {string|undefined}
     */
    getListValue(listId, position, fieldName) {
        return this._getDataSource(listId).getRecordField(position, fieldName);
    }

    /**
     * Get the currently selected list id
     * @returns {number|undefined} Id of the list, undefined if no one is selected
     */
    getSelectedListId() {
        return this.selectedListId;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Build an Odoo List
     * @param {string} sheetId Id of the sheet
     * @param {[number,number]} anchor Top-left cell in which the list should be inserted
     * @param {string} listId Id of the list
     * @param {number} linesNumber Number of records to insert
     * @param {Object.<string, Field>} types Types of the columns name, used to
     * format
     */
    _buildList(sheetId, anchor, listId, linesNumber, types) {
        const columns = this.getters.getListColumns(listId);
        let [col, row] = anchor;
        this._resizeSheet(sheetId, columns.length, linesNumber + 1, anchor);
        for (const field_name of columns) {
            this.dispatch("ADD_ODOO_LIST_FORMULA", {
                col,
                row,
                sheetId,
                formula: "LIST.HEADER",
                args: [listId, field_name],
            });
            col++;
        }
        row++;
        for (let i = 1; i <= linesNumber; i++) {
            col = anchor[0];
            for (const field_name of columns) {
                this.dispatch("ADD_ODOO_LIST_FORMULA", {
                    col,
                    row,
                    sheetId,
                    formula: "LIST",
                    args: [listId, i, field_name],
                });
                col++;
            }
            row++;
        }
        this.dispatch("SET_FORMATTING", {
            sheetId,
            style: TOP_LEVEL_STYLE,
            target: [
                {
                    top: anchor[1],
                    bottom: anchor[1],
                    left: anchor[0],
                    right: anchor[0] + columns.length - 1,
                },
            ],
        });
        col = anchor[0];
        for (const field_name of columns) {
            const type = types[field_name];
            if (["integer", "float", "monetary"].includes(type)) {
                this.dispatch("SET_FORMATTING", {
                    sheetId,
                    format: "#,##0.00",
                    target: [
                        {
                            top: anchor[1],
                            bottom: anchor[1] + linesNumber,
                            left: col,
                            right: col,
                        },
                    ],
                });
            }
            col++;
        }
    }

    /**
     * Get the dataSource object associated to the given listId
     * @param {string} listId ID of the list
     * @returns {ListDataSource}
     */
    _getDataSource(listId) {
        return this.dataSources.get(`LIST_${listId}`);
    }

    /**
     * Resize the sheet to match the size of the listing. Columns and/or rows
     * could be added to be sure to insert the entire sheet.
     *
     * @param {string} sheetId Id of the sheet
     * @param {number} columns Number of columns of the list
     * @param {number} rows Number of rows of the list
     * @param {[number,number]} anchor Anchor of the list [col,row]
     */
    _resizeSheet(sheetId, columns, rows, anchor) {
        const sheet = this.getters.getSheet(sheetId);
        const numberCols = sheet.cols.length;
        const deltaCol = numberCols - anchor[0];
        if (deltaCol < columns) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "COL",
                base: numberCols - 1,
                sheetId: sheetId,
                quantity: columns - deltaCol,
                position: "after",
            });
        }
        const numberRows = sheet.rows.length;
        const deltaRow = numberRows - anchor[1];
        if (deltaRow < rows) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "ROW",
                base: numberRows - 1,
                sheetId: sheetId,
                quantity: rows - deltaRow,
                position: "after",
            });
        }
    }
}

ListStructurePlugin.modes = ["normal", "headless"];
ListStructurePlugin.getters = [
    "getListComputedDomain",
    "getListDisplayName",
    "getListFieldName",
    "getListFields",
    "getListField",
    "getListHeader",
    "getListLastUpdate",
    "getListModelDisplayName",
    "getListValue",
    "getSelectedListId",
];
