/** @odoo-module **/

import { createEmptySpreadsheet } from "./o_spreadsheet/helpers/helpers";
import { helpers } from "documents_spreadsheet.spreadsheet_extended";
import PivotDataSource from "./o_spreadsheet/helpers/pivot_data_source";
import { PivotView } from "@web/views/pivot/pivot_view";
import { sanitizePivot } from "./o_spreadsheet/helpers/pivot_helpers";
import SpreadsheetSelectorDialog from "documents_spreadsheet.SpreadsheetSelectorDialog";
import { sprintf } from "@web/core/utils/strings";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

const uuidGenerator = new helpers.UuidGenerator();

const { hooks } = owl;
const { onWillStart } = hooks;

patch(PivotView.prototype, "pivot_spreadsheet", {
    setup() {
        this._super.apply(this, arguments);
        this.userService = useService("user");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        onWillStart(async () => {
            this.canInsertPivot = await this.userService.hasGroup("documents.group_documents_user");
        });
    },

    async onInsertInSpreadsheet() {
        const spreadsheets = await this.orm.call(
            "documents.document",
            "get_spreadsheets_to_display",
            [],
            []
        );
        const params = {
            spreadsheets,
            title: this.env._t("Select a spreadsheet to insert your pivot"),
        };
        const dialog = new SpreadsheetSelectorDialog(this, params).open();
        dialog.on("confirm", this, this.insertInSpreadsheet);
    },

    /**
     * Get the function to be called when the spreadsheet is opened in order
     * to insert the pivot.
     *
     * @param {boolean} isEmptySpreadsheet True if the pivot is inserted in
     *                                     an empty spreadsheet, false
     *                                     otherwise
     *
     * @returns Function to call
     */
    async getCallbackBuildPivot(isEmptySpreadsheet) {
        const pivot = this.getPivotForSpreadsheet();
        const cache = await this.getPivotCache(pivot);
        return (model) => {
            if (!isEmptySpreadsheet) {
                const sheetId = uuidGenerator.uuidv4();
                const sheetIdFrom = model.getters.getActiveSheetId();
                model.dispatch("CREATE_SHEET", {
                    sheetId,
                    position: model.getters.getVisibleSheets().length,
                });
                model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
            }
            pivot.id = model.getters.getNextPivotId();
            model.dispatch("BUILD_PIVOT", {
                sheetId: model.getters.getActiveSheetId(),
                pivot,
                cache,
                anchor: [0, 0],
            });
        };
    },

    /**
     * Retrieves the pivot data from an existing view instance.
     *
     * @returns {SpreadsheetPivot}
     */
    getPivotForSpreadsheet() {
        return sanitizePivot(this.model);
    },

    async getPivotCache(pivot) {
        const dataSource = new PivotDataSource({
            rpc: this.orm,
            definition: pivot,
            model: pivot.model,
        });
        return dataSource.get({ domain: pivot.domain });
    },

    /**
     * Open a new spreadsheet or an existing one and insert the pivot in it.
     *
     * @param {number|false} spreadsheet Id of the document in which the
     *                                   pivot should be inserted. False if
     *                                   it's a new sheet
     *
     */
    async insertInSpreadsheet({ id: spreadsheet }) {
        let documentId;
        let notificationMessage;
        if (!spreadsheet) {
            documentId = await createEmptySpreadsheet(this.orm);
            notificationMessage = this.env._t("New spreadsheet created in Documents");
        } else {
            documentId = spreadsheet.id;
            notificationMessage = notificationMessage = sprintf(
                this.env._t("New sheet inserted in '%s'"),
                spreadsheet.name
            );
        }
        this.notification.add(notificationMessage, { type: "info" });
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "action_open_spreadsheet",
            params: {
                active_id: documentId,
                initCallback: await this.getCallbackBuildPivot(!spreadsheet),
            },
        });
    },
});

PivotView.buttonTemplate = "documents_spreadsheet.PivotView.buttons";

// viewRegistry.add("pivot", PivotSpreadsheetView, { force: true });
