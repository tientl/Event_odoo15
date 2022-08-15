/** @odoo-module */
/* global moment */

/**
 * @typedef {Object} GlobalFilter
 * @property {string} id
 * @property {string} label
 * @property {string} type "text" | "date" | "relation"
 * @property {string|undefined} rangeType "year" | "month" | "quarter"
 * @property {Object} pivotFields
 * @property {Object} listFields
 * @property {string|Array<string>|Object} defaultValue Default Value
 * @property {number} [modelID] ID of the related model
 * @property {string} [modelName] Name of the related model
 */

import spreadsheet from "../../o_spreadsheet_loader";
import CommandResult from "../cancelled_reason";
import { checkFiltersTypeValueCombination } from "../../helpers/helpers";

const { UuidGenerator } = spreadsheet.helpers;
const uuidGenerator = new UuidGenerator();

export default class FiltersPlugin extends spreadsheet.CorePlugin {
    constructor() {
        super(...arguments);
        /** @type {Object.<string, GlobalFilter>} */
        this.globalFilters = {};
    }

    /**
     * Check if the given command can be dispatched
     *
     * @param {Object} cmd Command
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "EDIT_GLOBAL_FILTER":
                if (!this.getGlobalFilter(cmd.id)) {
                    return CommandResult.FilterNotFound;
                } else if (this._isDuplicatedLabel(cmd.id, cmd.filter.label)) {
                    return CommandResult.DuplicatedFilterLabel;
                }
                return checkFiltersTypeValueCombination(cmd.filter.type, cmd.filter.defaultValue);
            case "REMOVE_GLOBAL_FILTER":
                if (!this.getGlobalFilter(cmd.id)) {
                    return CommandResult.FilterNotFound;
                }
                break;
            case "ADD_GLOBAL_FILTER":
                if (this._isDuplicatedLabel(cmd.id, cmd.filter.label)) {
                    return CommandResult.DuplicatedFilterLabel;
                }
                return checkFiltersTypeValueCombination(cmd.filter.type, cmd.filter.defaultValue);
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
            case "ADD_GLOBAL_FILTER":
                this._addGlobalFilter(cmd.filter);
                break;
            case "EDIT_GLOBAL_FILTER":
                this._editGlobalFilter(cmd.id, cmd.filter);
                break;
            case "REMOVE_GLOBAL_FILTER":
                this._removeGlobalFilter(cmd.id);
                break;
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Retrieve the global filter with the given id
     *
     * @param {string} id
     * @returns {GlobalFilter|undefined} Global filter
     */
    getGlobalFilter(id) {
        return this.globalFilters[id];
    }

    /**
     * Get the field name on which the global filter is applied for a pivot
     *
     * @param {string} filterId Id of the filter
     * @param {string} pivotId Id of the pivot
     * @returns {string|undefined}
     */
    getGlobalFilterFieldPivot(filterId, pivotId) {
        return this.getGlobalFilter(filterId).pivotFields[pivotId];
    }

    /**
     * Get the field name on which the global filter is applied for a list
     *
     * @param {string} filterId Id of the filter
     * @param {string} listId Id of the list
     * @returns {string|undefined}
     */
    getGlobalFilterFieldList(filterId, listId) {
        return this.getGlobalFilter(filterId).listFields[listId];
    }

    /**
     * Get the global filter with the given name
     *
     * @param {string} label Label
     *
     * @returns {GlobalFilter|undefined}
     */
    getGlobalFilterLabel(label) {
        return this.getGlobalFilters().find((filter) => filter.label === label);
    }

    /**
     * Retrieve all the global filters
     *
     * @returns {Array<GlobalFilter>} Array of Global filters
     */
    getGlobalFilters() {
        return Object.values(this.globalFilters);
    }

    /**
     * Get the default value of a global filter
     *
     * @param {string} id Id of the filter
     *
     * @returns {string|Array<string>|Object}
     */
    getGlobalFilterDefaultValue(id) {
        return this.getGlobalFilter(id).defaultValue;
    }

    // ---------------------------------------------------------------------
    // Handlers
    // ---------------------------------------------------------------------

