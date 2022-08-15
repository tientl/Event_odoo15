/** @odoo-module **/

import { jsonToBase64 } from "../../js/o_spreadsheet/helpers/pivot_helpers";
import { _t } from "@web/core/l10n/translation";

/**
 * This class is an interface used to interact with
 * the server database to manipulate spreadsheet templates.
 * It hides details of the underlying "spreadsheet.template" model.
 */
export class SpreadsheetTemplateService {
    /**
     * @param {Object} orm orm service
     */
    constructor(orm) {
        this.orm = orm;
    }

    /**
     * Create a new spreadsheet template where every value
     * is copied from the existing template `spreadsheetTemplateId`,
     * except for the exported data and the thumbnail.
     * @param {number} spreadsheetTemplateId template to copy
     * @param {Object} values
     * @param {Object} values.data exported spreadsheet data
     * @param {string} values.thumbnail spreadsheet thumbnail
     * @returns {number} id of the newly created spreadsheet template
     */
    async copy(spreadsheetTemplateId, { data, thumbnail }) {
        const defaultValues = {
            data: jsonToBase64(data),
            thumbnail,
        };
        return this.orm.call("spreadsheet.template", "copy", [spreadsheetTemplateId], {
            default: defaultValues,
        });
    }

    /**
     * Create a new empty spreadsheet template
     * @returns {number} id of the newly created spreadsheet template
     */
    async createEmpty() {
        const data = {
            name: _t("Untitled spreadsheet template"),
            data: btoa("{}"),
        };
        return this.orm.create("spreadsheet.template", data);
    }

    /**
     * Save the data and thumbnail on the given template
     * @param {number} spreadsheetTemplateId
     * @param {Object} values values to save
     * @param {Object} values.data exported spreadsheet data
     * @param {string} values.thumbnail spreadsheet thumbnail
     */
    async save(spreadsheetTemplateId, { data, thumbnail }) {
        await this.orm.write("spreadsheet.template", [spreadsheetTemplateId], {
            data: jsonToBase64(data),
            thumbnail,
        });
    }

    /**
     * Save a new name for the given template
     * @param {number} spreadsheetTemplateId
     * @param {string} name
     */
    async saveName(spreadsheetTemplateId, name) {
        await this.orm.write("spreadsheet.template", [spreadsheetTemplateId], { name });
    }

    /**
     * Fetch all the necessary data to open a spreadsheet template
     * @param {number} spreadsheetTemplateId
     * @returns {Object}
     */
    async fetchData(spreadsheetTemplateId) {
        return this.orm.call("spreadsheet.template", "fetch_template_data", [spreadsheetTemplateId]);

    }
}
