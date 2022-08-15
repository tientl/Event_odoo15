/** @odoo-module alias=documents_spreadsheet.TestUtils default=0 */
import spreadsheet from "documents_spreadsheet.spreadsheet";
import pivotUtils from "documents_spreadsheet.pivot_utils";
import { createView } from "web.test_utils";
import ListView from "web.ListView";
import MockServer from "web.MockServer";
import makeTestEnvironment from "web.test_env";
import LegacyRegistry from "web.Registry";
import MockSpreadsheetCollaborativeChannel from "./mock_spreadsheet_collaborative_channel";
import { getBasicPivotArch, getBasicData, getBasicListArch } from "./spreadsheet_test_data";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { SpreadsheetAction } from "../src/actions/spreadsheet/spreadsheet_action";
import { SpreadsheetTemplateAction } from "../src/actions/spreadsheet_template/spreadsheet_template_action";
import { UNTITLED_SPREADSHEET_NAME } from "../src/constants";
import { PivotView } from "@web/views/pivot/pivot_view";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";
import { spreadsheetService } from "@documents_spreadsheet/actions/spreadsheet/spreadsheet_service";
import { nextTick } from "@web/../tests/helpers/utils";

const { Model } = spreadsheet;
const { toCartesian, toZone } = spreadsheet.helpers;
const { jsonToBase64 } = pivotUtils;
const { loadJS } = owl.utils;

const serviceRegistry = registry.category("services");

export async function waitForEvaluation(model) {
    /**
     * Here, we need to wait for two nextTick:
     * The first one to resolve the name_get that could be triggered by the evaluation
     * The second one to resolve the debounce method of the evaluation
     */
    await model.waitForIdle();
    await nextTick();
    await nextTick();
}

/**
 * Get the value of the given cell
 */
export function getCellValue(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const cell = model.getters.getCell(sheetId, ...toCartesian(xc));
    if (!cell) {
        return undefined;
    }
    return cell.evaluated.value;
}

/**
 * Add a global filter and ensure the data sources are completely reloaded
 */
export async function addGlobalFilter(model, filter) {
    const result = model.dispatch("ADD_GLOBAL_FILTER", filter);
    await waitForEvaluation(model);
    return result;
}

/**
 * Remove a global filter and ensure the data sources are completely reloaded
 */
export async function removeGlobalFilter(model, id) {
    const result = model.dispatch("REMOVE_GLOBAL_FILTER", { id });
    await waitForEvaluation(model);
    return result;
}

/**
 * Edit a global filter and ensure the data sources are completely reloaded
 */
export async function editGlobalFilter(model, filter) {
    const result = model.dispatch("EDIT_GLOBAL_FILTER", filter);
    await waitForEvaluation(model);
    return result;
}

/**
 * Set the value of a global filter and ensure the data sources are completely
 * reloaded
 */
export async function setGlobalFilterValue(model, payload) {
    const result = model.dispatch("SET_GLOBAL_FILTER_VALUE", payload);
    await waitForEvaluation(model);
    return result;
}

/**
 * Get the computed value that would be autofilled starting from the given xc
 */
export function getAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getPivotNextAutofillValue(content, column, increment);
}

/**
 * Get the computed value that would be autofilled starting from the given xc
 */
export function getListAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getNextListValue(content, column, increment);
}

/**
 * Autofill from a zone to a cell
 */
export function autofill(model, from, to) {
    setSelection(model, from);
    const [col, row] = toCartesian(to);
    model.dispatch("AUTOFILL_SELECT", { col, row });
    model.dispatch("AUTOFILL");
}

/**
 * Set the selection
 */
export function setSelection(model, xc) {
    const zone = toZone(xc);
    const anchor = [zone.left, zone.top];
    model.dispatch("SET_SELECTION", {
        anchorZone: zone,
        anchor,
        zones: [zone],
    });
}

/**
 * Get the cell of the given xc
 */
export function getCell(model, xc, sheetId = model.getters.getActiveSheetId()) {
    return model.getters.getCell(sheetId, ...toCartesian(xc));
}

/**
 * Get the cells of the given sheet (or active sheet if not provided)
 */
export function getCells(model, sheetId = model.getters.getActiveSheetId()) {
    return model.getters.getCells(sheetId);
}

/**
 * Get the formula of the given xc
 */
export function getCellFormula(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const cell = getCell(model, xc, sheetId);
    return cell && cell.isFormula() ? model.getters.getFormulaCellContent(sheetId, cell) : "";
}

/**
 * Get the content of the given xc
 */
