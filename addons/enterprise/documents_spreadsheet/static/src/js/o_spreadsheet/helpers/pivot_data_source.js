/** @odoo-module */
/* global moment */

import { _t } from "web.core";
import Domain from "web.Domain";
import pyUtils from "web.py_utils";
import { BasicDataSource } from "./basic_data_source";
import PivotCache from "./pivot_cache";
import { formats } from "../constants";
import { intersect, removeContextUserInfo } from "./helpers";
/**
 * @typedef {import("../plugins/core/pivot_plugin").SpreadsheetPivotForRPC} SpreadsheetPivotForRPC
 * @typedef {import("./basic_data_source").Field} Field
 */
export default class PivotDataSource extends BasicDataSource {
    /**
     *
     * @param {Object} params
     * @param {SpreadsheetPivotForRPC} params.definition;
     */
    constructor(params) {
        super(params);
        this.definition = params.definition;
        this.computedDomain = this.definition.domain;
        this.context = removeContextUserInfo(this.definition.context);
    }
    /**
     * @override
     * @param {Object} params
     * @param {boolean|undefined} params.initialDomain True to fetch with the
     * domain which does not contains the global filters
     */
    async _fetch(params = {}) {
        const result = await this.rpc({
            model: this.definition.model,
            method: "read_group",
            context: this.context,
            domain: params.initialDomain ? this.definition.domain : this.computedDomain,
            fields: this.definition.measures.map((elt) =>
                elt.field === "__count" ? elt.field : elt.field + ":" + elt.operator
            ),
            groupBy: this.definition.rowGroupBys.concat(this.definition.colGroupBys),
            lazy: false,
        });
        return this._createCache(result);
    }

    /**
     * Get the computed domain of this source
     * @returns {Array}
     */
    getComputedDomain() {
        return this.computedDomain;
    }

    /**
     * Set the computed domain
     *
     * @param {Array} computedDomain
     */
    setComputedDomain(computedDomain) {
        this.computedDomain = computedDomain;
    }

    /**
     * Fetch the labels which do not exist on the cache (it could happen for
     * example in multi-company)
     * It also update the cache to avoid further rpc.
     *
     * @param {Field} field Name of the field
     * @param {string} value Value
     *
     * @returns {Promise<string>}
     */
    async _fetchLabel(field, value) {
        const model = field.relation;
        let label;
        try {
            const rpc = await this.rpc({
                model,
                method: "name_get",
                args: [parseInt(value, 10)],
            });
            label = rpc;
        } catch (e) {
            label = new Error(_.str.sprintf(_t("Unable to fetch the label of %s of model %s"), value, model));
        }
        if (this.data) {
            this.data.addLabel(field.name, value, label);
        }
    }

    /**
     * Create a cache object for the given pivot from the result of the read
     * group RPC
     *
     * @param {Object} readGroups Result of the read_group rpc
     *
     * @private
     *
     * @returns {PivotCache} Cache for pivot object
     */
    async _createCache(readGroups) {
        const formulaToDomain = {};
        const groupBys = {};
        const labels = {};
        const values = [];

        const fieldNames = this.definition.rowGroupBys.concat(this.definition.colGroupBys);
        for (let fieldName of fieldNames) {
            labels[fieldName] = {};
        }

        for (let readGroup of readGroups) {
            const value = {};
            for (let measure of this.definition.measures) {
                const field = measure.field;
                value[field] = readGroup[field];
            }
            value["count"] = readGroup["__count"];
            const formulaDomain = [];
            const index = values.push(value) - 1;
            for (let fieldName of fieldNames) {
                const { label, id } = this._formatValue(fieldName, readGroup[fieldName]);
                labels[fieldName][id] = label;
                let groupBy = groupBys[fieldName] || {};
                let vals = groupBy[id] || [];
                vals.push(index);
                groupBy[id] = vals;
                groupBys[fieldName] = groupBy;
                formulaDomain.push(`${fieldName},${id}`);
            }
            formulaToDomain[formulaDomain.join(",")] = readGroup["__domain"];
        }
        const orderedValues = await this._getOrderedValues(this.definition, groupBys);
        const orderedMeasureIds = {};
        for (const fieldName of fieldNames) {
            orderedMeasureIds[fieldName] = orderedValues[fieldName]
                ? orderedValues[fieldName].map((value) => [value, groupBys[fieldName][value] || []])
                : [];
        }

        const measures = this.definition.measures.map((m) => m.field);
        const rows = this._createRows(this.definition.rowGroupBys, orderedMeasureIds);
        const cols = this._createCols(this.definition.colGroupBys, orderedMeasureIds, measures);
        const colStructure = this.definition.colGroupBys.slice();
        colStructure.push("measure");
        return new PivotCache({
            cols,
            colStructure,
            orderedMeasureIds,
            labels,
            rows,
            values,
            formulaToDomain,
        });
    }

