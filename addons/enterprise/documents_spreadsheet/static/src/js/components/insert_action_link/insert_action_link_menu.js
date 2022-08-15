/** @odoo-module */

import FavoriteMenu from "web.FavoriteMenu";
import pyUtils from "web.py_utils";
import Domain from "web.Domain";
import { useService } from "@web/core/utils/hooks";
import { useModel } from "web.Model";
import SpreadsheetSelectorDialog from "documents_spreadsheet.SpreadsheetSelectorDialog";

const { Component } = owl;

export class InsertViewSpreadsheet extends Component {
    constructor() {
        super(...arguments);
        this.model = useModel("searchModel");
        this.spreadsheet = useService("spreadsheet");
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @private
     */
    async linkInSpreadsheet() {
        const spreadsheets = await this.rpc({
            model: "documents.document",
            method: "get_spreadsheets_to_display",
            args: [],
        });
        const dialog = new SpreadsheetSelectorDialog(this, { spreadsheets }).open();
        dialog.on("confirm", this, this._insertInSpreadsheet);
    }

    /**
     * Open a new spreadsheet or an existing one and insert a link to the action.
     * @private
     */
    async _insertInSpreadsheet({ id: spreadsheet }) {
        const actionToLink = this._getViewDescription();
        return this.spreadsheet.insertInSpreadsheet(spreadsheet, actionToLink);
    }

    _getViewDescription() {
        const irFilterValues = this.model.get("irFilterValues");
        const domain = pyUtils.assembleDomains(
            [
                Domain.prototype.arrayToString(this.env.action.domain),
                Domain.prototype.arrayToString(irFilterValues.domain),
            ],
            "AND"
        );
        const action = {
            domain,
            context: irFilterValues.context,
            modelName: this.env.action.res_model,
            views: this.env.action.views.map((view) => [false, view.type]),
        };
        return {
            viewType: this.env.view.type,
            action: action,
            name: this.env.action.name,
        };
    }

    //---------------------------------------------------------------------
    // Static
    //---------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    static shouldBeDisplayed(env) {
        return env.view && env.action.type === "ir.actions.act_window" && !env.device.isMobile;
    }
}

InsertViewSpreadsheet.props = {};
InsertViewSpreadsheet.template = "documents_spreadsheet.InsertActionSpreadsheet";

FavoriteMenu.registry.add("insert-action-link-in-spreadsheet", InsertViewSpreadsheet, 1);
