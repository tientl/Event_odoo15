/** @odoo-module alias=documents_spreadsheet.pivot_utils default=0 **/

import { _t } from "web.core";
import spreadsheet from "../o_spreadsheet_loader";
import { formats } from "../constants";
import { removeContextUserInfo } from "./helpers";

const { Model } = spreadsheet;

/**
 * @typedef {import("../plugins/core/pivot_plugin").SpreadsheetPivotForRPC} SpreadsheetPivotForRPC
 */

export const pivotFormulaRegex = /^=.*PIVOT/;

export const PERIODS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    quarter: _t("Quarter"),
    year: _t("Year"),
};

//--------------------------------------------------------------------------
// Public
//--------------------------------------------------------------------------

/**
 * Format a data
 *
 * @param {string} field fieldName:interval
 * @param {string} value
 */
export function formatDate(field, value) {
    const interval = field.split(":")[1];
    const output = formats[interval].display;
    const input = formats[interval].out;
    const date = moment(value, input);
    return date.isValid() ? date.format(output) : _t("(Undefined)");
}

/**
 * Create the pivot object
 *
 * @param {PivotModel} instance of PivotModel
 *
 * @returns {Pivot}
 */
export function sanitizePivot(pivotModel) {
    let measures = _sanitizeFields(pivotModel.metaData.activeMeasures, pivotModel.metaData.measures);
    measures = pivotModel.metaData.activeMeasures.map((measure) => {
        const fieldName = measure.split(":")[0];
        const fieldDesc = pivotModel.metaData.measures[fieldName];
        const operator =
            (fieldDesc.group_operator && fieldDesc.group_operator.toLowerCase()) ||
            (fieldDesc.type === "many2one" ? "count_distinct" : "sum");
        return {
            field: measure,
            operator,
        };
    });
    const rowGroupBys = _sanitizeFields(pivotModel.metaData.fullRowGroupBys, pivotModel.metaData.fields);
    const colGroupBys = _sanitizeFields(pivotModel.metaData.fullColGroupBys, pivotModel.metaData.fields);
    return {
        model: pivotModel.metaData.resModel,
        rowGroupBys,
        colGroupBys,
        measures,
        domain: pivotModel.searchParams.domain,
        context: removeContextUserInfo(pivotModel.searchParams.context),
    };
}

/**
 * Takes a template id as input, will convert the formulas
 * from relative to absolute in a way that they can be used to create a sheet.
 *
 * @param {Function} rpc
 * @param {number} templateId
 * @returns {Promise<Object>} spreadsheetData
 */
export async function getDataFromTemplate(rpc, templateId) {
    let [{ data }] = await rpc({
        method: "read",
        model: "spreadsheet.template",
        args: [templateId, ["data"]],
    });
    data = base64ToJson(data);
    const model = new Model(data, {
        mode: "headless",
        evalContext: {
            env: {
                delayedRPC: rpc,
                services: { rpc },
            },
        },
    });
    await model.waitForIdle();
    model.dispatch("CONVERT_PIVOT_FROM_TEMPLATE");
    return model.exportData();
}

//--------------------------------------------------------------------------
// Private
//--------------------------------------------------------------------------

/**
 * Add a default interval for the date and datetime fields
 *
 * @param {Array<string>} fields List of the fields to sanitize
 * @param {Object} allFields fields_get result
 */
function _sanitizeFields(fields, allFields) {
    return fields.map((field) => {
        let [fieldName, group] = field.split(":");
        const fieldDesc = allFields[fieldName];
        if (["date", "datetime"].includes(fieldDesc.type)) {
            if (!group) {
                group = "month";
            }
            return `${fieldName}:${group}`;
        }
        return fieldName;
    });
}

/**
 * see https://stackoverflow.com/a/30106551
 * @param {string} string
 * @returns {string}
 */
function utf8ToBase64(str) {
    // first we use encodeURIComponent to get percent-encoded UTF-8,
    // then we convert the percent encodings into raw bytes which
    // can be fed into btoa.
    return btoa(
        encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, function toSolidBytes(match, p1) {
            return String.fromCharCode("0x" + p1);
        })
    );
}

/**
 * see https://stackoverflow.com/a/30106551
 * @param {string} string
 * @returns {string}
 */
function base64ToUtf8(str) {
    // Going backwards: from bytestream, to percent-encoding, to original string.
    return decodeURIComponent(
        atob(str)
            .split("")
            .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
            .join("")
    );
}

/**
 * Encode a json to a base64 string
 * @param {object} json
 */
export function jsonToBase64(json) {
    return utf8ToBase64(JSON.stringify(json));
}

/**
 * Decode a base64 encoded json
 * @param {string} string
 */
export function base64ToJson(string) {
    return JSON.parse(base64ToUtf8(string));
}
