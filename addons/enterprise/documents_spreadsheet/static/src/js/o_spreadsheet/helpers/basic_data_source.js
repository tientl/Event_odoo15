/** @odoo-module */

import spreadsheet from "../o_spreadsheet_loader";
import { legacyRPC } from "./helpers";

const { DataSource } = spreadsheet;

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef {Object} Field
 * @property {string} name Technical name of the field
 * @property {string} string Display name of the field
 * @property {string} type Type of the field
 * @property {string|undefined} relation Co model of the field (many2one, many2many, one2many)
 * @property {Array<Array<string>>|undefined} selection Possible values for a selection field
 */

/**
 * This class is the parent of Pivot and List DataSource, it contains the
 * common logic:
 * - RPC
 * - entity definition
 * - model and fields
 * - ...
 */
export class BasicDataSource extends DataSource {
    /**
     *
     * @param {Object} params
     * @param {function} params.rpc RPC function
     * @param {string} params.model Technical model name
     * @param {string} params.modelDisplayName Display model name
     * @param {Object.<string, Field>} params.fields Fields description
     */
    constructor(params) {
        super();
        if (params.rpc && params.rpc.constructor.name === "ORM") {
            this.rpc = legacyRPC(params.rpc);
        } else {
            this.rpc = params.rpc;
        }
        if (!this.rpc) {
            throw new Error("rpc cannot be undefined");
        }

        this.modelTechnicalName = params.model;
        this.modelDisplayName = params.modelDisplayName;
        this.fields = params.fields;
    }

    /**
     * Fetch the metadata, which should be fetched once.
     *
     * Metadata contains:
     * * Display name of the model
     * * Fields description of the model
     */
    async _fetchMetadata() {
        let fieldGetRPC = false;
        let modelNameRPC = false;
        if (!this.fields) {
            fieldGetRPC = this.rpc({
                model: this.modelTechnicalName,
                method: "fields_get",
            });
        }
        if (!this.modelDisplayName) {
            modelNameRPC = this.rpc({
                model: "ir.model",
                method: "search_read",
                fields: ["name"],
                domain: [["model", "=", this.modelTechnicalName]],
            });
        }
        if (fieldGetRPC) {
            this.fields = await fieldGetRPC;
        }
        if (modelNameRPC) {
            const result = await modelNameRPC;
            this.modelDisplayName = result[0] && result[0].name;
        }
        const metadata = {
            fields: this.fields,
            modelDisplayName: this.modelDisplayName,
        };
        this.fields = undefined;
        this.modelDisplayName = undefined;
        return metadata;
    }

    /**
     * Get the display name of the given field. If the name is not already
     * available, it returns the technical name
     * @param {string} technicalFieldName Technical name of the field
     * @returns {string} display name of technical name
     */
    getFieldName(technicalFieldName) {
        const field = this.getField(technicalFieldName);
        return field ? field.string : technicalFieldName;
    }

    /**
     * Return all field definitions
     *
     * @returns {Object.<string, Field>}
     */
    getFields() {
        return (this.metadata && this.metadata.fields) || {};
    }

    /**
     * Return a field description
     *
     * @param {string} fieldName
     * @returns {Field|undefined}
     */
    getField(fieldName) {
        return this.metadata && this.metadata.fields[fieldName];
    }

    /**
     * Get the display name of the model used in this source.
     * @returns {string|false} display name or technical name
     */
    getModelName() {
        return this.metadata && this.metadata.modelDisplayName;
    }
}
