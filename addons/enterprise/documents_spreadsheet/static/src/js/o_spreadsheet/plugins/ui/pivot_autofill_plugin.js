/** @odoo-module */

import core from "web.core";
import spreadsheet from "documents_spreadsheet.spreadsheet";
import { formats } from "../../constants";
import {
    getFirstPivotFunction,
    getNumberOfPivotFormulas,
} from "../../helpers/odoo_functions_helpers";

const { astToFormula } = spreadsheet;
const _t = core._t;

/**
 * @typedef CurrentElement
 * @property {Array<string>} cols
 * @property {Array<string>} rows
 *
 * @typedef TooltipFormula
 * @property {string} title
 * @property {string} value
 *
 * @typedef GroupByDate
 * @property {boolean} isDate
 * @property {string|undefined} group
 */

export default class PivotAutofillPlugin extends spreadsheet.UIPlugin {
    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill of a pivot function
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if autofill is LEFT/RIGHT, false otherwise
     * @param {number} increment number of steps
     *
     * @returns {string}
     */
    getPivotNextAutofillValue(formula, isColumn, increment) {
        if (getNumberOfPivotFormulas(formula) !== 1) {
            return formula;
        }
        const { functionName, args } = getFirstPivotFunction(formula);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        const pivotId = evaluatedArgs[0];
        let builder;
        if (functionName === "PIVOT") {
            builder = this._autofillPivotValue.bind(this);
        } else if (functionName === "PIVOT.HEADER") {
            if (evaluatedArgs.length === 1) {
                // Total
                if (isColumn) {
                    // LEFT-RIGHT
                    builder = this._autofillPivotRowHeader.bind(this);
                } else {
                    // UP-DOWN
                    builder = this._autofillPivotColHeader.bind(this);
                }
            } else if (this.getters.getPivotRowGroupBys(pivotId).includes(evaluatedArgs[1])) {
                builder = this._autofillPivotRowHeader.bind(this);
            } else {
                builder = this._autofillPivotColHeader.bind(this);
            }
        }
        if (builder) {
            return builder(pivotId, evaluatedArgs, isColumn, increment);
        }
        return formula;
    }

    /**
     * Compute the tooltip to display from a Pivot formula
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     *
     * @returns {Array<TooltipFormula>}
     */
    getTooltipFormula(formula, isColumn) {
        if (getNumberOfPivotFormulas(formula) !== 1) {
            return [];
        }
        const { functionName, args } = getFirstPivotFunction(formula);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        const pivotId = evaluatedArgs[0];
        if (functionName === "PIVOT") {
            return this._tooltipFormatPivot(pivotId, evaluatedArgs, isColumn);
        } else if (functionName === "PIVOT.HEADER") {
            return this._tooltipFormatPivotHeader(pivotId, evaluatedArgs);
        }
        return [];
    }

    // ---------------------------------------------------------------------
    // Autofill
    // ---------------------------------------------------------------------

    /**
     * Check if the pivot is only grouped by a date field.
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} groupBys Array of group by
     *
     * @private
     *
     * @returns {GroupByDate}
     */
    _isGroupedByDate(pivotId, groupBys) {
        if (groupBys.length !== 1) {
            return { isDate: false };
        }
        const [fieldName, group] = groupBys[0].split(":");
        return {
            isDate: this.getters.isPivotFieldDate(pivotId, fieldName),
            group,
        };
    }

