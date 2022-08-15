/** @odoo-module alias=documents_spreadsheet.PivotTemplateTests */

import { nextTick, dom, fields, createView } from "web.test_utils";
import pivotUtils from "documents_spreadsheet.pivot_utils";
import DocumentsKanbanView from "documents_spreadsheet.KanbanView";
import CommandResult from "../src/js/o_spreadsheet/plugins/cancelled_reason";
import DocumentsListView from "documents_spreadsheet.ListView";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import TemplateListView from "documents_spreadsheet.TemplateListView";
import { afterEach, beforeEach } from "@mail/utils/test_utils";
import { createDocumentsView } from "documents.test_utils";
import spreadsheet from "../src/js/o_spreadsheet/o_spreadsheet_extended";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { SpreadsheetTemplateAction } from "../src/actions/spreadsheet_template/spreadsheet_template_action";

import {
    createSpreadsheetFromPivot,
    setCellContent,
    getCellContent,
    getCellValue,
    getCellFormula,
    createSpreadsheetTemplate,
    createSpreadsheet,
    waitForEvaluation,
} from "./spreadsheet_test_utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { ClientActionAdapter } from "@web/legacy/action_adapters";
import { actionService } from "@web/webclient/actions/action_service";
import { spreadsheetService } from "../src/actions/spreadsheet/spreadsheet_service";

const { Model } = spreadsheet;
const { topbarMenuRegistry } = spreadsheet.registries;
const { createEmptyWorkbookData } = spreadsheet.helpers;
const { jsonToBase64, base64ToJson } = pivotUtils;

const { module, test } = QUnit;

let serverData;

async function convertFormula(config) {
    const { env, model: m1 } = await createSpreadsheetFromPivot({
        pivotView: {
            model: "partner",
            data: config.data,
            arch: config.arch,
        },
        webClient: config.webClient,
    });

    //reload the model in headless mode, with the conversion plugin
    const model = new Model(m1.exportData(), {
        mode: "headless",
        evalContext: { env },
    });

    await waitForEvaluation(model);
    setCellContent(model, "A1", `=${config.formula}`);
    model.dispatch(config.convert);
    // Remove the equal sign
    return getCellContent(model, "A1").slice(1);
}

