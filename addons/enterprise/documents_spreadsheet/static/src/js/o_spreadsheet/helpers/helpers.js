/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { UNTITLED_SPREADSHEET_NAME } from "../../../constants";
import CommandResult from "../plugins/cancelled_reason";
import spreadsheet from "@documents_spreadsheet/js/o_spreadsheet/o_spreadsheet_loader";

const { createEmptyWorkbookData } = spreadsheet.helpers;

/**
 * Get the intersection of two arrays
 *
 * @param {Array} a
 * @param {Array} b
 *
 * @private
 * @returns {Array} intersection between a and b
 */
export function intersect(a, b) {
    return a.filter((x) => b.includes(x));
}

/**
 * Create a new empty spreadsheet
 *
 * @param {Function} rpc RPC function
 *
 * @private
 * @returns ID of the newly created spreadsheet
 */
export async function createEmptySpreadsheet(rpc) {
    let callRPC;
    if (rpc && rpc.constructor.name === "ORM") {
        callRPC = legacyRPC(rpc);
    } else {
        callRPC = rpc;
    }
    if (!callRPC) {
        throw new Error("rpc cannot be undefined");
    }
    return callRPC({
        model: "documents.document",
        method: "create",
        args: [
            {
                name: UNTITLED_SPREADSHEET_NAME,
                mimetype: "application/o-spreadsheet",
                handler: "spreadsheet",
                raw: JSON.stringify(createEmptyWorkbookData(`${_t("Sheet")}1`)),
            },
        ],
    });
}

/**
 * Remove user specific info from the context
 * @param {Object} context
 * @returns {Object}
 */
export function removeContextUserInfo(context) {
    context = { ...context };
    delete context.allowed_company_ids;
    delete context.tz;
    delete context.lang;
    delete context.uid;
    return context;
}

/**
 * Given an object of form {"1": {...}, "2": {...}, ...} get the maximum ID used
 * in this object
 * If the object has no keys, return 0
 *
 * @param {Object} o an object for which the keys are an ID
 *
 * @returns {number}
 */
export function getMaxObjectId(o) {
    const keys = Object.keys(o);
    if (!keys.length) {
        return 0;
    }
    const nums = keys.map((id) => parseInt(id, 10));
    const max = Math.max(...nums);
    return max;
}

export function checkFiltersTypeValueCombination(type, value) {
    if (value !== undefined) {
        switch (type) {
            case "text":
                if (typeof value !== "string") {
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
            case "date":
                if (typeof value !== "object" || Array.isArray(value)) {
                    // not a date
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
            case "relation":
                if (!Array.isArray(value)) {
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
        }
    }
    return CommandResult.Success;
}

/**
 * Compatibility layer between the ORM service
 * and the legacy RPC API.
 * The returned function has the same API as the legacy RPC.
 *
 * Notes:
 *    - the compatibility is incomplete and only covers what's currently
 *      needed for spreadsheet
 *    - remove when views and helpers are converted to wowl.
 * @param {Object} orm
 */
export function legacyRPC(orm) {
    return (params) => {
        params = { ...params };
        const model = params.model;
        delete params.model;
        const method = params.method;
        delete params.method;
        if ('groupBy' in params) {
            if (params.groupBy) {
                params.groupby = params.groupBy;
            }
            delete params.groupBy;
        }
        if ('orderBy' in params) {
            if (params.orderBy) {
                params.order = params.orderBy
                    .map((order) => order.name + (order.asc !== false ? " ASC" : " DESC"))
                    .join(", ");
            }
            delete params.orderBy;
        }
        const { args, ...kwargs } = params;
        return orm.call(model, method, args || [], kwargs);
    };
}
