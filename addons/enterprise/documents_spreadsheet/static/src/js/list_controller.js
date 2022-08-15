/** @odoo-module */
/* global _ */

import ListController from "web.ListController";
import SpreadsheetSelectorDialog from "documents_spreadsheet.SpreadsheetSelectorDialog";
import spreadsheet from "./o_spreadsheet/o_spreadsheet_extended";
import { _t } from "web.core";
import { createEmptySpreadsheet, removeContextUserInfo } from "./o_spreadsheet/helpers/helpers";
import { MAXIMUM_CELLS_TO_INSERT } from "./o_spreadsheet/constants";

/**
 * @typedef {import("./o_spreadsheet/plugins/core/list_plugin").SpreadsheetList} SpreadsheetList
 * @typedef {import("./o_spreadsheet/plugins/core/list_plugin").SpreadsheetListForRPC} SpreadsheetListForRPC
 */

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

ListController.include({
    async _insertListSpreadsheet() {
        const spreadsheets = await this._rpc({
            model: "documents.document",
            method: "get_spreadsheets_to_display",
            args: [],
        });
        const model = this.model.get(this.handle);
        const threshold = Math.min(model.count, model.limit);
        const columns = this._getColumnsForSpreadsheet();
        // This maxThreshold is used to ensure that there is not more than
        // MAXIMUM_CELLS_TO_INSERT to insert in the spreadsheet.
        // In the multi-user, we send the commands to the server which transfer
        // through the bus the commands. As the longpolling bus stores the
        // result in the localStorage, we have to ensure that the payload is less
        // than 5mb
        const maxThreshold = Math.floor(MAXIMUM_CELLS_TO_INSERT / columns.length);
        const params = {
            spreadsheets,
            title: _t("Select a spreadsheet to insert your list"),
            threshold,
            maxThreshold,
        };
        const dialog = new SpreadsheetSelectorDialog(this, params).open();
        dialog.on("confirm", this, this._insertInSpreadsheet);
    },

    /**
     * Get the columns of a list to insert in spreadsheet
     *
     * @private
     *
     * @returns {Array<string>} Columns name
     */
    _getColumnsForSpreadsheet() {
        const fields = this.model.get(this.handle).fields;
        return this.renderer.columns
            .filter((col) => col.tag === "field")
            .filter((col) => col.attrs.widget !== "handle")
            .filter((col) => fields[col.attrs.name].type !== "binary")
            .map((col) => col.attrs.name);
    },

    /**
     * Retrieves the list object from an existing view instance.
     *
     * @private
     *
     * @returns {SpreadsheetListForRPC}
     */
    _getListForSpreadsheet() {
        const data = this.model.get(this.handle);
        const columns = this._getColumnsForSpreadsheet();
        return {
            model: data.model,
            domain: data.domain,
            orderBy: data.orderedBy,
            context: removeContextUserInfo(data.getContext()),
            columns,
        };
    },

    /**
     * Get the function that have to be executed to insert the given list in the
     * given spreadsheet. The returned function has to be called with the model
     * of the spreadsheet and the dataSource of this list
     *
     * @private
     *
     * @param {SpreadsheetList} list
     * @param {number} linesNumber
     * @param {boolean} isNewSpreadsheet If set to false, a new sheet is
     * inserted in the spreadsheet
     *
     * @returns {Function}
     */
    _getCallbackListInsertion(list, linesNumber, isNewSpreadsheet) {
        return (model) => {
            if (!isNewSpreadsheet) {
                const sheetId = uuidGenerator.uuidv4();
                const sheetIdFrom = model.getters.getActiveSheetId();
                model.dispatch("CREATE_SHEET", {
                    sheetId,
                    position: model.getters.getVisibleSheets().length,
                });
                model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
            }
            list.id = model.getters.getNextListId();
            const fields = this.model.get(this.handle).fields;
            const types = list.columns.reduce((acc, current) => {
                acc[current] = fields[current].type;
                return acc;
            }, {});
            model.dispatch("BUILD_ODOO_LIST", {
                sheetId: model.getters.getActiveSheetId(),
                anchor: [0, 0],
                list,
                types,
                linesNumber,
            });
        };
    },
    /**
     * Open a new spreadsheet or an existing one and insert the list in it.
     *
     * @private
     *
     * @param {Object} params
     * @param {Object|false} params.id Document in which the list should be inserted. False if it's a new spreadsheet
     * @param {number} params.threshold Number of lines to insert
     *
     */
    async _insertInSpreadsheet({ id: spreadsheet, threshold }) {
        let documentId;
        let notificationMessage;
        const list = this._getListForSpreadsheet();
        if (!spreadsheet) {
            documentId = await createEmptySpreadsheet(this._rpc.bind(this));
            notificationMessage = _t("New spreadsheet created in Documents");
        } else {
            documentId = spreadsheet.id;
            notificationMessage = notificationMessage = _.str.sprintf(
                _t("New sheet inserted in '%s'"),
                spreadsheet.name
            );
        }
        this.displayNotification({
            type: "info",
            message: notificationMessage,
            sticky: false,
        });
        this.do_action({
            type: "ir.actions.client",
            tag: "action_open_spreadsheet",
            params: {
                active_id: documentId,
                initCallback: this._getCallbackListInsertion(list, threshold, !spreadsheet),
            },
        });
    },

    on_attach_callback() {
        this._super(...arguments);
        if (this.searchModel) {
            this.searchModel.on("insert-list-spreadsheet", this, this._insertListSpreadsheet);
        }
    },

    on_detach_callback() {
        this._super(...arguments);
        if (this.searchModel) {
            this.searchModel.off("insert-list-spreadsheet", this);
        }
    },
});