export function getCellContent(model, xc, sheetId = undefined) {
    if (sheetId === undefined) {
        sheetId =
            model.config.mode === "headless"
                ? model.getters.getVisibleSheets()[0]
                : model.getters.getActiveSheetId();
    }
    const cell = getCell(model, xc, sheetId);
    return cell ? model.getters.getCellText(cell, sheetId, true) : "";
}

/**
 * Get the list of the merges (["A1:A2"]) of the sheet
 */
export function getMerges(model, sheetId = model.getters.getActiveSheetId()) {
    return model.exportData().sheets.find((sheet) => sheet.id === sheetId).merges;
}

/**
 * Set the content of a cell
 */
export function setCellContent(model, xc, content, sheetId = undefined) {
    if (sheetId === undefined) {
        sheetId =
            model.config.mode === "headless"
                ? model.getters.getVisibleSheets()[0]
                : model.getters.getActiveSheetId();
    }
    const [col, row] = toCartesian(xc);
    model.dispatch("UPDATE_CELL", { col, row, sheetId, content });
}

/**
 * Return the odoo spreadsheet component
 * @param {*} actionManager
 * @returns {Component}
 */
function getSpreadsheetComponent(actionManager) {
    return actionManager.spreadsheetRef.comp;
}

/**
 * Return the o-spreadsheet component
 * @param {*} actionManager
 * @returns {Component}
 */
function getOSpreadsheetComponent(actionManager) {
    return getSpreadsheetComponent(actionManager).spreadsheet.comp;
}

/**
 * Return the o-spreadsheet Model
 */
function getSpreadsheetActionModel(actionManager) {
    return getOSpreadsheetComponent(actionManager).model;
}

function getSpreadsheetActionEnv(actionManager) {
    const model = getSpreadsheetActionModel(actionManager);
    const component = getSpreadsheetComponent(actionManager);
    const oComponent = getOSpreadsheetComponent(actionManager);
    return {
        ...component.env,
        getters: model.getters,
        dispatch: model.dispatch,
        services: model.config.evalContext.env.services,
        openSidePanel: oComponent.openSidePanel.bind(oComponent),
        openLinkEditor: oComponent.openLinkEditor.bind(oComponent),
    };
}

export async function createSpreadsheetAction(actionTag, params = {}) {
    await loadJS("/web/static/lib/Chart/Chart.js");
    let { spreadsheetId, data, arch, mockRPC, legacyServicesRegistry, webClient } = params;
    let spreadsheetAction;
    const SpreadsheetActionComponent =
        actionTag === "action_open_spreadsheet" ? SpreadsheetAction : SpreadsheetTemplateAction;
    patchWithCleanup(SpreadsheetActionComponent.prototype, {
        setup() {
            this._super();
            spreadsheetAction = this;
        },
    });
    // TODO convert tests to use "serverData"
    const serverData = params.serverData || { models: data, views: arch };
    if (!webClient) {
        serviceRegistry.add("spreadsheet", spreadsheetService);
        webClient = await createWebClient({
            serverData,
            mockRPC,
            legacyParams: {
                withLegacyMockServer: true,
                serviceRegistry: legacyServicesRegistry,
            },
        });
        const legacyEnv = owl.Component.env;
        legacyEnv.services.spreadsheet = webClient.env.services.spreadsheet;
    }

    const transportService = params.transportService || new MockSpreadsheetCollaborativeChannel();
    await doAction(webClient, {
        type: "ir.actions.client",
        tag: actionTag,
        params: {
            spreadsheet_id: spreadsheetId,
            transportService,
        },
    },
    { clearBreadcrumbs: true } // Sometimes in test defining custom action, Odoo opens on the action instead of opening on root
    );
    return {
        webClient,
        model: getSpreadsheetActionModel(spreadsheetAction),
        env: getSpreadsheetActionEnv(spreadsheetAction),
    };
}

export async function createSpreadsheet(params = {}) {
    if (!params.spreadsheetId) {
        const models = params.serverData ? params.serverData.models : params.data
        const documents = models["documents.document"].records;
        const spreadsheetId = Math.max(...documents.map((d) => d.id)) + 1;
        documents.push({
            id: spreadsheetId,
            name: UNTITLED_SPREADSHEET_NAME,
            raw: "{}",
        });
        params = { ...params, spreadsheetId };
    }
    return createSpreadsheetAction("action_open_spreadsheet", params);
}

export async function createSpreadsheetTemplate(params = {}) {
    if (!params.spreadsheetId) {
        const templates = params.data["spreadsheet.template"].records;
        const spreadsheetId = Math.max(...templates.map((d) => d.id)) + 1;
        templates.push({
            id: spreadsheetId,
            name: "test template",
            data: jsonToBase64({}),
        });
        params = { ...params, spreadsheetId };
    }
    return createSpreadsheetAction("action_open_template", params);
}

