/** @odoo-module */

import { UIPlugin } from "documents_spreadsheet.spreadsheet";

export default class IrMenuPlugin extends UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        this.env = config.evalContext.env;
    }

    getIrMenuNameById(menuId) {
        return this.env.services.menu.getMenu(menuId).name;
    }

    getIrMenuNameByXmlId(xmlId) {
        return this._getIrMenuByXmlId(xmlId).name;
    }

    getIrMenuIdByXmlId(xmlId) {
        return this._getIrMenuByXmlId(xmlId).id;
    }

    _getIrMenuByXmlId(xmlId) {
        const menu = this.env.services.menu.getAll().find((menu) => menu.xmlid === xmlId);
        if (!menu) {
            throw new Error(`Menu ${xmlId} not found. You may not have the required access rights.`);
        }
        return menu;
    }
}
IrMenuPlugin.getters = ["getIrMenuNameByXmlId", "getIrMenuNameById", "getIrMenuIdByXmlId"];