    /**
     * Get the next value to autofill from a pivot value ("=PIVOT()")
     *
     * Here are the possibilities:
     * 1) LEFT-RIGHT
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting a row-header
     *      => Creation of a PIVOT.HEADER with the value of the current rows
     *  - Targeting outside the pivot (before the row header and after the
     *    last col)
     *      => Return empty string
     *  - Targeting a value cell
     *      => Autofill by changing the cols
     * 2) UP-DOWN
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting a col-header
     *      => Creation of a PIVOT.HEADER with the value of the current cols,
     *         with the given increment
     *  - Targeting outside the pivot (after the last row)
     *      => Return empty string
     *  - Targeting a value cell
     *      => Autofill by changing the rows
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args args of the pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @param {number} increment Increment of the autofill
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotValue(pivotId, args, isColumn, increment) {
        const currentElement = this._getCurrentValueElement(pivotId, args);
        const pivotData = this.getters.getPivotStructureData(pivotId);
        const date = this._isGroupedByDate(
            pivotId,
            isColumn
                ? this.getters.getPivotColGroupBys(pivotId)
                : this.getters.getPivotRowGroupBys(pivotId)
        );
        let cols = [];
        let rows = [];
        let measure;
        if (isColumn) {
            // LEFT-RIGHT
            rows = currentElement.rows;
            if (date.isDate) {
                // Date
                cols = currentElement.cols;
                cols[0] = this._incrementDate(cols[0], date.group, increment);
                measure = cols.pop();
            } else {
                const currentColIndex = pivotData.getTopGroupIndex(currentElement.cols);
                if (currentColIndex === -1) {
                    return "";
                }
                const nextColIndex = currentColIndex + increment;
                if (nextColIndex === -1) {
                    // Targeting row-header
                    return this._autofillRowFromValue(pivotId, currentElement);
                }
                if (nextColIndex < -1 || nextColIndex >= pivotData.getTopHeaderCount()) {
                    // Outside the pivot
                    return "";
                }
                // Targeting value
                cols = pivotData.getColumnValues(nextColIndex);
                measure = pivotData.getMeasureName(nextColIndex);
            }
        } else {
            // UP-DOWN
            cols = currentElement.cols;
            if (date.isDate) {
                // Date
                if (currentElement.rows.length === 0) {
                    return "";
                }
                rows = currentElement.rows;
                rows[0] = this._incrementDate(rows[0], date.group, increment);
            } else {
                const currentRowIndex = pivotData.getRowIndex(currentElement.rows);
                if (currentRowIndex === -1) {
                    return "";
                }
                const nextRowIndex = currentRowIndex + increment;
                if (nextRowIndex < 0) {
                    // Targeting col-header
                    return this._autofillColFromValue(pivotId, nextRowIndex, currentElement);
                }
                if (nextRowIndex >= pivotData.getRowCount()) {
                    // Outside the pivot
                    return "";
                }
                // Targeting value
                rows = pivotData.getRowValues(nextRowIndex);
            }
            measure = cols.pop();
        }
        return this._buildValueFormula(this._buildArgs(pivotId, measure, rows, cols));
    }
    /**
     * Get the next value to autofill from a pivot header ("=PIVOT.HEADER()")
     * which is a col.
     *
     * Here are the possibilities:
     * 1) LEFT-RIGHT
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting outside (before the first col after the last col)
     *      => Return empty string
     *  - Targeting a col-header
     *      => Creation of a PIVOT.HEADER with the value of the new cols
     * 2) UP-DOWN
     *  - Working on a date value, with one level of group by in the header
     *      => Replace the date in the headers and autocomplete as usual
     *  - Targeting a cell (after the last col and before the last row)
     *      => Autofill by adding the corresponding rows
     *  - Targeting a col-header (after the first col and before the last
     *    col)
     *      => Creation of a PIVOT.HEADER with the value of the new cols
     *  - Targeting outside the pivot (before the first col of after the
     *    last row)
     *      => Return empty string
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args args of the pivot.header formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @param {number} increment Increment of the autofill
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotColHeader(pivotId, args, isColumn, increment) {
        const pivotData = this.getters.getPivotStructureData(pivotId);
        const currentElement = this._getCurrentHeaderElement(pivotId, args);
        const currentIndex = pivotData.getTopGroupIndex(currentElement.cols);
        const date = this._isGroupedByDate(pivotId, this.getters.getPivotColGroupBys(pivotId));
        if (isColumn) {
            // LEFT-RIGHT
            let groupValues;
            if (date.isDate) {
                // Date
                groupValues = currentElement.cols;
                groupValues[0] = this._incrementDate(groupValues[0], date.group, increment);
            } else {
                const colIndex = pivotData.getSubgroupLevel(currentElement.cols);
                const nextIndex = currentIndex + increment;
                if (
                    currentIndex === -1 ||
                    nextIndex < 0 ||
                    nextIndex >= pivotData.getTopHeaderCount()
                ) {
                    // Outside the pivot
                    return "";
                }
                // Targeting a col.header
                groupValues = pivotData.getColGroupHierarchy(nextIndex, colIndex);
            }
            return this._buildHeaderFormula(this._buildArgs(pivotId, undefined, [], groupValues));
        } else {
            // UP-DOWN
            const colIndex = pivotData.getSubgroupLevel(currentElement.cols);
            const nextIndex = colIndex + increment;
            const groupLevels = pivotData.getColGroupByLevels();
            if (nextIndex < 0 || nextIndex >= groupLevels + 1 + pivotData.getRowCount()) {
                // Outside the pivot
                return "";
            }
            if (nextIndex >= groupLevels + 1) {
                // Targeting a value
                const rowIndex = nextIndex - groupLevels - 1;
                const measure = pivotData.getMeasureName(currentIndex);
                const cols = pivotData.getColumnValues(currentIndex);
                const rows = pivotData.getRowValues(rowIndex);
                return this._buildValueFormula(this._buildArgs(pivotId, measure, rows, cols));
            } else {
                // Targeting a col.header
                const cols = pivotData.getColGroupHierarchy(currentIndex, nextIndex);
                return this._buildHeaderFormula(this._buildArgs(pivotId, undefined, [], cols));
            }
        }
    }
    /**
     * Get the next value to autofill from a pivot header ("=PIVOT.HEADER()")
     * which is a row.
     *
     * Here are the possibilities:
     * 1) LEFT-RIGHT
     *  - Targeting outside (LEFT or after the last col)
     *      => Return empty string
     *  - Targeting a cell
     *      => Autofill by adding the corresponding cols
     * 2) UP-DOWN
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting a row-header
     *      => Creation of a PIVOT.HEADER with the value of the new rows
     *  - Targeting outside the pivot (before the first row of after the
     *    last row)
     *      => Return empty string
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args args of the pivot.header formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @param {number} increment Increment of the autofill
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotRowHeader(pivotId, args, isColumn, increment) {
        const pivotData = this.getters.getPivotStructureData(pivotId);
        const currentElement = this._getCurrentHeaderElement(pivotId, args);
        const currentIndex = pivotData.getRowIndex(currentElement.rows);
        const date = this._isGroupedByDate(pivotId, this.getters.getPivotRowGroupBys(pivotId));
        if (isColumn) {
            // LEFT-RIGHT
            if (increment < 0 || increment > pivotData.getTopHeaderCount()) {
                // Outside the pivot
                return "";
            }
            const values = pivotData.getColumnValues(increment - 1);
            const measure = pivotData.getMeasureName(increment - 1);
            return this._buildValueFormula(
                this._buildArgs(pivotId, measure, currentElement.rows, values)
            );
        } else {
            // UP-DOWN
            let rows;
            if (date.isDate) {
                // Date
                rows = currentElement.rows;
                rows[0] = this._incrementDate(rows[0], date.group, increment);
            } else {
                const nextIndex = currentIndex + increment;
                if (currentIndex === -1 || nextIndex < 0 || nextIndex >= pivotData.getRowCount()) {
                    return "";
                }
                rows = pivotData.getRowValues(nextIndex);
            }
            return this._buildHeaderFormula(this._buildArgs(pivotId, undefined, rows, []));
        }
    }
    /**
     * Create a col header from a value
     *
     * @param {string} pivotId Id of the pivot
     * @param {number} nextIndex Index of the target column
     * @param {CurrentElement} currentElement Current element (rows and cols)
     *
     * @private
     *
     * @returns {string}
     */
    _autofillColFromValue(pivotId, nextIndex, currentElement) {
        const pivotData = this.getters.getPivotStructureData(pivotId);
        const groupIndex = pivotData.getTopGroupIndex(currentElement.cols);
        if (groupIndex < 0) {
            return "";
        }
        const levels = pivotData.getColGroupByLevels();
        const index = levels + 1 + nextIndex;
        if (index < 0 || index >= levels + 1) {
            return "";
        }
        const cols = pivotData.getColGroupHierarchy(groupIndex, index);
        return this._buildHeaderFormula(this._buildArgs(pivotId, undefined, [], cols));
    }
    /**
     * Create a row header from a value
     *
     * @param {string} pivotId Id of the pivot
     * @param {CurrentElement} currentElement Current element (rows and cols)
     *
     * @private
     *
     * @returns {string}
     */
    _autofillRowFromValue(pivotId, currentElement) {
        const rows = currentElement.rows;
        if (!rows) {
            return "";
        }
        return this._buildHeaderFormula(this._buildArgs(pivotId, undefined, rows, []));
    }
    /**
     * Parse the arguments of a pivot function to find the col values and
     * the row values of a PIVOT.HEADER function
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args Args of the pivot.header formula
     *
     * @private
     *
     * @returns {CurrentElement}
     */
    _getCurrentHeaderElement(pivotId, args) {
        const values = this._parseArgs(args.slice(1));
        const cols = this._getFieldValues(
            [...this.getters.getPivotColGroupBys(pivotId), "measure"],
            values
        );
        const rows = this._getFieldValues(this.getters.getPivotRowGroupBys(pivotId), values);
        return { cols, rows };
    }
    /**
     * Parse the arguments of a pivot function to find the col values and
     * the row values of a PIVOT function
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args Args of the pivot formula
     *
     * @private
     *
     * @returns {CurrentElement}
     */
    _getCurrentValueElement(pivotId, args) {
        const values = this._parseArgs(args.slice(2));
        const colGroupBys = this.getters.getPivotColGroupBys(pivotId);
        const cols = this._getFieldValues(colGroupBys, values);
        cols.push(args[1]); // measure
        const rowGroupBys = this.getters.getPivotRowGroupBys(pivotId);
        const rows = this._getFieldValues(rowGroupBys, values);
        return { cols, rows };
    }
    /**
     * Return the values for the fields which are present in the list of
     * fields
     *
     * ex: groupBys: ["create_date"]
     *     items: { create_date: "01/01", stage_id: 1 }
     *      => ["01/01"]
     *
     * @param {Array<string>} fields List of fields
     * @param {Object} values Association field-values
     *
     * @private
     * @returns {Array<string>}
     */
    _getFieldValues(fields, values) {
        return fields.filter((field) => field in values).map((field) => values[field]);
    }
    /**
     * Increment a date with a given increment and interval (group)
     *
     * @param {string} date
     * @param {string} group (day, week, month, ...)
     * @param {number} increment
     *
     * @private
     * @returns {string}
     */
    _incrementDate(date, group, increment) {
        const format = formats[group].out;
        const interval = formats[group].interval;
        const dateMoment = moment(date, format);
        return dateMoment.isValid() ? dateMoment.add(increment, interval).format(format) : date;
    }
    /**
     * Create a structure { field: value } from the arguments of a pivot
     * function
     *
     * @param {Array<string>} args
     *
     * @private
     * @returns {Object}
     */
    _parseArgs(args) {
        const values = {};
        for (let i = 0; i < args.length; i += 2) {
            values[args[i]] = args[i + 1];
        }
        return values;
    }