/**
 * Create a spreadsheet model from a List controller
 */
export async function createSpreadsheetFromList(params = {}) {
    await loadJS("/web/static/lib/Chart/Chart.js");
    let { actions, listView, webClient, linesNumber } = params;
    if (linesNumber === undefined) {
        linesNumber = 10;
    }
    if (!listView) {
        listView = {};
    }
    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetAction.prototype, {
        mounted() {
            this._super();
            spreadsheetAction = this;
        },
    });
    listView = {
        arch: getBasicListArch(),
        data: getBasicData(),
        model: listView.model || "partner",
        ...listView,
    };
    const { data } = listView;
    if (!webClient) {
        serviceRegistry.add("spreadsheet", spreadsheetService);
        const serverData = { models: data, views: listView.archs };
        webClient = await createWebClient({
            serverData,
            legacyParams: { withLegacyMockServer: true },
            mockRPC: listView.mockRPC,
        });
        const legacyEnv = owl.Component.env;
        legacyEnv.services.spreadsheet = webClient.env.services.spreadsheet;
    }
    const controller = await createView({
        View: ListView,
        ...listView,
    });
    const documents = data["documents.document"].records;
    const id = Math.max(...documents.map((d) => d.id)) + 1;
    documents.push({
        id,
        name: "pivot spreadsheet",
        raw: "{}",
    });
    if (listView.services) {
        const serviceRegistry = new LegacyRegistry();
        for (const sname in listView.services) {
            serviceRegistry.add(sname, listView.services[sname]);
        }
    }
    if (actions) {
        await actions(controller);
    }
    const transportService = new MockSpreadsheetCollaborativeChannel();

    const list = controller._getListForSpreadsheet();
    const initCallback = controller._getCallbackListInsertion(list, linesNumber, true);
    await doAction(webClient, {
        type: "ir.actions.client",
        tag: "action_open_spreadsheet",
        params: {
            spreadsheet_id: id,
            transportService,
            initCallback,
        },
    });
    const spreadSheetComponent = spreadsheetAction.spreadsheetRef.comp;
    const oSpreadsheetComponent = spreadSheetComponent.spreadsheet.comp;
    const model = oSpreadsheetComponent.model;
    const env = Object.assign(spreadSheetComponent.env, {
        getters: model.getters,
        dispatch: model.dispatch,
        services: model.config.evalContext.env.services,
        openSidePanel: oSpreadsheetComponent.openSidePanel.bind(oSpreadsheetComponent),
    });
    await waitForEvaluation(model);
    return {
        webClient,
        env,
        model,
        transportService,
        get spreadsheetAction() {
            return spreadsheetAction;
        },
    };
}

/**
 * Create a spreadsheet with both a pivot and a list view.
 * The pivot is on the first sheet, the list is on the second.
 */
export async function createSpreadsheetWithPivotAndList() {
    // In createSpreadsheetFromPivot, we will reuse the webclient created in
    // createSpreadsheetFromList. We must be sure that it is configured in a
    // as similarly in createSpreadsheetFromPivot.
    const listView = {
        archs: {
            "partner,false,pivot": getBasicPivotArch(),
            "partner,false,search": `<search/>`
        },
    };
    if (!serviceRegistry.contains("user")) {
        serviceRegistry.add("user", makeFakeUserService(() => true));
    }

    const { model: listModel, webClient: listWebClient } = await createSpreadsheetFromList({ listView });
    const { model, webClient, env } = await createSpreadsheetFromPivot({
        webClient: listWebClient,
    });

    model.dispatch("CREATE_SHEET", {
        sheetId: "LIST",
        position: model.getters.getVisibleSheets().length,
    });
    const list = listModel.getters.getListForRPC("1");
    list.id = "1";
    const types = {
        foo: "integer",
        bar: "boolean",
        date: "date",
        product_id: "many2one",
    };
    model.dispatch("BUILD_ODOO_LIST", {
        sheetId: "LIST",
        anchor: [0, 0],
        list,
        linesNumber: 10,
        types,
    });
    await waitForEvaluation(model);
    return { model, webClient, env };
}

/**
 * Create a spreadsheet model from a Pivot controller
 * @param {*} params
 * the pivot data
 */
