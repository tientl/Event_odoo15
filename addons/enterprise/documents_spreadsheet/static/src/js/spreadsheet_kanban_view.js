odoo.define("documents_spreadsheet.KanbanView", function (require) {
    "use strict";

    const SpreadsheetKanbanController = require("documents_spreadsheet.KanbanController");
    const KanbanView = require("documents.DocumentsKanbanView");
    const viewRegistry = require("web.view_registry");

    const SpreadsheetKanbanView = KanbanView.extend({
        config: Object.assign({}, KanbanView.prototype.config, {
            Controller: SpreadsheetKanbanController,
        }),
    });

    viewRegistry.add("documents_kanban", SpreadsheetKanbanView);
    return SpreadsheetKanbanView;
});