module(
    "documents_spreadsheet > pivot_templates",
    {
        beforeEach: function () {
            beforeEach(this);
            Object.assign(this.data, {
                "ir.model": {
                    fields: {
                        name: { string: "Model Name", type: "char" },
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 37,
                            name: "Product",
                            model: "product",
                        },
                        {
                            id: 544,
                            name: "partner",
                            model: "partner",
                        },
                    ],
                },
                "documents.document": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        raw: { string: "Data", type: "text" },
                        mimetype: { string: "mimetype", type: "char" },
                        handler: { string: "handler", type: "char" },
                        available_rule_ids: {
                            string: "Rules",
                            type: "many2many",
                            relation: "documents.workflow.rule",
                        },
                        folder_id: {
                            string: "Workspaces",
                            type: "many2one",
                            relation: "documents.folder",
                        },
                        res_model: { string: "Resource model", type: "char" },
                        tag_ids: {
                            string: "Tags",
                            type: "many2many",
                            relation: "documents.tag",
                        },
                        favorited_ids: { string: "Name", type: "many2many" },
                        is_favorited: { string: "Name", type: "boolean" },
                        thumbnail: { string: "Thumbnail", type: "text" },
                    },
                    records: [
                        { id: 1, name: "My spreadsheet", raw: "{}", is_favorited: false },
                        { id: 2, name: "", raw: "{}", is_favorited: true },
                    ],
                },
                "documents.workflow.rule": {
                    fields: {
                        display_name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
                "documents.folder": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        parent_folder_id: {
                            string: "Parent Workspace",
                            type: "many2one",
                            relation: "documents.folder",
                        },
                        description: { string: "Description", type: "text" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Workspace1",
                            description: "Workspace",
                            parent_folder_id: false,
                        },
                    ],
                },
                "mail.alias": {
                    fields: {
                        alias_name: { string: "Name", type: "char" },
                    },
                    records: [{ id: 1, alias_name: "hazard@rmcf.es" }],
                },
                "documents.share": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        folder_id: {
                            string: "Workspaces",
                            type: "many2one",
                            relation: "documents.folder",
                        },
                        alias_id: { string: "alias", type: "many2one", relation: "mail.alias" },
                    },
                    records: [{ id: 1, name: "Share1", folder_id: 1, alias_id: 1 }],
                    create_share: function () {
                        return Promise.resolve();
                    },
                },
                "documents.tag": {
                    fields: {},
                    records: [],
                    get_tags: () => [],
                },
                "spreadsheet.template": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        data: { string: "Data", type: "binary" },
                        thumbnail: { string: "Thumbnail", type: "binary" },
                    },
                    records: [
                        { id: 1, name: "Template 1", data: btoa("{}") },
                        { id: 2, name: "Template 2", data: btoa("{}") },
                    ],
                },
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "integer",
                            searchable: true,
                            group_operator: "sum",
                        },
                        bar: {
                            string: "Bar",
                            type: "integer",
                            searchable: true,
                            group_operator: "sum",
                        },
                        probability: {
                            string: "Probability",
                            type: "integer",
                            searchable: true,
                            group_operator: "avg",
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            store: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: 12,
                            bar: 110,
                            probability: 10,
                            product_id: [37],
                        },
                        {
                            id: 2,
                            foo: 1,
                            bar: 110,
                            probability: 11,
                            product_id: [41],
                        },
                    ],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
            });
            serverData = { models: this.data };
        },
        afterEach() {
            afterEach(this);
        },
    },
    function () {
        module("Template");
        test("Dispatch template command is not allowed if cache is not loaded", async function (assert) {
            assert.expect(2);
            const { model: m1, env } = await createSpreadsheetFromPivot();
            //reload the model in headless mode, with the conversion plugin
            const model = new Model(m1.exportData(), {
                mode: "headless",
                evalContext: { env },
            });
            assert.deepEqual(model.dispatch("CONVERT_PIVOT_TO_TEMPLATE").reasons, [
                CommandResult.PivotCacheNotLoaded,
            ]);
            assert.deepEqual(model.dispatch("CONVERT_PIVOT_FROM_TEMPLATE").reasons, [
                CommandResult.PivotCacheNotLoaded,
            ]);
        });

        test("Don't change formula if not many2one", async function (assert) {
            assert.expect(1);
            const formula = `PIVOT("1","probability","foo","12","bar","110")`;
            const result = await convertFormula({
                data: this.data,
                formula,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
                arch: `
                <pivot string="Partners">
                    <field name="foo" type="col"/>
                    <field name="bar" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            assert.equal(result, formula);
        });

        test("Adapt formula from absolute to relative with many2one in col", async function (assert) {
            assert.expect(4);
            const arch = `
                    <pivot string="Partners">
                        <field name="product_id" type="col"/>
                        <field name="bar" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`;
            const views = { "partner,false,pivot": arch, "partner,false,search": `<search/>` };
            Object.assign(serverData, { views });
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });
            let result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id","37","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`
            );

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT.HEADER("1","product_id","37","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`
            );

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id","41","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT.HEADER("1","product_id","41","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );
        });

        test("Adapt formula from absolute to relative with integer ids", async function (assert) {
            assert.expect(2);
            const arch = `
                    <pivot string="Partners">
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`;
            const views = { "partner,false,pivot": arch, "partner,false,search": `<search/>` };
            Object.assign(serverData, { views });
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });
            let result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id",37,"bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`
            );
            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT.HEADER("1","product_id",41,"bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );
        });

        test("Adapt formula from absolute to relative with many2one in row", async function (assert) {
            assert.expect(4);
            const arch = `
                    <pivot string="Partners">
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`;
            const views = { "partner,false,pivot": arch, "partner,false,search": `<search/>` };
            Object.assign(serverData, { views });
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });

            let result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id","37","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`
            );

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id","41","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id","41","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT.HEADER("1","product_id","41","bar","110")`,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
            });
            assert.equal(
                result,
                `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );
        });

        test("Adapt formula from relative to absolute with many2one in col", async function (assert) {
            assert.expect(4);
            const arch = `
                    <pivot string="Partners">
                        <field name="product_id" type="col"/>
                        <field name="bar" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`;
            const views = { "partner,false,pivot": arch, "partner,false,search": `<search/>` };
            Object.assign(serverData, { views });
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });
            let result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 1),"bar","110")`,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
            });
            assert.equal(result, `PIVOT("1","probability","product_id","37","bar","110")`);

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
            });
            assert.equal(result, `PIVOT.HEADER("1","product_id","37","bar","110")`);

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 2),"bar","110")`,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
            });
            assert.equal(result, `PIVOT("1","probability","product_id","41","bar","110")`);

            result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id", 2),"bar","110")`,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
            });
            assert.equal(result, `PIVOT.HEADER("1","product_id","41","bar","110")`);
        });

        test("Will ignore overflowing template position", async function (assert) {
            assert.expect(1);
            const arch = `
                <pivot string="Partners">
                <field name="bar" type="col"/>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`;
            const views = { "partner,false,pivot": arch, "partner,false,search": `<search/>` };
            Object.assign(serverData, { views });
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });
            const result = await convertFormula({
                webClient,
                data: this.data,
                arch,
                formula: `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar","110")`,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
            });
            assert.equal(result, "");
        });

        test("copy template menu", async function (assert) {
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    return {
                        ...actionMain,
                        doAction: (actionRequest, options = {}) => {
                            if (
                                actionRequest.tag === "action_open_template" &&
                                actionRequest.params.spreadsheet_id === 111
                            ) {
                                assert.step("redirect");
                            }
                            return actionMain.doAction(actionRequest, options);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });
            const serverData = this.data;
            const { env } = await createSpreadsheetTemplate({
                data: serverData,
                mockRPC: function (route, args) {
                    if (args.model == "spreadsheet.template" && args.method === "copy") {
                        assert.step("template_copied");
                        const { data, thumbnail } = args.kwargs.default;
                        assert.ok(data);
                        assert.ok(thumbnail);
                        serverData["spreadsheet.template"].records.push({
                            id: 111,
                            name: "template",
                            data,
                            thumbnail,
                        });
                        return 111;
                    }
                },
            });
            const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
            const makeACopy = file.children.find((item) => item.id === "make_copy");
            makeACopy.action(env);
            await nextTick();
            assert.verifySteps(["template_copied", "redirect"]);
        });

        test("Adapt formula from relative to absolute with many2one in row", async function (assert) {
            assert.expect(4);
            const arch = `
                    <pivot string="Partners">
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`;
            const views = { "partner,false,pivot": arch, "partner,false,search": `<search/>` };
            Object.assign(serverData, { views });
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });
            let result = await convertFormula({
                webClient,
                formula: `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch,
            });
            assert.equal(result, `PIVOT("1","probability","product_id","37","bar","110")`);

            result = await convertFormula({
                webClient,
                formula: `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch,
            });
            assert.equal(result, `PIVOT.HEADER("1","product_id","37","bar","110")`);

            result = await convertFormula({
                webClient,
                formula: `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch,
            });
            assert.equal(result, `PIVOT("1","probability","product_id","41","bar","110")`);

            result = await convertFormula({
                webClient,
                formula: `PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch,
            });
            assert.equal(result, `PIVOT.HEADER("1","product_id","41","bar","110")`);
        });

        test("Adapt pivot as function arg from relative to absolute", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `SUM(
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110"),
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")
                )`,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch: `
                <pivot string="Partners">
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            assert.equal(
                result,
                `SUM(PIVOT("1","probability","product_id","37","bar","110"),PIVOT("1","probability","product_id","41","bar","110"))`
            );
        });

        test("Adapt pivot as operator arg from relative to absolute", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")
                    +
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")
                `,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch: `
                <pivot string="Partners">
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id","37","bar","110")+PIVOT("1","probability","product_id","41","bar","110")`
            );
        });

        test("Adapt pivot as unary operator arg from relative to absolute", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `
                        -PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")
                    `,
                data: this.data,
                convert: "CONVERT_PIVOT_FROM_TEMPLATE",
                arch: `
                <pivot string="Partners">
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            assert.equal(result, `-PIVOT("1","probability","product_id","37","bar","110")`);
        });

        test("Adapt pivot as operator arg from absolute to relative", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `
                    PIVOT("1","probability","product_id","37","bar","110")
                    +
                    PIVOT("1","probability","product_id","41","bar","110")
                `,
                data: this.data,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
                arch: `
                    <pivot string="Partners">
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            assert.equal(
                result,
                `PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")+PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110")`
            );
        });

        test("Adapt pivot as unary operator arg from absolute to relative", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `
                    -PIVOT("1","probability","product_id","37","bar","110")
                `,
                data: this.data,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
                arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
            });
            assert.equal(
                result,
                `-PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`
            );
        });

        test("Adapt pivot as function arg from absolute to relative", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `
                SUM(
                    PIVOT("1","probability","product_id","37","bar","110"),
                    PIVOT("1","probability","product_id","41","bar","110")
                )
            `,
                data: this.data,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
                arch: `
                    <pivot string="Partners">
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            assert.equal(
                result,
                `SUM(PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110"),PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",2),"bar","110"))`
            );
        });

        test("Computed ids are not changed", async function (assert) {
            assert.expect(1);
            const result = await convertFormula({
                formula: `PIVOT("1","probability","product_id",A2,"bar","110")`,
                data: this.data,
                convert: "CONVERT_PIVOT_TO_TEMPLATE",
                arch: `
                    <pivot string="Partners">
                    <field name="bar" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            assert.equal(result, `PIVOT("1","probability","product_id",A2,"bar","110")`);
        });

        test("Save as template menu", async function (assert) {
            assert.expect(7);
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    return Object.assign({}, actionMain, {
                        doAction: (actionRequest, options = {}) => {
                            if (
                                actionRequest ===
                                "documents_spreadsheet.save_spreadsheet_template_action"
                            ) {
                                assert.step("create_template_wizard");

                                const context = options.additionalContext;
                                const data = base64ToJson(context.default_data);
                                const name = context.default_template_name;
                                const cells = data.sheets[0].cells;
                                assert.equal(
                                    name,
                                    "pivot spreadsheet - Template",
                                    "It should be named after the spreadsheet"
                                );
                                assert.ok(context.default_thumbnail);
                                assert.equal(
                                    cells.A3.content,
                                    `=PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",1))`
                                );
                                assert.equal(
                                    cells.B3.content,
                                    `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id",1),"bar","110")`
                                );
                                assert.equal(cells.A11.content, "😃");
                                return Promise.resolve(true);
                            }
                            return actionMain.doAction(actionRequest, options);
                        },
                    });
                },
            };
            serviceRegistry.add("action", fakeActionService);

            const { env, model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(model, "A11", "😃");
            const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
            const saveAsTemplate = file.children.find((item) => item.id === "save_as_template");
            saveAsTemplate.action(env);
            await nextTick();
            assert.verifySteps(["create_template_wizard"]);
        });

        test("copy template menu", async function (assert) {
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    return {
                        ...actionMain,
                        doAction: (actionRequest, options = {}) => {
                            if (
                                actionRequest.tag === "action_open_template" &&
                                actionRequest.params.spreadsheet_id === 111
                            ) {
                                assert.step("redirect");
                            }
                            return actionMain.doAction(actionRequest, options);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });
            const serverData = this.data;
            const { env } = await createSpreadsheetTemplate({
                data: serverData,
                mockRPC: function (route, args) {
                    if (args.model == "spreadsheet.template" && args.method === "copy") {
                        assert.step("template_copied");
                        const { data, thumbnail } = args.kwargs.default;
                        assert.ok(data);
                        assert.ok(thumbnail);
                        serverData["spreadsheet.template"].records.push({
                            id: 111,
                            name: "template",
                            data,
                            thumbnail,
                        });
                        return 111;
                    }
                },
            });
            const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
            const makeACopy = file.children.find((item) => item.id === "make_copy");
            makeACopy.action(env);
            await nextTick();
            assert.verifySteps(["template_copied", "redirect"]);
        });

        test("Autofill template position", async function (assert) {
            assert.expect(4);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(
                model,
                "B2",
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4444))`
            );

            function selectB2(model) {
                model.dispatch("SET_SELECTION", {
                    anchor: [1, 1],
                    zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                    anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
                });
            }

            // DOWN
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 10000),"bar",PIVOT.POSITION("1","bar", 4444))`
            );

            // UP
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 0 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B1"),
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9998),"bar",PIVOT.POSITION("1","bar", 4444))`
            );

            // RIGHT
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 2, row: 1 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "C2"),
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4445))`
            );

            // LEFT
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 0, row: 1 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "A2"),
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4443))`
            );
        });

        test("Autofill template position: =-PIVOT(...)", async function (assert) {
            assert.expect(1);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(
                model,
                "B2",
                `= - PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4444))`
            );

            // DOWN
            model.dispatch("SET_SELECTION", {
                anchor: [1, 1],
                zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
            });
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `= - PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 10000),"bar",PIVOT.POSITION("1","bar", 4444))`
            );
        });

        test("Autofill template position: 2 PIVOT in one formula", async function (assert) {
            assert.expect(1);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(
                model,
                "B2",
                `=SUM(
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4444)),
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 666),"bar",PIVOT.POSITION("1","bar", 4444))
                )`.replace(/\n/g, "")
            );

            model.dispatch("SET_SELECTION", {
                anchor: [1, 1],
                zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
            });
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            // Well this does not work, it only updates the last PIVOT figure. But at least it does not crash.
            assert.equal(
                getCellFormula(model, "B3"),
                `=SUM(
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4444)),
                    PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 667),"bar",PIVOT.POSITION("1","bar", 4444))
                )`.replace(/\n/g, "")
            );
        });

        test("Autofill template position: PIVOT.POSITION not in PIVOT", async function (assert) {
            assert.expect(1);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(model, "B2", `=PIVOT.POSITION("1","foo", 3333)`);
            function selectB2(model) {
                model.dispatch("SET_SELECTION", {
                    anchor: [1, 1],
                    zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                    anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
                });
            }

            // DOWN
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `=PIVOT.POSITION("1","foo", 3333)`,
                "Should have copied the origin value"
            );
        });

        test("Autofill template position: with invalid pivot id", async function (assert) {
            assert.expect(1);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(
                model,
                "B2",
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("10000","product_id", 9999))`
            );
            function selectB2(model) {
                model.dispatch("SET_SELECTION", {
                    anchor: [1, 1],
                    zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                    anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
                });
            }

            // DOWN
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("10000","product_id", 9999))`,
                "Should have copied the origin value"
            );
        });

        test("Autofill template position: increment last group", async function (assert) {
            assert.expect(1);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="foo" type="row"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            setCellContent(
                model,
                "B2",
                `=PIVOT("1","probability","foo",PIVOT.POSITION("1","foo", 3333),"product_id",PIVOT.POSITION("1","product_id", 9999),"bar",PIVOT.POSITION("1","bar", 4444))`
            );
            function selectB2(model) {
                model.dispatch("SET_SELECTION", {
                    anchor: [1, 1],
                    zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                    anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
                });
            }

            // DOWN
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `=PIVOT("1","probability","foo",PIVOT.POSITION("1","foo", 3333),"product_id",PIVOT.POSITION("1","product_id", 10000),"bar",PIVOT.POSITION("1","bar", 4444))`,
                "It should have incremented the last row group position"
            );
        });

        test("Autofill template position: does not increment last field if not many2one", async function (assert) {
            assert.expect(1);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="foo" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                },
            });
            // last row field (foo) is not a position
            setCellContent(
                model,
                "B2",
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999), "foo","10","bar","15")`
            );
            function selectB2(model) {
                model.dispatch("SET_SELECTION", {
                    anchor: [1, 1],
                    zones: [{ top: 1, bottom: 1, right: 1, left: 1 }],
                    anchorZone: { top: 1, bottom: 1, right: 1, left: 1 },
                });
            }

            // DOWN
            selectB2(model);
            model.dispatch("AUTOFILL_SELECT", { col: 1, row: 2 });
            model.dispatch("AUTOFILL");
            assert.equal(
                getCellFormula(model, "B3"),
                `=PIVOT("1","probability","product_id",PIVOT.POSITION("1","product_id", 9999), "foo","10","bar","15")`,
                "It should not have changed the formula"
            );
        });

        module("Template Modal");

        test("Create spreadsheet from kanban view opens a modal", async function (assert) {
            assert.expect(2);
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data: this.data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
            });
            await dom.click(".o_documents_kanban_spreadsheet");
            await nextTick();
            assert.ok(
                $(".o-spreadsheet-templates-dialog").length,
                "should have opened the template modal"
            );
            assert.ok(
                $(".o-spreadsheet-templates-dialog .modal-body .o_searchview").length,
                "The Modal should have a search view"
            );
            kanban.destroy();
        });

        test("Create spreadsheet from list view opens a modal", async function (assert) {
            assert.expect(2);
            const list = await createDocumentsView({
                View: DocumentsListView,
                model: "documents.document",
                data: this.data,
                arch: `<tree></tree>`,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
            });
            await dom.click(".o_documents_kanban_spreadsheet");

            assert.ok(
                $(".o-spreadsheet-templates-dialog").length,
                "should have opened the template modal"
            );

            assert.ok(
                $(".o-spreadsheet-templates-dialog .modal-body .o_searchview").length,
                "The Modal should have a search view"
            );
            list.destroy();
        });

        test("Can search template in modal with searchbar", async function (assert) {
            assert.expect(4);
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data: this.data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <field name="name"/>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
            });
            await dom.click(".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            assert.equal(dialog.querySelectorAll(".o-template").length, 3);
            assert.equal(dialog.querySelector(".o-template").textContent, "Blank");

            const searchInput = dialog.querySelector(".o_searchview_input");
            await fields.editInput(searchInput, "Template 1");
            await dom.triggerEvent(searchInput, "keydown", { key: "Enter" });
            assert.equal(dialog.querySelectorAll(".o-template").length, 2);
            assert.equal(dialog.querySelector(".o-template").textContent, "Blank");
            kanban.destroy();
        });

        test("Can create a spreadsheet from template", async function (assert) {
            assert.expect(5);
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data: this.data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <field name="name"/>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
                mockRPC: function (route, args) {
                    if (args.method === "create" && args.model === "documents.document") {
                        assert.step("create_sheet");
                        assert.equal(
                            args.args[0].name,
                            "Template 2",
                            "It should have been named after the template"
                        );
                    }
                    if (args.method === "search_read" && args.model === "ir.model") {
                        return Promise.resolve([{ name: "partner" }]);
                    }
                    return this._super.apply(this, arguments);
                },
                intercepts: {
                    do_action: function (ev) {
                        assert.step("redirect");
                        assert.equal(ev.data.action.tag, "action_open_spreadsheet");
                    },
                },
            });

            await dom.click(".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

            // select template 2
            await dom.triggerEvent(dialog.querySelectorAll(".o-template img")[2], "focus");
            await dom.click(dialog.querySelector(".o-spreadsheet-create"));
            assert.verifySteps(["create_sheet", "redirect"]);
            kanban.destroy();
        });

        test("Can create a blank spreadsheet from template dialog", async function (assert) {
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data: this.data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <field name="name"/>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
                mockRPC: function (route, args) {
                    if (args.method === "create" && args.model === "documents.document") {
                        assert.step("create_sheet");
                        assert.deepEqual(
                            JSON.parse(args.args[0].raw),
                            createEmptyWorkbookData("Sheet1"),
                            "It should be an empty spreadsheet"
                        )
                        assert.equal(
                            args.args[0].name,
                            "Untitled spreadsheet",
                            "It should have the default name"
                        );
                    }
                    return this._super(...arguments);
                },
                intercepts: {
                    do_action: function (ev) {
                        assert.step("redirect");
                        assert.equal(ev.data.action.tag, "action_open_spreadsheet");
                    },
                },
            });

            await dom.click(".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

            // select blank spreadsheet
            await dom.triggerEvent(dialog.querySelectorAll(".o-template img")[0], "focus");
            await dom.click(dialog.querySelector(".o-spreadsheet-create"));
            assert.verifySteps(["create_sheet", "redirect"]);
            kanban.destroy();
        });

        test("Will convert additional template position to empty cell", async function (assert) {
            assert.expect(5);
            const data = Object.assign({}, this.data);

            // 0. Create a spreadsheet from the template
            // @legacy: The kanban is created before the call to "createSpreadsheetFromPivot"
            // to allow the execution environment of this test to be created and then cleaned up
            // in the right order. For this exact same reason, the mockRPC that the kanban will actually use
            // after the call to "createSpreadsheetFromPivot" is defined in "createSpreadsheetFromPivot".
            // The code responsible for this is located at @web/legacy/utils:mapLegacyEnvToWowlEnv
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <field name="name"/>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
            });
            registerCleanup(() => kanban.destroy());

            // 1. create a spreadsheet with a pivot
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                        <pivot string="Partners">
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    mockRPC: function (route, args) {
                        if (args.method === "create" && args.model === "documents.document") {
                            const data = JSON.parse(args.args[0].raw);
                            assert.step("create_sheet");
                            assert.equal(
                                data.sheets[0].cells.F15.content,
                                `Coucou petite perruche`,
                                "Row 15 should have been deleted"
                            );
                            assert.equal(
                                data.sheets[0].cells.G15,
                                undefined,
                                "(previous) Row 15 should have been deleted"
                            );
                            assert.notOk(
                                data.sheets[0].cells.F1,
                                "The invalid F1 cell should be empty"
                            );
                        }
                        if (args.method === "search_read" && args.model === "ir.model") {
                            return Promise.resolve([{ name: "partner" }]);
                        }
                    },
                },
            });
            await waitForEvaluation(model);

            // 2. Set a template position which is too high
            // there are other pivot headers on row 1
            setCellContent(
                model,
                "F1",
                `=PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",999),"bar","110")`
            );
            // there are not other pivot headers on row 15
            setCellContent(
                model,
                "F15",
                `=PIVOT.HEADER("1","product_id",PIVOT.POSITION("1","product_id",888),"bar","110")`
            );
            setCellContent(model, "G15", `Hello`);
            setCellContent(model, "F16", `Coucou petite perruche`);
            const modelData = model.exportData();
            data["spreadsheet.template"].records.push({
                id: 99,
                name: "template",
                data: btoa(JSON.stringify(modelData)),
            });

            await dom.click(".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            // select template 2
            await dom.triggerEvent(dialog.querySelectorAll(".o-template img")[3], "focus");
            await dom.click(dialog.querySelector(".o-spreadsheet-create"));
            assert.verifySteps(["create_sheet"]);
        });

        test("Name template with spreadsheet name", async function (assert) {
            assert.expect(3);
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    return Object.assign({}, actionMain, {
                        doAction: (actionRequest, options = {}) => {
                            if (
                                actionRequest ===
                                "documents_spreadsheet.save_spreadsheet_template_action"
                            ) {
                                assert.step("create_template_wizard");
                                const name = options.additionalContext.default_template_name;
                                assert.equal(
                                    name,
                                    "My spreadsheet - Template",
                                    "It should be named after the spreadsheet"
                                );
                                return Promise.resolve(true);
                            }
                            return actionMain.doAction(actionRequest, options);
                        },
                    });
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });

            let spreadSheetComponent;
            patchWithCleanup(ClientActionAdapter.prototype, {
                mounted() {
                    this._super();
                    spreadSheetComponent = this.widget.spreadsheetComponent.componentRef.comp;
                },
            });

            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: function (route, args) {
                    if (args.method === "create" && args.model === "spreadsheet.template") {
                        assert.step("create_template");
                        assert.equal(
                            args.args[0].name,
                            "My spreadsheet",
                            "It should be named after the spreadsheet"
                        );
                    }
                },
            });
            const { env } = await createSpreadsheet({ spreadsheetId: 2, webClient });
            const input = $(webClient.el).find(".breadcrumb-item input");
            await fields.editInput(input, "My spreadsheet");
            await dom.triggerEvent(input, "change");
            const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
            const saveAsTemplate = file.children.find((item) => item.id === "save_as_template");
            saveAsTemplate.action(env);
            await nextTick();

            assert.verifySteps(["create_template_wizard"]);
        });

        test("Can fetch next templates", async function (assert) {
            assert.expect(8);
            this.data["spreadsheet.template"].records = this.data[
                "spreadsheet.template"
            ].records.concat([
                { id: 3, name: "Template 3", data: btoa("{}") },
                { id: 4, name: "Template 4", data: btoa("{}") },
                { id: 5, name: "Template 5", data: btoa("{}") },
                { id: 6, name: "Template 6", data: btoa("{}") },
                { id: 7, name: "Template 7", data: btoa("{}") },
                { id: 8, name: "Template 8", data: btoa("{}") },
                { id: 9, name: "Template 9", data: btoa("{}") },
                { id: 10, name: "Template 10", data: btoa("{}") },
                { id: 11, name: "Template 11", data: btoa("{}") },
                { id: 12, name: "Template 12", data: btoa("{}") },
            ]);
            let fetch = 0;
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data: this.data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <field name="name"/>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
                mockRPC: function (route, args) {
                    if (
                        route === "/web/dataset/search_read" &&
                        args.model === "spreadsheet.template"
                    ) {
                        fetch++;
                        assert.equal(args.limit, 9);
                        assert.step("fetch_templates");
                        if (fetch === 1) {
                            assert.equal(args.offset, undefined);
                        } else if (fetch === 2) {
                            assert.equal(args.offset, 9);
                        }
                    }
                    if (args.method === "search_read" && args.model === "ir.model") {
                        return Promise.resolve([{ name: "partner" }]);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await dom.click(".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

            assert.equal(dialog.querySelectorAll(".o-template").length, 10);
            await dom.click(dialog.querySelector(".o_pager_next"));
            assert.verifySteps(["fetch_templates", "fetch_templates"]);
            kanban.destroy();
        });

        test("Disable create button if no template is selected", async function (assert) {
            assert.expect(2);
            this.data["spreadsheet.template"].records = this.data[
                "spreadsheet.template"
            ].records.concat([
                { id: 3, name: "Template 3", data: btoa("{}") },
                { id: 4, name: "Template 4", data: btoa("{}") },
                { id: 5, name: "Template 5", data: btoa("{}") },
                { id: 6, name: "Template 6", data: btoa("{}") },
                { id: 7, name: "Template 7", data: btoa("{}") },
                { id: 8, name: "Template 8", data: btoa("{}") },
                { id: 9, name: "Template 9", data: btoa("{}") },
                { id: 10, name: "Template 10", data: btoa("{}") },
                { id: 11, name: "Template 11", data: btoa("{}") },
                { id: 12, name: "Template 12", data: btoa("{}") },
            ]);
            const kanban = await createDocumentsView({
                View: DocumentsKanbanView,
                model: "documents.document",
                data: this.data,
                arch: `
                    <kanban><templates><t t-name="kanban-box">
                        <field name="name"/>
                    </t></templates></kanban>
                `,
                archs: {
                    "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
                },
            });
            // open template dialog
            await dom.click(".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

            // select template
            await dom.triggerEvent(dialog.querySelectorAll(".o-template img")[1], "focus");

            // change page; no template should be selected
            await dom.click(dialog.querySelector(".o_pager_next"));
            assert.containsNone(dialog, ".o-template-selected");
            const createButton = dialog.querySelector(".o-spreadsheet-create");
            await dom.click(createButton);
            assert.ok(createButton.attributes.disabled);
            kanban.destroy();
        });

        test("Open spreadsheet template from list view", async function (assert) {
            assert.expect(3);
            const list = await createView({
                View: TemplateListView,
                model: "spreadsheet.template",
                data: this.data,
                arch: `
                    <tree>
                        <field name="name"/>
                        <button string="Edit" class="float-right" name="edit_template" icon="fa-pencil" />
                    </tree>
                `,
                intercepts: {
                    do_action: function ({ data }) {
                        assert.step("redirect_to_template");
                        assert.deepEqual(data.action, {
                            type: "ir.actions.client",
                            tag: "action_open_template",
                            params: {
                                spreadsheet_id: 1,
                                showFormulas: true,
                            },
                        });
                    },
                },
            });
            await dom.clickFirst(`button[name="edit_template"]`);
            assert.verifySteps(["redirect_to_template"]);
            list.destroy();
        });

        test("Copy template from list view", async function (assert) {
            assert.expect(4);
            const list = await createView({
                View: TemplateListView,
                model: "spreadsheet.template",
                data: this.data,
                arch: `
                    <tree>
                        <field name="name"/>
                        <button string="Make a copy" class="float-right" name="copy" type="object" icon="fa-clone" />
                    </tree>
                `,
                intercepts: {
                    execute_action: function ({ data }) {
                        assert.strictEqual(
                            data.action_data.name,
                            "copy",
                            "should call the copy method"
                        );
                        assert.equal(data.env.currentID, 1, "template with ID 1 should be copied");
                        assert.step("add_copy_of_template");
                    },
                },
            });
            await dom.clickFirst(`button[name="copy"]`);
            assert.verifySteps(["add_copy_of_template"]);
            list.destroy();
        });

        test("Create new spreadsheet from template from list view", async function (assert) {
            assert.expect(4);
            const list = await createView({
                View: TemplateListView,
                model: "spreadsheet.template",
                data: this.data,
                arch: `
                    <tree>
                        <field name="name"/>
                        <button string="New spreadsheet" class="o-new-spreadsheet float-right" name="create_spreadsheet" icon="fa-plus" />
                    </tree>
                `,
                mockRPC: async function (route, args) {
                    if (args.method === "create" && args.model === "documents.document") {
                        assert.step("spreadsheet_created");
                        return 42;
                    }
                    return this._super.apply(this, arguments);
                },
                intercepts: {
                    do_action: function ({ data }) {
                        assert.deepEqual(data.action, {
                            type: "ir.actions.client",
                            tag: "action_open_spreadsheet",
                            params: {
                                spreadsheet_id: 42,
                            },
                        });
                        assert.step("redirect_to_spreadsheet");
                    },
                },
            });
            await dom.clickFirst(`button[name="create_spreadsheet"]`);
            assert.verifySteps(["spreadsheet_created", "redirect_to_spreadsheet"]);
            list.destroy();
        });

        test("open template client action without collaborative indicators", async function (assert) {
            assert.expect(2);
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
            });
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_template",
                params: { spreadsheet_id: 1 },
            });
            assert.containsNone(webClient, ".o_spreadsheet_sync_status");
            assert.containsNone(webClient, ".o_spreadsheet_number_users");
        });

        test("collaboration communication is disabled", async function (assert) {
            assert.expect(1);
            registry.category("services").add("spreadsheet", spreadsheetService);
            const webClient = await createWebClient({
                serverData,
                legacyParams: { withLegacyMockServer: true },
                mockRPC: async function (route, args) {
                    if (route.includes("join_spreadsheet_session")) {
                        assert.ok(false, "it should not join a collaborative session");
                    }
                    if (route.includes("dispatch_spreadsheet_message")) {
                        assert.ok(false, "it should not dispatch collaborative revisions");
                    }
                },
            });
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_template",
                params: { spreadsheet_id: 1 },
            });
            assert.ok(true);
        });

        test("Create new spreadsheet from template containing non Latin characters", async function (assert) {
            assert.expect(1);
            const model = new Model();
            setCellContent(model, "A1", "😃");
            this.data["spreadsheet.template"].records = [
                {
                    id: 99,
                    name: "template",
                    data: jsonToBase64(model.exportData()),
                },
            ];
            const list = await createView({
                View: TemplateListView,
                model: "spreadsheet.template",
                data: this.data,
                arch: `
                    <tree>
                        <field name="name"/>
                        <button string="New spreadsheet" class="o-new-spreadsheet float-right" name="create_spreadsheet" icon="fa-plus" />
                    </tree>
                `,
            });
            await dom.click(`button[name="create_spreadsheet"]`);
            const documents = this.data["documents.document"].records;
            const data = JSON.parse(documents[documents.length - 1].raw);
            const cells = data.sheets[0].cells;
            assert.equal(cells.A1.content, "😃");
            list.destroy();
        });

        test("open template with non Latin characters", async function (assert) {
            assert.expect(1);
            const model = new Model();
            setCellContent(model, "A1", "😃");
            this.data["spreadsheet.template"].records = [
                {
                    id: 99,
                    name: "template",
                    data: jsonToBase64(model.exportData()),
                },
            ];
            const { model: template } = await createSpreadsheetTemplate({
                data: this.data,
                spreadsheetId: 99,
            });
            assert.equal(
                getCellValue(template, "A1"),
                "😃",
                "It should show the smiley as a smiley 😉"
            );
        });
        test("create and edit template and create new spreadsheet from it", async function (assert) {
            assert.expect(4);
            const templateModel = new Model();
            setCellContent(templateModel, "A1", "Firstname");
            setCellContent(templateModel, "B1", "Lastname");
            const id = 101;
            this.data["spreadsheet.template"].records = [
                {
                    id,
                    name: "template",
                    data: jsonToBase64(templateModel.exportData()),
                },
            ];
            let spreadSheetComponent;
            patchWithCleanup(SpreadsheetTemplateAction.prototype, {
                mounted() {
                    this._super();
                    spreadSheetComponent = this.spreadsheetRef.comp;
                },
            });
            const { model, webClient } = await createSpreadsheetTemplate({
                data: this.data,
                spreadsheetId: id,
                mockRPC: function (route, args) {
                    if (args.model == "spreadsheet.template") {
                        if (args.method === "write") {
                            const model = base64ToJson(args.args[1].data);
                            assert.strictEqual(
                                typeof model,
                                "object",
                                "Model type should be object"
                            );
                            const { A1, B1 } = model.sheets[0].cells;
                            assert.equal(
                                `${A1.content} ${B1.content}`,
                                `Firstname Name`,
                                "A1 and B1 should be changed after update"
                            );
                        }
                    }
                    if (this) {
                        return this._super.apply(this, arguments);
                    }
                },
            });

            setCellContent(model, "B1", "Name");
            await spreadSheetComponent.trigger(
                "spreadsheet-saved",
                spreadSheetComponent.getSaveData()
            );
            await doAction(webClient, {
                type: "ir.actions.client",
                tag: "action_open_template",
                params: { active_id: id },
            });
        });
    }
);
