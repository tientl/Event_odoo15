odoo.define("spreadsheet.DocumentsListController", function (require) {
    "use strict";

    const DocumentsListController = require("documents.DocumentsListController");
    const DocumentsControllerMixin = require("documents.controllerMixin");
    const DocumentsSpreadsheetControllerMixin = require("documents_spreadsheet.DocumentsControllerMixin");

    const SpreadsheetListController = DocumentsListController.extend(
        DocumentsSpreadsheetControllerMixin,
        {
            events: Object.assign(
                {},
                DocumentsListController.prototype.events,
                DocumentsSpreadsheetControllerMixin.events,
                DocumentsControllerMixin.events
            ),
            custom_events: Object.assign(
                {},
                DocumentsListController.prototype.custom_events,
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
    return SpreadsheetListController;
});
