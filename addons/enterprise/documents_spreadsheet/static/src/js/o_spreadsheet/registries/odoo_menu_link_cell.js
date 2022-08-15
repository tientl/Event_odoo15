/** @odoo-module */

import spreadsheet from "../o_spreadsheet_loader";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { IrMenuSelector } from "../../components/ir_menu_selector/ir_menu_selector";

const { cellRegistry, linkMenuRegistry } = spreadsheet.registries;
const { LinkCell } = spreadsheet.cellTypes;
const { isMarkdownLink, parseMarkdownLink } = spreadsheet.helpers;

const VIEW_PREFIX = "odoo://view/";
const IR_MENU_ID_PREFIX = "odoo://ir_menu_id/";
const IR_MENU_XML_ID_PREFIX = "odoo://ir_menu_xml_id/";

/**
 * @typedef Action
 * @property {Array} domain
 * @property {Object} context
 * @property {string} modelName
 * @property {string} orderBy
 * @property {Array<[boolean, string]} views
 *
 * @typedef ViewLinkDescription
 * @property {string} name Action name
 * @property {Action} action
 * @property {string} viewType Type of view (list, pivot, ...)
 */

/**
 *
 * @param {string} str
 * @returns {boolean}
 */
function isMarkdownViewLink(str) {
    if (!isMarkdownLink(str)) {
        return false;
    }
    const { url } = parseMarkdownLink(str);
    return url.startsWith(VIEW_PREFIX);
}

/**
 *
 * @param {string} viewLink
 * @returns {ViewLinkDescription}
 */
function parseViewLink(viewLink) {
    if (viewLink.startsWith(VIEW_PREFIX)) {
        return JSON.parse(viewLink.substr(VIEW_PREFIX.length))
    }
    throw new Error(`${viewLink} is not a valid view link`);
}

/**
 * @param {ViewLinkDescription} viewDescription Id of the ir.filter
 * @returns {string}
 */
export function buildViewLink(viewDescription) {
    return `${VIEW_PREFIX}${JSON.stringify(viewDescription)}`;
}

/**
 *
 * @param {string} str
 * @returns
 */
function isMarkdownIrMenuIdLink(str) {
    if (!isMarkdownLink(str)) {
        return false;
    }
    const { url } = parseMarkdownLink(str);
    return url.startsWith(IR_MENU_ID_PREFIX);
}

/**
 *
 * @param {string} irMenuLink
 * @returns ir.ui.menu record id
 */
function parseIrMenuIdLink(irMenuLink) {
    if (irMenuLink.startsWith(IR_MENU_ID_PREFIX)) {
        return parseInt(irMenuLink.substr(IR_MENU_ID_PREFIX.length), 10);
    }
    throw new Error(`${irMenuLink} is not a valid menu id link`);
}

/**
 * @param {number} menuId
 * @returns
 */
export function buildIrMenuIdLink(menuId) {
    return `${IR_MENU_ID_PREFIX}${menuId}`;
}

/**
 *
 * @param {string} str
 * @returns
 */
function isMarkdownIrMenuXmlLink(str) {
    if (!isMarkdownLink(str)) {
        return false;
    }
    const { url } = parseMarkdownLink(str);
    return url.startsWith(IR_MENU_XML_ID_PREFIX);
}

/**
 *
 * @param {string} irMenuLink
 * @returns ir.ui.menu record id
 */
function parseIrMenuXmlLink(irMenuLink) {
    if (irMenuLink.startsWith(IR_MENU_XML_ID_PREFIX)) {
        return irMenuLink.substr(IR_MENU_XML_ID_PREFIX.length);
    }
    throw new Error(`${irMenuLink} is not a valid menu xml link`);
}
/**
 * @param {number} menuXmlId
 * @returns
 */
function buildIrMenuXmlLink(menuXmlId) {
    return `${IR_MENU_XML_ID_PREFIX}${menuXmlId}`;
}

class OdooMenuLinkCell extends LinkCell {
    constructor(id, content, menuId, menuName, properties = {}) {
        super(id, content, properties);
        this.urlRepresentation = menuName;
        this.isUrlEditable = false;
        this._irMenuId = menuId;
    }

    action(env) {
        const menu = env.services.menu.getMenu(this._irMenuId);
        env.services.action.doAction(menu.actionID);
    }
}

class OdooViewLinkCell extends LinkCell {
    /**
     *
     * @param {string} id
     * @param {string} content
     * @param {ViewLinkDescription} actionDescription
     * @param {Object} properties
     */
    constructor(id, content, actionDescription, properties = {}) {
        super(id, content, properties);
        this.urlRepresentation = actionDescription.name;
        this.isUrlEditable = false;
        this._viewType = actionDescription.viewType;
        /** @type {Action} */
        this._action = actionDescription.action;
    }

    action(env) {
        env.services.action.doAction({
            type: "ir.actions.act_window",
            name: this.urlRepresentation,
            res_model: this._action.modelName,
            views: this._action.views,
            target: 'current',
            domain: this._action.domain,
            context: this._action.context,
        }, {
            viewType: this._viewType,
        });
    }
}
export const spreadsheetLinkMenuCellService = {
    dependencies: ["menu"],
    start(env) {
        function _getIrMenuByXmlId(xmlId) {
            const menu = env.services.menu.getAll().find((menu) => menu.xmlid === xmlId);
            if (!menu) {
                throw new Error(`Menu ${xmlId} not found. You may not have the required access rights.`);
            }
            return menu;
        };

        cellRegistry.add("OdooMenuIdLink", {
            sequence: 65,
            match: isMarkdownIrMenuIdLink,
            createCell: (id, content, properties, sheetId, getters) => {
                const { url } = parseMarkdownLink(content);
                const menuId = parseIrMenuIdLink(url);
                const menuName = env.services.menu.getMenu(menuId).name;
                return new OdooMenuLinkCell(id, content, menuId, menuName, properties);
            },
        }).add("OdooMenuXmlLink", {
            sequence: 66,
            match: isMarkdownIrMenuXmlLink,
            createCell: (id, content, properties, sheetId, getters) => {
                const { url } = parseMarkdownLink(content);
                const xmlId = parseIrMenuXmlLink(url);
                const menuId = _getIrMenuByXmlId(xmlId).id;
                const menuName = _getIrMenuByXmlId(xmlId).name;
                return new OdooMenuLinkCell(id, content, menuId, menuName, properties);
            },
        }).add("OdooIrFilterLink", {
            sequence: 67,
            match: isMarkdownViewLink,
            createCell: (id, content, properties, sheetId, getters) => {
                const { url } = parseMarkdownLink(content);
                const actionDescription = parseViewLink(url);
                return new OdooViewLinkCell(id, content, actionDescription, properties);
            },
        });

        return true;
    },
};

registry.category("services").add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);

linkMenuRegistry.add("odooMenu", {
    name: _lt("Link an Odoo menu"),
    sequence: 20,
    action: async (env) => {
        return new Promise((resolve) => {
            const closeDialog = env.services.dialog.add(IrMenuSelector, {
                onMenuSelected: (menuId) => {
                    closeDialog();
                    const menu = env.services.menu.getMenu(menuId);
                    const xmlId = menu && menu.xmlid;
                    const url = xmlId ? buildIrMenuXmlLink(xmlId) : buildIrMenuIdLink(menuId);
                    const name = menu.name;
                    const link = { url, label: name };
                    resolve({
                        link,
                        isUrlEditable: false,
                        urlRepresentation: name,
                    });
                },
            });
        });
    },
});