    /**
     * Retrieves the id and the label of a field/value. It also convert dates
     * to non-locale version (i.e. March 2020 => 03/2020)
     *
     * @param {string} fieldDesc Field (create_date:month)
     * @param {string} value Value
     *
     * @private
     * @returns {Object} Label and id formatted
     */
    _formatValue(fieldDesc, value) {
        const [fieldName, group] = fieldDesc.split(":");
        const field = this.metadata.fields[fieldName];
        let id;
        let label;
        if (value instanceof Array) {
            id = value[0];
            label = value[1];
        } else {
            id = value;
            label = value;
        }
        if (field && field.type === "selection") {
            const selection = field.selection.find((x) => x[0] === id);
            label = selection && selection[1];
        }
        if (field && ["date", "datetime"].includes(field.type) && group && value) {
            const fIn = formats[group]["in"];
            const fOut = formats[group]["out"];
            // eslint-disable-next-line no-undef
            const date = moment(value, fIn);
            id = date.isValid() ? date.format(fOut) : false;
            label = id;
        }
        return { label, id };
    }
    /**
     * Return all possible values for each grouped field. Values are ordered according
     * to the read group result.
     * e.g.
     *  {
     *      field1: [value1, value2, value3],
     *      field2: [value1, value2],
     *  }
     *
     * @param {Object} params rpc params
     * @param {string} params.model model name
     * @param {Object} groupBys
     * @returns {Object}
     */
    async _getOrderedValues({ model, domain }, groupBys) {
        return Object.fromEntries(
            await Promise.all(
                Object.entries(groupBys).map(async ([groupBy, measures]) => {
                    const [fieldName, aggregationFunction] = groupBy.split(":");
                    const field = this.metadata.fields[fieldName];
                    let values = Object.keys(measures);
                    const hasUndefined = values.includes("false");
                    values = ["date", "datetime"].includes(field.type)
                        ? this._orderDateValues(
                              values.filter((value) => value !== "false"),
                              aggregationFunction
                          )
                        : await this._orderValues(values, fieldName, field, model, domain);
                    if (hasUndefined && field.type !== "boolean") {
                        values.push("false");
                    }
                    return [groupBy, values];
                })
            )
        );
    }
    /**
     * Sort date and datetime aggregated values.
     *
     * @param {Array<string>} values
     * @param {string} aggregationFunction
     * @returns {Array<string>}
     */
    _orderDateValues(values, aggregationFunction) {
        return values
          .map((value) => moment(value, formats[aggregationFunction].out))
          .sort((a, b) => a - b)
          .map((value) => value.format(formats[aggregationFunction].out));
    }

