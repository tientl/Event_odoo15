/** @odoo-module alias=documents_spreadsheet.PivotCache */

import { _t } from "web.core";
import Domain from "web.Domain";
import pyUtils from "web.py_utils";
import spreadsheet from "../o_spreadsheet_loader";

const { toString } = spreadsheet.helpers;
const functionRegistry = spreadsheet.registries.functionRegistry;

/**
 * Chunk array elements two by two
 * chunkBy2([1, 2, 3, 4])
 * >> [[1, 2], [3, 4]]
 */
function chunkBy2(arr) {
    return Array.from({ length: arr.length / 2 }, () => arr.splice(0, 2));
}

/**
 * groupDomainElements(["stage_id", "1", "create_date:month", "11/2021"])
 * >> ["stage_id,1", "create_date:month,11/2021"]
 */
function groupDomainElements(pivotFormulaDomainArgs) {
    return chunkBy2(pivotFormulaDomainArgs).map((chunk) => chunk.join(","));
}

export default class PivotCache {
    constructor(data) {
        /**
         * Here is an example of a possible cols structure in the PivotCache.
         * Each element of the array describes a spreadsheet column. Each element
         * of a column is part of its group hierarchy which are used to build the headers.
         * e.g. a pivot grouped by partner then stage
         * [
         *      [   partner = 10 > stage = 2 > measure = "expected_revenue"
         *          ["10"],
         *          ["10", "2"],
         *          ["10", "2", "expected_revenue"],
         *      ],
         *      [   partner = 12 > stage = 2 > measure = "expected_revenue"
         *          ["12"],
         *          ["12", "2"],
         *          ["12", "2", "expected_revenue"],
         *      ],
         *      [   partner = 12 > stage = 3 > measure = "expected_revenue"
         *          ["12"],
         *          ["12", "3"],
         *          ["12", "3", "expected_revenue"],
         *      ],
         * ]
         **/
        this._cols = data.cols;

        /**
         * Pivot structure with grouped fields and measures
         * e.g. ["partner_id", "stage_id", "measure"]
         */
        this._colStructure = data.colStructure;

        /**
         * Link between a given group and measures falling in that group.
         * e.g. group with partner=10 contains the measure referenced by 4,
         * the group with no partner (=false) contains measures referenced by 1, 2 and 3.
         * {
         *      partner: [
         *          [10, [4]],
         *          [11, [0]],
         *          [12, [6, 5]],
         *          [false, [1, 2, 3]],
         *      ],
         *      "create_date:day" : [
         *          ["10/07/2020", [5]],
         *          ["15/07/2020", [6]],
         *          ["16/07/2020", [0, 3, 4]],
         *          ["17/05/2020", [1]],
         *          ["17/06/2020", [2]],
         *      ],
         *      stage: ...,
         *      country: ...,
         * }
         */
        this._orderedMeasureIds = data.orderedMeasureIds;

        /**
         * All possible values for each fields.
         * {
         *      partner: [10, 11, 12, false],
         *      "create_date:day": [
         *          "10/07/2020",
         *          "15/07/2020",
         *          "16/07/2020",
         *          "17/05/2020",
         *          "17/06/2020",
         *      ]
         *      stage: ...,
         *      country: ...,
         * }
         */
        this._fieldValues = {};
        for (let fieldName of Object.keys(this._orderedMeasureIds)) {
            this._fieldValues[fieldName] = this._orderedMeasureIds[fieldName].map(
                ([fieldValue]) => fieldValue
            );
        }

        /**
         * Promises resolving to display name of many2one records.
         * Useless for non many2one fields.
         * {
         *      partner: {
         *          10: "Raoul",
         *          11: "Borat",
         *          12: "James",
         *      },
         *      "create_date:day" : {
         *          09/07/2020: "09/07/2020",
         *          10/07/2020: "10/07/2020",
         *          ...
         *      },
         *      stage: ...,
         *      country: ...,
         * }
         */
        this._labels = data.labels;

        /**
         * Each element of the array describes a spreadsheet row. Each row contains
         * the hierarchy of the group it belongs to.
         * [
         *      ["10"],                     //country = 10
         *      ["10", "16/07/2020"],       //country = 10 > create_date = "16/07/2020"
         *      ["13"],                     //country = 13
         *      ["13", "16/07/2020"],       //country = 13 > create_date = "16/07/2020"
         *      ["13", "17/07/2020"],       //country = 13 > create_date = "17/07/2020"
         *      ["173"],                    //country = 173
         *      ["173", "17/07/2020"],      //country = 173 > create_date = "17/07/2020"
         * ]
         **/
        this._rows = data.rows;

        /**
         * Measures references by the groupBys data structure.
         * They are referenced by their index.
         * [
         *      { expected_revenue: 4500, count: 1},
         *      { expected_revenue: 500, count: 1},
         *      { expected_revenue: 100, count: 2},
         *      { expected_revenue: 1000, count: 1},
         *      { expected_revenue: 25000, count: 5},
         *      { expected_revenue: 70000, count: 2},
         *      { expected_revenue: 25000, count: 5},
         * ]
         */
        this._values = data.values;

        /**
         * List of measure references. Cached for performance reasons. Rebuilding them
         * at each function evaluation requires too much GC work.
         */
        this._cacheKeys = [...data.values.keys()];

        /**
         * Contains the domain of the values used during the evaluation of the formula =Pivot(...)
         * Is used to know if a pivot cell is missing or not
         * */

        this._usedValueDomains = new Set();
        /**
         * Contains the domain of the headers used during the evaluation of the formula =Pivot.header(...)
         * Is used to know if a pivot cell is missing or not
         * */
        this._usedHeaderDomains = new Set();
        /**
         * for each individual cell map the domain of a cell to its formula
         * */
        this._formulaToDomain = data.formulaToDomain;
    }