    /**
     * Add a global filter
     *
     * @param {GlobalFilter} filter
     */
    _addGlobalFilter(filter) {
        const globalFilters = { ...this.globalFilters };
        globalFilters[filter.id] = filter;
        this.history.update("globalFilters", globalFilters);
    }
    /**
     * Remove a global filter
     *
     * @param {number} id Id of the filter to remove
     */
    _removeGlobalFilter(id) {
        const globalFilters = { ...this.globalFilters };
        delete globalFilters[id];
        this.history.update("globalFilters", globalFilters);
    }
    /**
     * Edit a global filter
     *
     * @param {number} id Id of the filter to update
     * @param {GlobalFilter} newFilter
     */
    _editGlobalFilter(id, newFilter) {
        const currentLabel = this.getGlobalFilter(id).label;
        const globalFilters = { ...this.globalFilters };
        newFilter.id = id;
        globalFilters[id] = newFilter;
        this.history.update("globalFilters", globalFilters);
        const newLabel = this.getGlobalFilter(id).label;
        if (currentLabel !== newLabel) {
            this._updateFilterLabelInFormulas(currentLabel, newLabel);
        }
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * Import the filters
     *
     * @param {Object} data
     */
    import(data) {
        if (data.globalFilters) {
            for (const globalFilter of data.globalFilters) {
                globalFilter.pivotFields = globalFilter.fields;
                this.globalFilters[globalFilter.id] = globalFilter;
                if (!this.globalFilters[globalFilter.id].listFields) {
                    this.globalFilters[globalFilter.id].listFields = {};
                }
            }
        }
    }
    /**
     * Export the filters
     *
     * @param {Object} data
     */
    export(data) {
        data.globalFilters = this.getGlobalFilters().map((filter) => ({
            ...filter,
            fields: filter.pivotFields,
        }));
    }

    /**
     * Adds all active filters (and their values) at the time of export in a dedicated sheet
     *
     * @param {Object} data
     */
    exportForExcel(data) {
        if (this.getGlobalFilters().length === 0) {
            return;
        }
        /**
         * In order to get the evaluate data of a filter (the value), we have to
         * make some calls to UI plugins. In order to avoid issues when the
         * spreadsheet is instantiated in headless mode, we introduce the
         * following check
         */
        if (!("getActiveSheetId" in this.getters)) {
            return;
        }
        const styles = Object.entries(data.styles);
        let titleStyleId =
            styles.findIndex((el) => JSON.stringify(el[1]) === JSON.stringify({ bold: true })) + 1;

        if (titleStyleId <= 0) {
            titleStyleId = styles.length + 1;
            data.styles[styles.length + 1] = { bold: true };
        }

        const cells = {};
        cells["A1"] = { content: "Filter", style: titleStyleId };
        cells["B1"] = { content: "Value", style: titleStyleId };
        let row = 2;
        for (const filter of this.getGlobalFilters()) {
            const content = this.getters.getFilterDisplayValue(filter.label);
            cells[`A${row}`] = { content: filter.label };
            cells[`B${row}`] = { content };
            row++;
        }
        data.sheets.push({
            id: uuidGenerator.uuidv4(),
            name: "Active Filters",
            cells,
            colNumber: 2,
            rowNumber: this.getGlobalFilters().length + 1,
            cols: {},
            rows: {},
            merges: [],
            figures: [],
            conditionalFormats: [],
            charts: [],
        });
    }

    // ---------------------------------------------------------------------
    // Global filters
    // ---------------------------------------------------------------------

    /**
     * Update all FILTER.VALUE formulas to reference a filter
     * by its new label.
     *
     * @param {string} currentLabel
     * @param {string} newLabel
     */
    _updateFilterLabelInFormulas(currentLabel, newLabel) {
        const sheets = this.getters.getSheets();
        currentLabel = currentLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        for (let sheet of sheets) {
            for (let cell of Object.values(this.getters.getCells(sheet.id))) {
                if (cell.isFormula()) {
                    const newContent = cell.content.replace(
                        new RegExp(`FILTER\\.VALUE\\(\\s*"${currentLabel}"\\s*\\)`, "g"),
                        `FILTER.VALUE("${newLabel}")`
                    );
                    if (newContent !== cell.content) {
                        const { col, row } = this.getters.getCellPosition(cell.id);
                        this.dispatch("UPDATE_CELL", {
                            sheetId: sheet.id,
                            content: newContent,
                            col,
                            row,
                        });
                    }
                }
            }
        }
    }

    /**
     * Return true if the label is duplicated
     *
     * @param {string | undefined} filterId
     * @param {string} label
     * @returns {boolean}
     */
    _isDuplicatedLabel(filterId, label) {
        return (
            this.getGlobalFilters().findIndex(
                (filter) => (!filterId || filter.id !== filterId) && filter.label === label
            ) > -1
        );
    }
}

FiltersPlugin.modes = ["normal", "headless"];
FiltersPlugin.getters = [
    "getGlobalFilter",
    "getGlobalFilters",
    "getGlobalFilterDefaultValue",
    "getGlobalFilterLabel",
    "getGlobalFilterFieldPivot",
    "getGlobalFilterFieldList",
];
