odoo.define("spreadsheet.DocumentsKanbanRecord", function (require) {
    "use strict";

    const DocumentsKanbanRecord = require("documents.DocumentsKanbanRecord");

    DocumentsKanbanRecord.include({
        events: _.extend(
            {
                "click .o_document_spreadsheet": "_onOpenSheet",
            },
            DocumentsKanbanRecord.prototype.events
        ),

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onOpenSheet(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            if (this.state.data.handler === "spreadsheet") {
                const activeId = this.state.data.id;
                if (activeId) {
                    this.do_action({
                        type: "ir.actions.client",
                        tag: "action_open_spreadsheet",
                        params: {
                            spreadsheet_id: activeId,
                        },
                    });
                }
            }
        },
    });
});