    getRows() {
        return this._rows;
    }

    /**
     * Return the total number of rows in the pivot, including
     * totals.
     *
     * @returns {number}
     */
    getRowCount() {
        return this._rows.length;
    }

    /**
     * Return the name identifying a header level in
     * the columns hierarchy.
     * e.g. "stage_id" or "measure"
     *
     * @param {number} level
     * @returns {string}
     */
    getColLevelIdentifier(level) {
        return this._colStructure[level];
    }

    /**
     * Return all possible values in the pivot for a given field.
     *
     * @param {string} fieldName
     * @returns {Array<string>}
     */
    getFieldValues(fieldName) {
        if (!(fieldName in this._fieldValues)) {
            throw new Error(`Cannot find any pivot values for field "${fieldName}"`);
        }
        return this._fieldValues[fieldName];
    }

    /**
     * Return the label of a group.
     *
     * @param {string} groupBy e.g. create_date:month
     * @param {string} groupValue e.g. "05/2020"
     * @returns {Promise<string> | undefined}
     */
    getGroupLabel(groupBy, groupValue) {
        return this._labels[groupBy] && this._labels[groupBy][groupValue];
    }

    /**
     * Check if the label of group is loaded or being loaded.
     *
     * @param {string} groupBy
     * @param {string} groupValue
     * @returns {boolean}
     */
    isGroupLabelLoaded(groupBy, groupValue) {
        return groupValue in this._labels[groupBy];
    }

    /**
     * Return the measure name given the column index in the pivot.
     *
     * @param {number} columnIndex
     * @returns {string}
     */
    getMeasureName(columnIndex) {
        const columnValues = this._cols[columnIndex];
        return columnValues[columnValues.length - 1].slice().pop();
    }

    /**
     * Return values of each group and subgroup of a given column.
     * e.g. ["17", "05/2020", "true"]
     *
     * @param {number} columnIndex
     * @returns {Array<string>}
     */
    getColumnValues(columnIndex) {
        const columnValues = this._cols[columnIndex];
        const values = columnValues[columnValues.length - 1].slice();
        values.pop();
        return values;
    }

    /**
     * Returns the hierarchy from a subgroup to a topgroup.
     * e.g. ["17", "05/2020", "true", "expected_revenue"]
     *
     * @param {number} topGroupIndex
     * @param {number} subgroupIndex
     */
    getColGroupHierarchy(topGroupIndex, subgroupIndex) {
        return this._cols[topGroupIndex][subgroupIndex];
    }

    /**
     * Return values of each group and subgroup of a given row.
     * e.g. ["17", "05/2020", true]
     *
     * @param {number} columnIndex
     * @param {Array<string>}
     */
    getRowValues(rowIndex) {
        return this._rows[rowIndex];
    }

    /**
     * Return the number of levels of column groups.
     *
     * @returns {number}
     */
    getColGroupByLevels() {
        return this._cols[0].length - 1;
    }

    /**
     * Return the number of top level headers, including
     * a header for the total.
     *
     * @returns {number}
     */
    getTopHeaderCount() {
        return this._cols.length;
    }

    /**
     * From lower level column values, find the top group index.
     *
     * @param {Array<string>} groupeValues e.g. ["17", "05/2020", "probability"]
     * @returns {number}
     */
    getTopGroupIndex(groupValues) {
        return this._cols.findIndex((topGroup) => {
            const index = topGroup.findIndex(
                (values) => JSON.stringify(values) === JSON.stringify(groupValues)
            );
            return index !== -1;
        });
    }

    /**
     * From row group values, find the row index in the pivot.
     *
     * @param {Array<string>} groupValues
     * @returns {number}
     */
    getRowIndex(groupValues) {
        const stringifiedValues = JSON.stringify(groupValues);
        return this._rows.findIndex((values) => JSON.stringify(values) === stringifiedValues);
    }