    // ---------------------------------------------------------------------
    // Tooltips
    // ---------------------------------------------------------------------

    /**
     * Get the tooltip for a pivot formula
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @private
     *
     * @returns {Array<TooltipFormula>}
     */
    _tooltipFormatPivot(pivotId, args, isColumn) {
        const tooltips = [];
        const values = this._parseArgs(args.slice(2));
        const colGroupBys = this.getters.getPivotColGroupBys(pivotId);
        const rowGroupBys = this.getters.getPivotRowGroupBys(pivotId);
        for (let [field, value] of Object.entries(values)) {
            if (
                (colGroupBys.includes(field) && isColumn) ||
                (rowGroupBys.includes(field) && !isColumn)
            ) {
                tooltips.push({
                    title: this.getters.getFormattedGroupBy(pivotId, field),
                    value: this.getters.getFormattedHeader(pivotId, field, value),
                });
            }
        }
        if (this.getters.getPivotMeasures(pivotId).length !== 1 && isColumn) {
            const measure = args[1];
            tooltips.push({
                title: _t("Measure"),
                value: this.getters.getFormattedHeader(pivotId, "measure", measure),
            });
        }
        return tooltips;
    }
    /**
     * Get the tooltip for a pivot header formula
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args
     *
     * @private
     *
     * @returns {Array<TooltipFormula>}
     */
    _tooltipFormatPivotHeader(pivotId, args) {
        const tooltips = [];
        const values = this._parseArgs(args.slice(1));
        if (Object.keys(values).length === 0) {
            return [{ title: _t("Total"), value: _t("Total") }];
        }
        for (let [field, value] of Object.entries(values)) {
            tooltips.push({
                title:
                    field === "measure"
                        ? _t("Measure")
                        : this.getters.getFormattedGroupBy(pivotId, field),
                value: this.getters.getFormattedHeader(pivotId, field, value),
            });
        }
        return tooltips;
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    /**
     * Create the args from pivot, measure, rows and cols
     * if measure is undefined, it's not added
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} measure
     * @param {Object} rows
     * @param {Object} cols
     *
     * @private
     * @returns {Array<string>}
     */
    _buildArgs(pivotId, measure, rows, cols) {
        const args = [pivotId];
        if (measure) {
            args.push(measure);
        }
        const rowGroupBys = this.getters.getPivotRowGroupBys(pivotId);
        for (let index in rows) {
            args.push(rowGroupBys[index]);
            args.push(rows[index]);
        }
        const measures = this.getters.getPivotMeasures(pivotId);
        if (cols.length === 1 && measures.map((x) => x.field).includes(cols[0])) {
            args.push("measure");
            args.push(cols[0]);
        } else {
            const pivotData = this.getters.getPivotStructureData(pivotId);
            for (let index in cols) {
                args.push(pivotData.getColLevelIdentifier(index));
                args.push(cols[index]);
            }
        }
        return args;
    }
    /**
     * Create a pivot header formula at col/row
     *
     * @param {Array<string>} args
     *
     * @private
     * @returns {string}
     */
    _buildHeaderFormula(args) {
        return `=PIVOT.HEADER("${args
            .map((arg) => arg.toString().replace(/"/g, '\\"'))
            .join('","')}")`;
    }
    /**
     * Create a pivot formula at col/row
     *
     * @param {Array<string>} args
     *
     * @private
     * @returns {string}
     */
    _buildValueFormula(args) {
        return `=PIVOT("${args.map((arg) => arg.toString().replace(/"/g, '\\"')).join('","')}")`;
    }
}

PivotAutofillPlugin.modes = ["normal", "headless"];
PivotAutofillPlugin.getters = ["getPivotNextAutofillValue", "getTooltipFormula"];
