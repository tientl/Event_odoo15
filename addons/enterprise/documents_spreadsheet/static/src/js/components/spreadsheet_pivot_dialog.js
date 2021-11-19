odoo.define("documents_spreadsheet.PivotDialog", function (require) {
    "use strict";
    const core = require("web.core");
    const spreadsheet = require("documents_spreadsheet.spreadsheet_extended");
    const PivotDialogTable = require("documents_spreadsheet.PivotDialogTable");
    const _t = core._t;
    const { useState } = owl.hooks;
    const formatDecimal = spreadsheet.helpers.formatDecimal;

    /**
     * @typedef {Object} PivotDialogColumn
     * @property {string} formula Pivot formula
     * @property {string} value Pivot value of the formula
     * @property {number} span Size of col-span
     * @property {number} position Position of the column
     * @property {boolean} isMissing True if the value is missing from the sheet
     * @property {string} style Style of the column
     */

    /**
     * @typedef {Object} PivotDialogRow
     * @property {Array<string>} args Args of the pivot formula
     * @property {string} formula Pivot formula
     * @property {string} value Pivot value of the formula
     * @property {boolean} isMissing True if the value is missing from the sheet
     * @property {string} style Style of the column
     */

    /**
     * @typedef {Object} PivotDialogValue
     * @property {Object} args
     * @property {string} args.formula Pivot formula
     * @property {string} args.value Pivot value of the formula
     * @property {boolean} isMissing True if the value is missing from the sheet
     */

    class PivotDialog extends owl.Component {
        constructor() {
            super(...arguments);
            this.state = useState({
                showMissingValuesOnly: false,
            });
        }

        async willStart() {
            await this.getters.waitForPivotDataReady(this.pivotId);
            this.data = {
                columns: this._buildColHeaders(),
                rows: this._buildRowHeaders(),
                values: this._buildValues(),
            };
        }

        get pivotId() {
            return this.props.pivotId;
        }

        get getters() {
            return this.props.getters;
        }

        /**
         * This method always returns the PivotCache, as we ensure that it's
         * loaded in the willStart
         *
         * @returns {PivotCache}
         */
        get pivotData() {
            return this.getters.getPivotStructureData(this.pivotId);
        }

        // ---------------------------------------------------------------------
        // Missing values building
        // ---------------------------------------------------------------------

        /**
         * Retrieve the data to display in the Pivot Table
         * In the case when showMissingValuesOnly is false, the returned value
         * is the complete data
         * In the case when showMissingValuesOnly is true, the returned value is
         * the data which contains only missing values in the rows and cols. In
         * the rows, we also return the parent rows of rows which contains missing
         * values, to give context to the user.
         *
         * @returns {Object} { columns, rows, values }
         */
        getTableData() {
            if (!this.state.showMissingValuesOnly) {
                return this.data;
            }
            const colIndexes = this._getColumnsIndexes();
            const rowIndexes = this._getRowsIndexes();
            const columns = this._buildColumnsMissing(colIndexes);
            const rows = this._buildRowsMissing(rowIndexes);
            const values = this._buildValuesMissing(colIndexes, rowIndexes);
            return { columns, rows, values };
        }
        /**
         * Retrieve the parents of the given row
         * ex:
         *  Australia
         *    January
         *    February
         * The parent of "January" is "Australia"
         *
         * @private
         * @param {number} index Index of the row
         * @returns {Array<number>}
         */
        _addRecursiveRow(index) {
            const row = this.pivotData.getRowValues(index).slice();
            if (row.length <= 1) {
                return [index];
            }
            row.pop();
            const parentRowIndex = this.pivotData.getRowIndex(row);
            return [index].concat(this._addRecursiveRow(parentRowIndex));
        }
        /**
         * Create the columns to be used, based on the indexes of the columns in
         * which a missing value is present
         *
         * @private
         * @param {Array<number>} indexes Indexes of columns with a missing value
         * @returns {Array<Array<PivotDialogColumn>>}
         */
        _buildColumnsMissing(indexes) {
            // columnsMap explode the columns in an array of array of the same
            // size with the index of each columns, repeated 'span' times.
            // ex:
            //  | A     | B |
            //  | 1 | 2 | 3 |
            // => [
            //      [0, 0, 1]
            //      [0, 1, 2]
            //    ]
            const columnsMap = [];
            for (let column of this.data.columns) {
                const columnMap = [];
                for (let index in column) {
                    for (let i = 0; i < column[index].span; i++) {
                        columnMap.push(index);
                    }
                }
                columnsMap.push(columnMap);
            }
            // Remove the columns that are not present in indexes
            for (let i = columnsMap[columnsMap.length - 1].length; i >= 0; i--) {
                if (!indexes.includes(i)) {
                    for (let columnMap of columnsMap) {
                        columnMap.splice(i, 1);
                    }
                }
            }
            // Build the columns
            const columns = [];
            for (let mapIndex in columnsMap) {
                const column = [];
                let index = undefined;
                let span = 1;
                for (let i = 0; i < columnsMap[mapIndex].length; i++) {
                    if (index !== columnsMap[mapIndex][i]) {
                        if (index) {
                            column.push(
                                Object.assign({}, this.data.columns[mapIndex][index], { span })
                            );
                        }
                        index = columnsMap[mapIndex][i];
                        span = 1;
                    } else {
                        span++;
                    }
                }
                if (index) {
                    column.push(Object.assign({}, this.data.columns[mapIndex][index], { span }));
                }
                columns.push(column);
            }
            return columns;
        }
        /**
         * Create the rows to be used, based on the indexes of the rows in
         * which a missing value is present.
         *
         * @private
         * @param {Array<number>} indexes Indexes of rows with a missing value
         * @returns {Array<PivotDialogRow>}
         */
        _buildRowsMissing(indexes) {
            return indexes.map((index) => this.data.rows[index]);
        }
        /**
         * Create the value to be used, based on the indexes of the columns and
         * rows in which a missing value is present.
         *
         * @private
         * @param {Array<number>} colIndexes Indexes of columns with a missing value
         * @param {Array<number>} rowIndexes Indexes of rows with a missing value
         * @returns {Array<PivotDialogValue}
         */
        _buildValuesMissing(colIndexes, rowIndexes) {
            const values = colIndexes.map(() => []);
            for (let row of rowIndexes) {
                for (let col in colIndexes) {
                    values[col].push(this.data.values[colIndexes[col]][row]);
                }
            }
            return values;
        }
        /**
         * Get the indexes of the columns in which a missing value is present
         * @private
         * @returns {Array<number>}
         */
        _getColumnsIndexes() {
            const indexes = new Set();
            for (let i = 0; i < this.data.columns.length; i++) {
                const exploded = [];
                for (let y = 0; y < this.data.columns[i].length; y++) {
                    for (let x = 0; x < this.data.columns[i][y].span; x++) {
                        exploded.push(this.data.columns[i][y]);
                    }
                }
                for (let y = 0; y < exploded.length; y++) {
                    if (exploded[y].isMissing) {
                        indexes.add(y);
                    }
                }
            }
            for (let i = 0; i < this.data.columns[this.data.columns.length - 1].length; i++) {
                const values = this.data.values[i];
                if (values.find((x) => x.isMissing)) {
                    indexes.add(i);
                }
            }
            return Array.from(indexes).sort((a, b) => a - b);
        }
        /**
         * Get the indexes of the rows in which a missing value is present
         * @private
         * @returns {Array<number>}
         */
        _getRowsIndexes() {
            const rowIndexes = new Set();
            for (let i = 0; i < this.data.rows.length; i++) {
                if (this.data.rows[i].isMissing) {
                    rowIndexes.add(i);
                }
                for (let col of this.data.values) {
                    if (col[i].isMissing) {
                        this._addRecursiveRow(i).forEach((x) => rowIndexes.add(x));
                    }
                }
            }
            return Array.from(rowIndexes).sort((a, b) => a - b);
        }

        // ---------------------------------------------------------------------
        // Data table creation
        // ---------------------------------------------------------------------

        /**
         * Create a cell information from the args of the pivot formula
         *
         * @private
         * @param {Array<string>} args Args of the pivot formula
         * @returns {Object} { value, formula }
         */
        _buildCell(args) {
            const formula = `=PIVOT("${args.join('","')}")`;
            const measure = args[1];
            const measures = this.getters.getPivotMeasures(this.pivotId);
            const operator = measures.filter((m) => m.field === measure)[0].operator;
            args.splice(0, 2);
            const domain = args.map((x) => x.toString());
            const value = this.pivotData.getMeasureValue(measure, operator, domain);
            return { value: this._formatValue(value), formula };
        }
        /**
         * Create the columns headers of the Pivot
         *
         * @private
         * @returns {Array<Array<PivotDialogColumn>>}
         */
        _buildColHeaders() {
            const levels = this.pivotData.getColGroupByLevels();
            const headers = [];

            let length =
                this.pivotData.getTopHeaderCount() -
                this.getters.getPivotMeasures(this.pivotId).length;
            if (length === 0) {
                length = this.pivotData.getTopHeaderCount();
            }
            for (let i = 0; i < length; i++) {
                for (let level = 0; level <= levels; level++) {
                    const pivotArgs = [];
                    const values = this.pivotData.getColGroupHierarchy(i, level);
                    for (const index in values) {
                        pivotArgs.push(this.pivotData.getColLevelIdentifier(index));
                        pivotArgs.push(values[index]);
                    }
                    const isMissing = !this.pivotData.isUsedHeader(pivotArgs);
                    pivotArgs.unshift(this.pivotId);
                    if (headers[level]) {
                        headers[level].push({ args: pivotArgs, isMissing });
                    } else {
                        headers[level] = [{ args: pivotArgs, isMissing }];
                    }
                }
            }
            for (let i = length; i < this.pivotData.getTopHeaderCount(); i++) {
                let isMissing = !this.pivotData.isUsedHeader([]);
                headers[headers.length - 2].push({ args: [this.pivotId], isMissing });
                const args = ["measure", this.pivotData.getColGroupHierarchy(i, 1)[0]];
                isMissing = !this.pivotData.isUsedHeader(args);
                headers[headers.length - 1].push({ args: [this.pivotId, ...args], isMissing });
            }
            return headers.map((row) => {
                const reducedRow = row.reduce((acc, curr) => {
                    const val = curr.args.join('","');
                    if (acc[val] === undefined) {
                        acc[val] = {
                            count: 0,
                            position: Object.keys(acc).length,
                            isMissing: curr.isMissing,
                        };
                    }
                    acc[val].count++;
                    return acc;
                }, {});

                return Object.entries(reducedRow)
                    .map(([val, info]) => {
                        const style =
                            row === headers[headers.length - 1] &&
                            !info.isMissing &&
                            "color: #756f6f;";
                        return {
                            formula: `=PIVOT.HEADER("${val}")`,
                            value: this._getLabel(val),
                            span: info.count,
                            position: info.position,
                            isMissing: info.isMissing,
                            style,
                        };
                    })
                    .sort((a, b) => (a.position > b.position ? 1 : -1));
            });
        }
        /**
         * Create the row of the pivot table
         *
         * @private
         * @returns {Array<PivotDialogRow>}
         */
        _buildRowHeaders() {
            const rowCount = this.pivotData.getRowCount();
            const headers = [];
            for (let index = 0; index < rowCount; index++) {
                const pivotArgs = [];
                const current = this.pivotData.getRowValues(index);
                for (let i in current) {
                    pivotArgs.push(this.getters.getPivotRowGroupBys(this.pivotId)[i]);
                    pivotArgs.push(current[i]);
                }
                const isMissing = !this.pivotData.isUsedHeader(pivotArgs);
                pivotArgs.unshift(this.pivotId);
                headers.push({ args: pivotArgs, isMissing });
            }
            return headers.map(({ args, isMissing }) => {
                const argsString = args.join('","');
                const style = this._getStyle(args);
                return {
                    args,
                    formula: `=PIVOT.HEADER("${argsString}")`,
                    value: this._getLabel(argsString),
                    style,
                    isMissing,
                };
            });
        }
        /**
         * Build the values of the pivot table
         *
         * @private
         * @returns {Array<PivotDialogValue>}
         */
        _buildValues() {
            const length =
                this.pivotData.getTopHeaderCount() -
                this.getters.getPivotMeasures(this.pivotId).length;
            const rowGroupBys = this.getters.getPivotRowGroupBys(this.pivotId);
            const values = [];
            for (let i = 0; i < length; i++) {
                const colElement = [
                    ...this.pivotData.getColumnValues(i),
                    this.pivotData.getMeasureName(i),
                ];
                const colValues = [];
                for (let rowElement of this.pivotData.getRows()) {
                    const pivotArgs = [];
                    for (let index in rowElement) {
                        pivotArgs.push(rowGroupBys[index]);
                        pivotArgs.push(rowElement[index]);
                    }
                    for (let index in colElement) {
                        const field = this.pivotData.getColLevelIdentifier(index);
                        if (field === "measure") {
                            pivotArgs.unshift(colElement[index]);
                        } else {
                            pivotArgs.push(this.pivotData.getColLevelIdentifier(index));
                            pivotArgs.push(colElement[index]);
                        }
                    }
                    const isMissing = !this.pivotData.isUsedValue(pivotArgs);
                    pivotArgs.unshift(this.pivotId);
                    colValues.push({ args: this._buildCell(pivotArgs), isMissing });
                }
                values.push(colValues);
            }
            for (let i = length; i < this.pivotData.getTopHeaderCount(); i++) {
                const colElement = [
                    ...this.pivotData.getColumnValues(i),
                    this.pivotData.getMeasureName(i),
                ];
                const colValues = [];
                for (let rowElement of this.pivotData.getRows()) {
                    const pivotArgs = [];
                    for (let index in rowElement) {
                        pivotArgs.push(rowGroupBys[index]);
                        pivotArgs.push(rowElement[index]);
                    }
                    pivotArgs.unshift(colElement[0]);
                    const isMissing = !this.pivotData.isUsedValue(pivotArgs);
                    pivotArgs.unshift(this.pivotId);
                    colValues.push({ args: this._buildCell(pivotArgs), isMissing });
                }
                values.push(colValues);
            }
            return values;
        }
        /**
         * Format the given value with two decimals
         *
         * @private
         * @param {string} value Value to format
         * @returns {string}
         */
        _formatValue(value) {
            if (!value) {
                return "";
            }
            return formatDecimal(value, 2);
        }
        /**
         * Get the label of a pivot formula based on the args formula
         *
         * @private
         * @param {string} args Args of the pivot formula
         */
        _getLabel(args) {
            let domain = args.split('","');
            domain.shift();
            const len = domain.length;
            if (len === 0) {
                return _t("Total");
            }
            const field = domain[len - 2];
            const value = domain[len - 1];
            return this.getters.getFormattedHeader(this.pivotId, field, value);
        }
        /**
         * Get the style to apply to a row.
         * It will compute the padding
         *
         * @private
         * @param {Array<string>} args Args of the pivot row
         * @returns {string}
         */
        _getStyle(args) {
            // The structure of args is [measure, gb, value, (gb, value)...]
            // So, with a size of 3, the padding is null
            const length = args.length - 3;
            if (!length) {
                return "";
            }
            return `padding-left: ${length * 10}px`;
        }
    }
    PivotDialog.template = "documents_spreadsheet.PivotDialog";
    PivotDialog.components = { PivotDialogTable };
    return PivotDialog;
});