export async function createSpreadsheetFromPivot(params = {}) {
    await loadJS("/web/static/lib/Chart/Chart.js");
    let { actions, pivotView, webClient, legacyServicesRegistry } = params;

    if (!pivotView) {
        pivotView = {};
    }

    if (!pivotView.model) {
        pivotView.model = "partner";
    }

    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            this._super();
            spreadsheetAction = this;
        },
    });

    let pivot = null;
    patchWithCleanup(PivotView.prototype, {
        setup() {
            this._super();
            pivot = this;
        },
    });

    let views = null;
    if (pivotView.archs) {
        views = pivotView.archs;
    } else if (pivotView.arch) {
        views = {};
        views[`${pivotView.model},false,pivot`] = pivotView.arch;
        views[`${pivotView.model},false,search`] = `<search/>`;
    } else {
        views = { "partner,false,pivot": getBasicPivotArch(), "partner,false,search": `<search/>` };
    }
    const serverData = {
        models: pivotView.data || getBasicData(),
        views: views,
    };
    if (!webClient) {
        if (!serviceRegistry.contains("user")) {
            serviceRegistry.add("user", makeFakeUserService(() => true));
        }
        serviceRegistry.add("spreadsheet", spreadsheetService);
        webClient = await createWebClient({
            serverData,
            legacyParams: {
                withLegacyMockServer: true,
                serviceRegistry: legacyServicesRegistry,
            },
            mockRPC: function (route, args) {
                if (pivotView.mockRPC) {
                    return pivotView.mockRPC(route, args);
                }
            },
        });
        const legacyEnv = owl.Component.env;
        legacyEnv.services.spreadsheet = webClient.env.services.spreadsheet;
    }
    await doAction(webClient, {
        name: "pivot view",
        res_model: pivotView.model,
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
        domain: pivotView.domain,
    });

    if (actions) {
        await actions(pivot);
    }

    const documents = serverData.models["documents.document"].records;
    const id = Math.max(...documents.map((d) => d.id)) + 1;
    documents.push({
        id,
        name: "pivot spreadsheet",
        raw: "{}",
    });

    const transportService = new MockSpreadsheetCollaborativeChannel();
    await doAction(webClient, {
        type: "ir.actions.client",
        tag: "action_open_spreadsheet",
        params: {
            spreadsheet_id: id,
            transportService,
            initCallback: await pivot.getCallbackBuildPivot(true),
        },
    });
    const spreadSheetComponent = spreadsheetAction.spreadsheetRef.comp;
    const oSpreadsheetComponent = spreadSheetComponent.spreadsheet.comp;
    const model = oSpreadsheetComponent.model;
    const env = Object.assign(spreadSheetComponent.env, {
        getters: model.getters,
        dispatch: model.dispatch,
        services: model.config.evalContext.env.services,
        openSidePanel: oSpreadsheetComponent.openSidePanel.bind(oSpreadsheetComponent),
    });
    await waitForEvaluation(model);
    return {
        webClient,
        env,
        model,
        transportService,
        get spreadsheetAction() {
            return spreadsheetAction;
        },
    };
}

/**
 * Setup a realtime collaborative test environment, with the given data
 */
export function setupCollaborativeEnv(data) {
    const mockServer = new MockServer(data, {});
    const env = makeTestEnvironment({}, mockServer.performRpc.bind(mockServer));
    env.delayedRPC = env.services.rpc;
    const network = new MockSpreadsheetCollaborativeChannel();
    const model = new Model();
    const alice = new Model(model.exportData(), {
        evalContext: { env },
        transportService: network,
        client: { id: "alice", name: "Alice" },
    });
    const bob = new Model(model.exportData(), {
        evalContext: { env },
        transportService: network,
        client: { id: "bob", name: "Bob" },
    });
    const charlie = new Model(model.exportData(), {
        evalContext: { env },
        transportService: network,
        client: { id: "charlie", name: "Charlie" },
    });
    return { network, alice, bob, charlie, rpc: env.services.rpc };
}

export function joinSession(spreadsheetChannel, client) {
    spreadsheetChannel.broadcast({
        type: "CLIENT_JOINED",
        client: {
            position: {
                sheetId: "1",
                col: 1,
                row: 1,
            },
            name: "Raoul Grosbedon",
            ...client,
        },
    });
}

export function leaveSession(spreadsheetChannel, clientId) {
    spreadsheetChannel.broadcast({
        type: "CLIENT_LEFT",
        clientId,
    });
}

QUnit.assert.spreadsheetIsSynchronized = function (users, callback, expected) {
    for (const user of users) {
        const actual = callback(user);
        if (!QUnit.equiv(actual, expected)) {
            const userName = user.getters.getClient().name;
            return this.pushResult({
                result: false,
                actual,
                expected,
                message: `${userName} does not have the expected value`,
            });
        }
    }
    this.pushResult({ result: true });
};
