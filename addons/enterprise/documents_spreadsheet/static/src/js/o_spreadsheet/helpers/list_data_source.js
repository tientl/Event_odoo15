/** @odoo-module */

import { BasicDataSource } from "./basic_data_source";
import { _t } from "web.core";
import { removeContextUserInfo } from "./helpers";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef {import("./basic_data_source").Field} Field
 * @typedef {import("../plugins/core/list_plugin").SpreadsheetListForRPC} SpreadsheetListForRPC
 */

export default class ListDataSource extends BasicDataSource {
    /**
     * @override
     *
     * @param {Object} params
     * @param {number|undefined} params.limit Number of records to fetch
     * @param {SpreadsheetListForRPC} params.definition Definition of the list
     */
    constructor(params) {
        super(params);
        this.labels = {};
        this.limit = params.limit || 0;
        this.definition = JSON.parse(JSON.stringify(params.definition));
        this.setTimeoutPromise = undefined;
        this.computedDomain = this.definition.domain;
    }

    async _fetch() {
        const data = await this.rpc({
            model: this.definition.model,
            method: "search_read",
            context: removeContextUserInfo(this.definition.context),
            domain: this.computedDomain,
            fields: this.definition.columns.filter(f => this.getField(f)),
            orderBy: this.definition.orderBy,
            limit: this.limit,
        });
        const proms = [];
        for (const column of this.definition.columns) {
            const field = this.getField(column);
            if (!field) {
                continue;
            }
            if (["one2many", "many2many"].includes(field.type)) {
                let ids = [];
                for (const record of data) {
                    ids = ids.concat(record[column]);
                }
                ids = Array.from(new Set(ids));
                for (const id of ids) {
                    proms.push(this._fetchLabel(field, id));
                }
            }
        }
        await Promise.all(proms);
        return data;
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
     * This method is used to ensure that the data source is loaded only once,
     * at the end of the evaluation process. It's done at the end to ensure that
     * the limit is correctly set.
     *
     * @private
     */
    _fetchAfterTimeout() {
        if (!this.setTimeoutPromise) {
            this.setTimeoutPromise = new Promise((resolve) => {
                setTimeout(async () => {
                    await this.get({ forceFetch: true });
                    this.setTimeoutPromise = undefined;
                    resolve();
                });
            });
        }
    }

    /**
     * Add the label for the record from the given model with the given id to
     * the cache of labels.
     *
     * @private
     *
     * @param {string} model
     * @param {string} id
     * @param {number} label
     */
    _addLabel(model, id, label) {
        if (!(model in this.labels)) {
            this.labels[model] = {};
        }
        this.labels[model][id] = label;
    }

    /**
     * Get the label for the record from the given model with the given id.
     *
     * @param {string} model
     * @param {string} id
     * @returns {string|undefined}
     */
    _getLabel(model, id) {
        return (this.labels[model] && this.labels[model][id]) || undefined;
    }

    /**
     * Fetch the label for the record from the given model with the given id.
     * Add the result to the cache of labels.
     *
     * @private
     *
     * @param {Field} field
     * @param {string} id
     */
    async _fetchLabel(field, id) {
        const model = field.relation
        let label;
        try {
            const rpc = await this.rpc({
                model,
                method: "name_get",
                args: [parseInt(id, 10)],
            });
            label = rpc;
        } catch (e) {
            label = e;
        }
        this._addLabel(model, id, label);
    }

    /**
     * Return the label to display from a value and a field
     *
     * @private
     *
     * @param {Field} field
     * @param {number} id
     *
     * @returns {string|undefined}
     */
    _getX2Many(field, id) {
        const model = field.relation;
        const label = this._getLabel(model, id);
        if (label === undefined) {
            this._fetchLabel(field, id).then(() => this.trigger("data-loaded"));
            return undefined;
        }
        if (label instanceof Error) {
            throw label;
        }
        return label;
    }

    /**
     * Get the value of a fieldName for the record at the given position.
     * @param {number} position
     * @param {string} fieldName
     *
     * @returns {string|undefined}
     */
    getRecordField(position, fieldName) {
        if (position >= this.limit) {
            this.limit = position + 1;
            this._fetchAfterTimeout();
            return undefined;
        }
        if (!this.data) {
            this._fetchAfterTimeout();
            return undefined;
        }
        const record = this.data[position];
        if (!record) {
            return "";
        }
        const field = this.getField(fieldName);
        if (!field) {
            throw new Error(_.str.sprintf(_t("The field %s does not exist or you do not have access to that field"), fieldName));
        }
        if (!(fieldName in record)) {
            this.definition.columns.push(fieldName);
            this.definition.columns = [...new Set(this.definition.columns)]; //Remove duplicates
            this._fetchAfterTimeout();
            return undefined;
        }
        if (field.type === "many2one") {
            return record[fieldName].length === 2 ? record[fieldName][1] : "";
        }
        if (field.type === "one2many" || field.type === "many2many") {
            const labels = record[fieldName].map((id) => this._getX2Many(field, id));
            return labels.join(", ");
        }
        if (field.type === "selection") {
            const key = record[fieldName];
            const value = field.selection.find((array) => array[0] === key);
            return value ? value[1] : "";
        }
        if (field.type === "boolean") {
            return record[fieldName] ? "TRUE" : "FALSE";
        }
        return record[fieldName] || "";
    }
}
