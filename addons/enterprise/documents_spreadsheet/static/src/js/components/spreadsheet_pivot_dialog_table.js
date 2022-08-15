odoo.define("documents_spreadsheet.PivotDialogTable", function (require) {
    "use strict";

    class PivotDialogTable extends owl.Component {
        _onCellClicked(formula) {
            this.trigger('cell-selected', { formula });
        }
    }
    PivotDialogTable.template = "documents_spreadsheet.PivotDialogTable";
    return PivotDialogTable;
});
