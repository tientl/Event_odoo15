odoo.define("documents_spreadsheet.KanbanController", function (require) {
    "use strict";

    const DocumentsKanbanController = require("documents.DocumentsKanbanController");
    const DocumentsControllerMixin = require("documents.controllerMixin");
    const DocumentsSpreadsheetControllerMixin = require("documents_spreadsheet.DocumentsControllerMixin");

    const SpreadsheetKanbanController = DocumentsKanbanController.extend(
        DocumentsSpreadsheetControllerMixin,
        {
            events: Object.assign(
                {},
                DocumentsKanbanController.prototype.events,
                DocumentsSpreadsheetControllerMixin.events,
                DocumentsControllerMixin.events
            ),
            custom_events: Object.assign(
                {},
                DocumentsKanbanController.prototype.custom_events,
                DocumentsSpreadsheetControllerMixin.custom_events,
                DocumentsControllerMixin.custom_events
            ),

            /**
             * @override
             */
            updateButtons() {
                this._super(...arguments);
                DocumentsControllerMixin.updateButtons.apply(this, arguments);
                DocumentsSpreadsheetControllerMixin.updateButtons.apply(this, arguments);
            },
        }
    );

    return SpreadsheetKanbanController;
});
