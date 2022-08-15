odoo.define("spreadsheet.DocumentsInspector", function (require) {
    "use strict";

    const DocumentsInspector = require("documents.DocumentsInspector");
    const core = require('web.core');

    const _t = core._t;

    DocumentsInspector.include({
        events: _.extend(
            {
                "click .o_document_spreadsheet": "_onOpenSpreadSheet",
            },
            DocumentsInspector.prototype.events
        ),

        init: function (parent, params) {
            this._super(...arguments);
            for (const record of this.records) {
                this.recordsData[record.id].isSheet = record.data.handler === "spreadsheet";
            }
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Compute the classes to use in DocumentsInspector.previews template
         *
         * @param {Object} record
         * @return {String}
         */
        _computeClasses: function (record) {
            let classes = this._super(...arguments);
            if (this.recordsData[record.id].isSheet) {
                classes = classes.replace(
                    "o_documents_preview_mimetype",
                    "o_documents_preview_image"
                );
            }
            return classes;
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * Open the spreadsheet
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onOpenSpreadSheet: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            const activeId = $(ev.currentTarget).data("id");
            if (activeId) {
                this.do_action({
                    type: "ir.actions.client",
                    tag: "action_open_spreadsheet",
                    params: {
                        spreadsheet_id: activeId,
                    },
                });
            }
        },

        /**
         * @override
         */
        _onDownload: function () {
            if(this.records.some(record => record.data.handler === 'spreadsheet')){
                if (this.records.length === 1) {
                    this.do_action({
                        type: "ir.actions.client",
                        tag: "action_open_spreadsheet",
                        params: {
                            spreadsheet_id: this.records[0].data.id,
                            download: true,
                        },
                    });
                }
                else {
                    this.displayNotification({
                        type: "danger",
                        message: _t("Spreadsheets mass download not yet supported.\n Download spreadsheets individually instead."),
                        sticky: false,
                    });
                    this.trigger_up('download', {
                        resIds: this.records.filter(record => record.data.handler !== 'spreadsheet').map(record => record.res_id),
                    });
                }
            }
            else{
                this._super(...arguments);
            }
        }
    });
});
