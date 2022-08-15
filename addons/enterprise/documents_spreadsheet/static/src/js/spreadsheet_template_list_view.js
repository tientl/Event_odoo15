odoo.define("documents_spreadsheet.TemplateListView", function (require) {
    "use strict";

    const ListController = require("web.ListController");
    const ListView = require("web.ListView");
    const viewRegistry = require("web.view_registry");
    const { getDataFromTemplate } = require("documents_spreadsheet.pivot_utils");

    const TemplateController = ListController.extend({
        _callButtonAction(attrs, record) {
            if (attrs.name === "create_spreadsheet") {
                this._createSpreadsheet(record);
            } else if (attrs.name === "edit_template") {
                this._editTemplate(record);
            } else {
                return this._super(...arguments);
            }
        },

        /**
         * Create a new spreadsheet based on a given template and redirect to
         * the spreadsheet.
         * @param {Object} record template
         */
        async _createSpreadsheet(record) {
            const data = await getDataFromTemplate(this._rpc.bind(this), record.data.id);
            const spreadsheetId = await this._rpc({
                model: "documents.document",
                method: "create",
                args: [
                    {
                        name: record.data.name,
                        mimetype: "application/o-spreadsheet",
                        handler: "spreadsheet",
                        raw: JSON.stringify(data),
                    },
                ],
            });
            this.do_action({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: spreadsheetId,
                },
            });
        },

        async _editTemplate(record) {
            this.do_action({
                type: "ir.actions.client",
                tag: "action_open_template",
                params: {
                    spreadsheet_id: record.data.id,
                    showFormulas: true,
                },
            });
        },
    });

    const TemplateListView = ListView.extend({
        config: Object.assign({}, ListView.prototype.config, {
            Controller: TemplateController,
        }),
    });

    viewRegistry.add("spreadsheet_template_list", TemplateListView);
    return TemplateListView;
});
