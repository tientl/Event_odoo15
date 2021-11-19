/** @odoo-module */

import { registry } from "@web/core/registry";

registry
    .category("mock_server")
    .add("documents.document/get_spreadsheets_to_display", function (route, args) {
        return this.models["documents.document"].records
            .filter((document) => document.handler === "spreadsheet")
            .map((spreadsheet) => ({
                name: spreadsheet.name,
                id: spreadsheet.id,
            }));
    })
    .add("documents.document/join_spreadsheet_session", function (route, args) {
        const [id] = args.args;
        const record = this.models["documents.document"].records.find((record) => record.id === id);
        if (!record) {
            throw new Error(`Spreadsheet ${id} does not exist`);
        }
        return {
            raw: record.raw,
            name: record.name,
            is_favorited: record.is_favorited,
            revisions: [],
            isReadonly: false
        };
    })
    .add("documents.document/dispatch_spreadsheet_message", () => false)
    .add("spreadsheet.template/fetch_template_data", function (route, args) {
        const [id] = args.args;
        const record = this.models["spreadsheet.template"].records.find((record) => record.id === id);
        if (!record) {
            throw new Error(`Spreadsheet Template ${id} does not exist`);
        }
        return {
            data: record.data,
            name: record.name,
            isReadonly: false
        };
    });