    /**
     * Given some group values, return to which group level they belong.
     *
     * @param {Array<string>} groupValues
     * @returns {number}
     */
    getSubgroupLevel(groupValues) {
        return groupValues.length - 1;
    }

    isUsedValue(pivotArgs) {
        return this._usedValueDomains.has(pivotArgs.join());
    }

    isUsedHeader(pivotArgs) {
        return this._usedHeaderDomains.has(pivotArgs.join());
    }

    markAsValueUsed(domain, measure) {
        const toTag = domain.slice();
        toTag.unshift(measure);
        this._usedValueDomains.add(toTag.join());
    }

    markAsHeaderUsed(domain) {
        this._usedHeaderDomains.add(domain.join());
    }

    /**
     * Compute and aggregate measures satisfying a given domain.
     *
     * @param {string} measureName
     * @param {string} operator
     * @param  {Array<string>} domain
     */
    getMeasureValue(measureName, operator, domain) {
        const measureIds = this._computeMeasureIds(domain);
        return this._aggregateMeasure(measureIds, measureName, operator);
    }

    /**
     * A a new label for a field value
     *
     * @param {string} field
     * @param {string} fieldValue
     * @param {string} label
     */
    addLabel(field, fieldValue, label) {
        this._labels[field] = { ...this._labels[field], [fieldValue]: label };
    }

    /**
     * Return the domain as it is used in odoo, based on the args of a Pivot formula.
     * an exemple of args would be:
     * ["1","expected_revenue","create_date:month","08/2021","stage_id","1"]
     * @param {Array} args
     * @returns {Array}
     */
    getDomainFromFormula(args) {
        const parsedFormulaDomain = groupDomainElements(args.slice(2));
        const formulaDomains = Object.keys(this._formulaToDomain).filter((cellDomain) => {
            const parsedCellDomain = groupDomainElements(cellDomain.split(","));
            return parsedFormulaDomain.every((v) => parsedCellDomain.includes(v));
        });
        const domains = formulaDomains.map((formulaDomain) =>
            Domain.prototype.arrayToString(this._formulaToDomain[formulaDomain])
        );
        return pyUtils.assembleDomains(domains, "OR");
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute the values corresponding to a pivot and a given domain
     *
     * For that, we take the intersection of all group_bys
     *
     * @private
     * @param {Object} pivot Pivot object
     * @param  {Array<string>} domain Domain
     *
     * @returns List of measure ids
     */
    _computeMeasureIds(domain) {
        let returnValue = this._cacheKeys;
        let i = 0;
        while (i < domain.length && returnValue.length) {
            const field = toString(domain[i]);
            if (!(field in this._orderedMeasureIds)) {
                return [];
            }
            const value = toString(domain[i + 1]);
            if (!this._fieldValues[field].includes(value)) {
                return [];
            }
            const [, measureIds] =
                field in this._orderedMeasureIds &&
                this._orderedMeasureIds[field].find(([fieldValue]) => fieldValue === value);
            returnValue = measureIds.filter((x) => returnValue.includes(x));
            i += 2;
        }
        return returnValue;
    }

    /**
     * Process the values computed to return one value
     *
     * @private
     * @param {Array<number>} measureIds
     * @param {string} measureName Name of the measure
     *
     * @returns Computed value
     */
    _aggregateMeasure(measureIds, measureName, operator) {
        const functions = functionRegistry.mapping;
        if (measureIds.length === 0) {
            return "";
        }
        if (measureIds.length === 1) {
            return this._values[measureIds[0]][measureName] || "";
        }
        switch (operator) {
            case "array_agg":
                throw Error(_.str.sprintf(_t("Not implemented: %s"), operator));
            case "count":
                return functions.COUNT(
                    ...measureIds.map((id) => this._values[id][measureName] || 0)
                );
            case "count_distinct":
                return functions.COUNTUNIQUE(
                    ...measureIds.map((id) => measureIds[id][measureName] || 0)
                );
            case "bool_and":
                return functions.AND(...measureIds.map((id) => this._values[id][measureName] || 0));
            case "bool_or":
                return functions.OR(...measureIds.map((id) => this._values[id][measureName] || 0));
            case "max":
                return functions.MAX(...measureIds.map((id) => this._values[id][measureName] || 0));
            case "min":
                return functions.MIN(...measureIds.map((id) => this._values[id][measureName] || 0));
            case "avg":
                return functions["AVERAGE.WEIGHTED"](
                    ...measureIds
                        .map((id) => [
                            this._values[id][measureName] || 0,
                            this._values[id]["count"],
                        ])
                        .flat()
                );
            case "sum":
                return functions.SUM(...measureIds.map((id) => this._values[id][measureName] || 0));
            default:
                console.warn(_.str.sprintf(_t("Unknown operator: %s"), operator));
                return "";
        }
    }
}
