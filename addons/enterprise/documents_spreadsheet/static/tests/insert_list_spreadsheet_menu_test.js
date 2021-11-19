/** @odoo-module */

import ListView from "web.ListView";
import testUtils from "web.test_utils";
import { createSpreadsheetFromList } from "./spreadsheet_test_utils";
import { doAction } from "@web/../tests/webclient/helpers";
import * as LegacyFavoriteMenu from "web.FavoriteMenu";
import { InsertListSpreadsheetMenu as LegacyInsertListSpreadsheetMenu } from "@documents_spreadsheet/js/components/insert_list_spreadsheet_menu";

const createView = testUtils.createView;
const legacyFavoriteMenuRegistry = LegacyFavoriteMenu.registry;

QUnit.module(
    "documents_spreadsheet > insert_list_spreadsheet_menu",
    {
        beforeEach: function () {
            legacyFavoriteMenuRegistry.add(
                "insert-list-spreadsheet-menu",
                LegacyInsertListSpreadsheetMenu,
                5
            );
            this.data = {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [{ id: 1, foo: "yop" }],
                },
            };
        },
    },
    function () {
        QUnit.test("Menu item is present in list view", async function (assert) {
            assert.expect(1);

            const list = await createView({
                View: ListView,
                model: "foo",
                data: this.data,
                arch: '<tree><field name="foo"/></tree>',
            });

            await testUtils.dom.click(list.$(".o_favorite_menu button"));
            assert.containsOnce(list, ".o_insert_list_spreadsheet_menu");

            list.destroy();
        });

        QUnit.test("Can save a list in a new spreadsheet", async (assert) => {
            assert.expect(2);

            await createSpreadsheetFromList({
                listView: {
                    mockRPC: async function (route, args) {
                        if (route.includes("get_spreadsheets_to_display")) {
                            return [{ id: 1, name: "My Spreadsheet" }];
                        }
                        if (args.method === "create" && args.model === "documents.document") {
                            assert.step("create");
                            return [1];
                        }
                        if (this) {
                            return this._super.apply(this, arguments);
                        }
                    },
                    session: { user_has_group: async () => true },
                },
                actions: async (controller) => {
                    await testUtils.dom.click(controller.$el.find(".o_favorite_menu button"));
                    await testUtils.dom.click(
                        controller.$el.find(".o_insert_list_spreadsheet_menu")
                    );
                    await testUtils.nextTick();
                    await testUtils.modal.clickButton("Confirm");
                    await testUtils.nextTick();
                },
            });
            assert.verifySteps(["create"]);
        });

        QUnit.test("Can save a list in existing spreadsheet", async (assert) => {
            assert.expect(3);

            const { webClient } = await createSpreadsheetFromList({
                listView: {
                    async mockRPC(route, args) {
                        if (route === "/web/action/load") {
                            return { id: args.action_id, type: "ir.actions.act_window_close" };
                        }
                        if (args.model === "documents.document") {
                            assert.step(args.method);
                            switch (args.method) {
                                case "get_spreadsheets_to_display":
                                    return [{ id: 1, name: "My Spreadsheet" }];
                            }
                        }
                        if (this) {
                            return this._super.apply(this, arguments);
                        }
                    },
                    session: { user_has_group: async () => true },
                },
                async actions(controller) {
                    await testUtils.dom.click(controller.$el.find(".o_favorite_menu button"));
                    await testUtils.dom.click(
                        controller.$el.find(".o_insert_list_spreadsheet_menu")
                    );
                    await testUtils.nextTick();
                    document.body
                        .querySelector(".modal-content option[value='1']")
                        .setAttribute("selected", "selected");
                    await testUtils.modal.clickButton("Confirm");
                },
            });
            await doAction(webClient, 1); // leave the spreadsheet action
            assert.verifySteps(["get_spreadsheets_to_display", "join_spreadsheet_session"]);
        });
    }
);
