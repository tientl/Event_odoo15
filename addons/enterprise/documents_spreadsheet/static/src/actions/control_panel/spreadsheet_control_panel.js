/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SpreadsheetName } from "./spreadsheet_name";
import { useService } from "@web/core/utils/hooks";

const { Component, hooks } = owl;
const { useSubEnv } = hooks;

export class SpreadsheetControlPanel extends Component {

    constructor() {
        super(...arguments);
        this.controlPanelDisplay = {
            "bottom-left": false,
            "bottom-right": false,
        }
        this.actionService = useService("action");
    }

    /**
     * Called when an element of the breadcrumbs is clicked.
     *
     * @param {string} jsId
     */
    onBreadcrumbClicked(jsId) {
        this.actionService.restore(jsId);
    }


    _toggleFavorited() {
        this.trigger("favorite-toggled");
    }
}

SpreadsheetControlPanel.template = "documents_spreadsheet.SpreadsheetControlPanel";
SpreadsheetControlPanel.components = {
    ControlPanel,
    SpreadsheetName,
};
SpreadsheetControlPanel.props = {
    spreadsheetName: String,
    isFavorited: {
        type: Boolean,
        optional: true
    },
    isSpreadsheetSynced: {
        type: Boolean,
        optional: true
    },
    numberOfConnectedUsers: {
        type: Number,
        optional: true
    },
    isReadonly: {
        type: Boolean,
        optional: true
    },
};
