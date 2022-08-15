/** @odoo-module */

import FavoriteMenu from "web.FavoriteMenu";
import { useModel } from "web.Model";

const { Component } = owl;

/**
 * Insert list view in spreadsheet menu
 *
 * This component is used to insert a list view in a spreadsheet
 */
export class InsertListSpreadsheetMenu extends Component {
    constructor() {
        super(...arguments);
        this.model = useModel("searchModel");
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        this.model.trigger("insert-list-spreadsheet");
    }

    //---------------------------------------------------------------------
    // Static
    //---------------------------------------------------------------------

    /**
     * @param {Object} env
     * @returns {boolean}
     */
    static shouldBeDisplayed(env) {
        return (
            env.view &&
            env.view.type === "list" &&
            env.action.type === "ir.actions.act_window" &&
            !env.device.isMobile
        );
    }
}

InsertListSpreadsheetMenu.props = {};
InsertListSpreadsheetMenu.template = "documents_spreadsheet.InsertListSpreadsheetMenu";

FavoriteMenu.registry.add("insert-list-spreadsheet-menu", InsertListSpreadsheetMenu, 5);
