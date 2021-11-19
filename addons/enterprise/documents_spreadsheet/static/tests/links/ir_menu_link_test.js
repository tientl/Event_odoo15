/** @odoo-module */
import { registry } from "@web/core/registry";
import { menuService } from "@web/webclient/menus/menu_service";
import { session } from "@web/session";
import { actionService } from "@web/webclient/actions/action_service";
import { click, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { createSpreadsheet, getCell, setCellContent } from "../spreadsheet_test_utils";
import spreadsheet from "../../src/js/o_spreadsheet/o_spreadsheet_extended";
import { getBasicData } from "../spreadsheet_test_data";

const { registries, Model } = spreadsheet;
const { cellMenuRegistry } = registries;

function labelInput(webClient) {
    return webClient.el.querySelectorAll(".o-link-editor input")[0];
}

function urlInput(webClient) {
    return webClient.el.querySelectorAll(".o-link-editor input")[1];
}

/**
 * Create a spreadsheet and open the menu selector to
 * insert a menu link in A1.
 */
async function openMenuSelector(serverData) {
    const { webClient, env, model } = await createSpreadsheet({
        serverData,
    });
    const insertLinkMenu = cellMenuRegistry.getAll().find((item) => item.id === "insert_link");
    await insertLinkMenu.action(env);
    await nextTick();
    await click(webClient.el, ".o-special-link");
    await click(webClient.el, ".o-menu-item[data-name='odooMenu']");
    return { webClient, env, model };
}

QUnit.module(
    "documents_spreadsheet > ir.ui.menu links",
    {
        beforeEach: function () {
            this.serverData = {};
            this.serverData.menus = {
                root: { id: "root", children: [1, 2], name: "root", appID: "root" },
                1: { id: 1, children: [], name: "menu with xmlid", appID: 1, xmlid: "test_menu" },
                2: { id: 2, children: [], name: "menu without xmlid", appID: 2 },
            };
            this.serverData.models = {
                ...getBasicData(),
                "ir.ui.menu": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        action: { string: "Action", type: "char" },
                        groups_id: { string: "Groups", type: "many2many", relation: "res.group" },
                    },
                    records: [
                        { id: 1, name: "menu with xmlid", action: "action1", groups_id: [10] },
                        { id: 2, name: "menu without xmlid", action: "action2", groups_id: [10] },
                    ],
                },
                "res.users": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        groups_id: { string: "Groups", type: "many2many", relation: "res.group" },
                    },
                    records: [
                        { id: 1, name: "Raoul", groups_id: [10] },
                        { id: 2, name: "Joseph", groups_id: [] },
                    ],
                },
                "res.group": {
                    fields: { name: { string: "Name", type: "char" } },
                    records: [{ id: 10, name: "test group" }],
                },
            };
            patchWithCleanup(session, { uid: 1 });
        },
    },
    () => {
        QUnit.test("ir.menu linked based on xml id", async function (assert) {
            registry.category("services").add("menu", menuService).add("action", actionService);
            const env = await makeTestEnv({ serverData: this.serverData });
            const model = new Model({}, { evalContext: { env } });
            setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/test_menu)");
            const cell = getCell(model, "A1");
            assert.equal(cell.evaluated.value, "label", "The value should be the menu name");
            assert.equal(
                cell.content,
                "[label](odoo://ir_menu_xml_id/test_menu)",
                "The content should be the complete markdown link"
            );
            assert.equal(cell.link.label, "label", "The link label should be the menu name");
            assert.equal(
                cell.link.url,
                "odoo://ir_menu_xml_id/test_menu",
                "The link url should reference the correct menu"
            );
        });

        QUnit.test("ir.menu linked based on record id", async function (assert) {
            assert.expect(4);
            registry.category("services").add("menu", menuService).add("action", actionService);
            const env = await makeTestEnv({ serverData: this.serverData });
            const model = new Model({}, { evalContext: { env } });
            setCellContent(model, "A1", "[label](odoo://ir_menu_id/2)");
            const cell = getCell(model, "A1");
            assert.equal(cell.evaluated.value, "label", "The value should be the menu name");
            assert.equal(
                cell.content,
                "[label](odoo://ir_menu_id/2)",
                "The content should be the complete markdown link"
            );
            assert.equal(cell.link.label, "label", "The link label should be the menu name");
            assert.equal(
                cell.link.url,
                "odoo://ir_menu_id/2",
                "The link url should reference the correct menu"
            );
        });

        QUnit.test("ir.menu linked based on xml id which does not exists", async function (assert) {
            assert.expect(2);
            registry.category("services").add("menu", menuService).add("action", actionService);
            const env = await makeTestEnv({ serverData: this.serverData });
            const model = new Model(
                {},
                {
                    evalContext: { env },
                }
            );
            setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/does_not_exists)");
            const cell = getCell(model, "A1");
            assert.equal(cell.content, "[label](odoo://ir_menu_xml_id/does_not_exists)");
            assert.equal(cell.evaluated.value, "#BAD_EXPR");
        });

        QUnit.test(
            "ir.menu linked based on record id which does not exists",
            async function (assert) {
                assert.expect(2);
                registry.category("services").add("menu", menuService).add("action", actionService);
                const env = await makeTestEnv({ serverData: this.serverData });
                const model = new Model(
                    {},
                    {
                        evalContext: { env },
                    }
                );
                setCellContent(model, "A1", "[label](odoo://ir_menu_id/9999)");
                const cell = getCell(model, "A1");
                assert.equal(cell.content, "[label](odoo://ir_menu_id/9999)");
                assert.equal(cell.evaluated.value, "#BAD_EXPR");
            }
        );

        QUnit.test("insert a new ir menu link", async function (assert) {
            assert.expect(6);
            const { webClient, model } = await openMenuSelector(this.serverData);
            await click(webClient.el, ".o_field_many2one input");
            assert.ok(webClient.el.querySelector("button.o-confirm").disabled);
            await click(document.querySelectorAll(".ui-menu-item")[0]);
            await click(webClient.el, "button.o-confirm");
            assert.equal(
                labelInput(webClient).value,
                "menu with xmlid",
                "The label should be the menu name"
            );
            assert.equal(
                urlInput(webClient).value,
                "menu with xmlid",
                "The url displayed should be the menu name"
            );
            assert.ok(urlInput(webClient).disabled, "The url input should be disabled");
            await click(webClient.el, "button.o-save");
            const cell = getCell(model, "A1");
            assert.equal(
                cell.content,
                "[menu with xmlid](odoo://ir_menu_xml_id/test_menu)",
                "The content should be the complete markdown link"
            );
            assert.equal(
                webClient.el.querySelector(".o-link-tool a").text,
                "menu with xmlid",
                "The link tooltip should display the menu name"
            );
        });

        QUnit.test(
            "insert a new ir menu link when the menu does not have an xml id",
            async function (assert) {
                assert.expect(6);
                const { webClient, model } = await openMenuSelector(this.serverData);
                await click(webClient.el, ".o_field_many2one input");
                assert.ok(webClient.el.querySelector("button.o-confirm").disabled);
                const item = document.querySelectorAll(".ui-menu-item")[1];
                // don't ask why it's needed and why it only works with a jquery event >:(
                $(item).trigger("mouseenter");
                await click(item);
                await click(webClient.el, "button.o-confirm");
                assert.equal(
                    labelInput(webClient).value,
                    "menu without xmlid",
                    "The label should be the menu name"
                );
                assert.equal(
                    urlInput(webClient).value,
                    "menu without xmlid",
                    "The url displayed should be the menu name"
                );
                assert.ok(urlInput(webClient).disabled, "The url input should be disabled");
                await click(webClient.el, "button.o-save");
                const cell = getCell(model, "A1");
                assert.equal(
                    cell.content,
                    "[menu without xmlid](odoo://ir_menu_id/2)",
                    "The content should be the complete markdown link"
                );
                assert.equal(
                    webClient.el.querySelector(".o-link-tool a").text,
                    "menu without xmlid",
                    "The link tooltip should display the menu name"
                );
            }
        );

        QUnit.test("cancel ir.menu selection", async function (assert) {
            assert.expect(4);
            const { webClient } = await openMenuSelector(this.serverData);
            await click(webClient.el, ".o_field_many2one input");
            await click(document.querySelectorAll(".ui-menu-item")[0]);
            assert.containsOnce(webClient, ".o-ir-menu-selector");
            await click(webClient.el, ".modal-footer button.o-cancel");
            assert.containsNone(webClient, ".o-ir-menu-selector");
            assert.equal(labelInput(webClient).value, "", "The label should be empty");
            assert.equal(
                urlInput(webClient).value,
                "",
                "The url displayed should be the menu name"
            );
        });

        QUnit.test("menu many2one field input is focused", async function (assert) {
            assert.expect(1);
            const { webClient } = await openMenuSelector(this.serverData);
            assert.equal(
                document.activeElement,
                webClient.el.querySelector(".o_field_many2one input"),
                "the input should be focused"
            );
        });
    }
);