    /**
     * Order values according to a search_read result.
     *
     * @param {Array} values
     * @param {string} fieldName
     * @param {Field} field
     * @param {string} model
     * @param {Array} domain
     * @returns {Array}
     */
    async _orderValues(values, fieldName, field, model, baseDomain) {
        const requestField = field.relation ? "id" : fieldName;
        values = ["boolean", "many2one", "many2many", "integer", "float"].includes(field.type)
            ? values.map((value) => JSON.parse(value))
            : values;
        const domainString = pyUtils.assembleDomains([
            field.relation ? "[]" : Domain.prototype.arrayToString(baseDomain),
            Domain.prototype.arrayToString([[requestField, "in", values]]),
            ], "AND");
        const domain = pyUtils.eval("domain", domainString, {});
        const records = await this.rpc({
            model: field.relation ? field.relation : model,
            domain,
            context: { ...this.context, active_test: false },
            method: "search_read",
            fields: [requestField],
            // orderby is omitted for relational fields on purpose to have the default order of the model
            orderBy: field.relation ? false : [{ name: fieldName, asc: true }],
        });
        return [...new Set(records.map((record) => record[requestField].toString()))];
    }
    /**
     * Create the columns structure
     *
     * @param {Array<string>} groupBys Name of the fields of colGroupBys
     * @param {Object} values Values of the pivot (see PivotCache.groupBys)
     * @param {Array<string>} measures Measures
     *
     * @private
     * @returns {Array<Array<Array<string>>>} cols
     */
    _createCols(groupBys, values, measures) {
        const cols = [];
        if (groupBys.length !== 0) {
            const shouldFilterChildValues = this._shouldFilterChildValues(groupBys);
            this._fillColumns(cols, [], [], groupBys, measures, values, false, shouldFilterChildValues);
        }
        for (let field of measures) {
            cols.push([[], [field]]); // Total
        }
        return cols;
    }
    /**
     * Create the rows structure
     *
     * @param {Array<string>} groupBys Name of the fields of rowGroupBys
     * @param {Object} values Values of the pivot (see PivotCache.groupBys)
     *
     * @private
     * @returns {Array<Array<string>>} rows
     */
    _createRows(groupBys, values) {
        const rows = [];
        const shouldFilterChildValues = this._shouldFilterChildValues(groupBys);
        this._fillRows(rows, [], groupBys, values, false, shouldFilterChildValues);
        rows.push([]); // Total
        return rows;
    }
    /**
     * fill the columns structure
     *
     * @param {Array} cols Columns to fill
     * @param {Array} currentRow Current value of a row
     * @param {Array} currentCol Current value of a col
     * @param {Array<string>} groupBys Name of the fields of colGroupBys
     * @param {Array<string>} measures Measures
     * @param {Object} values Values of the pivot (see PivotCache.groupBys)
     * @param {Array<number|false} currentIds Ids used to compute the intersection
     * @param {Object} shouldFilterChildValues Dictionary specifying for each fields
     *                                         if the children should be filtered or not
     *
     * @private
     */
    _fillColumns(cols, currentRow, currentCol, groupBys, measures, values, currentIds, shouldFilterChildValues) {
        const field = groupBys[0];
        if (!field) {
            for (let measure of measures) {
                const row = currentRow.slice();
                const col = currentCol.slice();
                row.push(measure);
                col.push(row);
                cols.push(col);
            }
            return;
        }
        for (let [id, vals] of values[field] || []) {
            let ids = currentIds ? intersect(currentIds, vals) : vals;
            const newValues = shouldFilterChildValues[field] ? this._filterValues(values, ids) : values;
            const row = currentRow.slice();
            const col = currentCol.slice();
            row.push(id);
            col.push(row);
            this._fillColumns(cols, row, col, groupBys.slice(1), measures, newValues, ids, shouldFilterChildValues);
        }
    }
    /**
     * Fill the rows structure
     *
     * @param {Array} rows Rows to fill
     * @param {Array} currentRow Current value of a row
     * @param {Array<string>} groupBys Name of the fields of colGroupBys
     * @param {Object} values Values of the pivot (see PivotCache.groupBys)
     * @param {Array<number|false} currentIds Ids used to compute the intersection
     * @param {Object} shouldFilterChildValues Dictionary specifying for each fields
     *                                         if the children should be filtered or not
     *
     * @private
     */
    _fillRows(rows, currentRow, groupBys, values, currentIds, shouldFilterChildValues) {
        if (groupBys.length === 0) {
            return;
        }
        const fieldName = groupBys[0];
        for (let [id, vals] of values[fieldName] || []) {
            let ids = currentIds ? intersect(currentIds, vals) : vals;
            const newValues = shouldFilterChildValues[fieldName] ? this._filterValues(values, ids) : values;
            const row = currentRow.slice();
            row.push(id);
            rows.push(row);
            this._fillRows(rows, row, groupBys.slice(1), newValues, ids, shouldFilterChildValues);
        }
    }

    /**
     * Fills a dictionary which as keys the different fields and as value if
     * the children should be filtered or not. The value will be true if the children
     * should be filtered, and false if they should be joined.
     *
     * @param {Array<string>} groupBys Name of the fields of groupBys
     *
     * @returns {Object<string, bool>} Dictionary specifying for each fields
     *                                 if the children should be filtered(true) or joined(false)
     * @private
     */

    _shouldFilterChildValues(groupBys) {
        let joiningOn = false;
        const shouldFilterChildValues = {};
        for (const i in groupBys) {
            const fieldDesc = groupBys[i];
            const [fieldName] = fieldDesc.split(":");
            const field = this.getField(fieldName);
            const type = field ? field.type : undefined;
            const nextId = parseInt(i, 10) + 1;
            const fieldDescNext = nextId < groupBys.length ? groupBys[nextId] : undefined;
            const fieldNameNext = fieldDescNext ? fieldDescNext.split(":")[0] : undefined;
            const nextField = this.getField(fieldNameNext);
            const typeNext = nextField ? nextField.type : undefined;
            if (["date", "datetime"].includes(type)) {
                joiningOn = fieldName;
            }
            if (["date", "datetime"].includes(typeNext) && joiningOn === fieldNameNext) {
                joiningOn = false;
            }
            shouldFilterChildValues[fieldDesc] = !joiningOn;
        }
        return shouldFilterChildValues;
    }

    /**
     * This function will filter a Values Object and remove all the nodes that
     * do not contain the given ids.
     *
     * @param {Object} values All possible values at current depth in pivot
     * @param {Array} ids Ids to keep
     *
     * @private
     */
    _filterValues(values, ids) {
        let filteredValues = {};
        for (const [key, value] of Object.entries(values)) {
            const filteredLabels = [];
            value.forEach((labelValuesPair) => {
                const a = labelValuesPair[1].length ? intersect(labelValuesPair[1], ids) : [];
                if (a.length) {
                    filteredLabels.push([labelValuesPair[0], a]);
                }
            });
            if (filteredLabels.length) {
                filteredValues[key] = filteredLabels;
            }
        }
        return filteredValues;
    }
}
