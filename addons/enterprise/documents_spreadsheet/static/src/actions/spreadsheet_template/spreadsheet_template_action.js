/** @odoo-module **/

import SpreadsheetComponent from "documents_spreadsheet.SpreadsheetComponent";
import { SpreadsheetControlPanel } from "../control_panel/spreadsheet_control_panel";
import { base64ToJson } from "../../js/o_spreadsheet/helpers/pivot_helpers"
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { SpreadsheetTemplateService } from "./spreadsheet_template_service";
import { AbstractSpreadsheetAction } from "../abstract_spreadsheet_action";

const { useRef } = owl.hooks;

export class SpreadsheetTemplateAction extends AbstractSpreadsheetAction {
    setup() {
        super.setup();
        this.notificationMessage = this.env._t("New spreadsheet template created");
        const orm = useService("orm");
        this.service = new SpreadsheetTemplateService(orm);
        this.spreadsheetRef = useRef("spreadsheet");
    }

    _loadData(record) {
        this.spreadsheetData = base64ToJson(record.data);
        this.state.spreadsheetName = record.name;
        this.isReadonly = record.isReadonly;
    }
}
SpreadsheetTemplateAction.template = "documents_spreadsheet.SpreadsheetTemplateAction"
SpreadsheetTemplateAction.components = {
    SpreadsheetComponent,
    SpreadsheetControlPanel,
};

registry
    .category("actions")
    .add("action_open_template", SpreadsheetTemplateAction);
