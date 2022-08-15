/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { userService } from "@web/core/user_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture } from "@web/../tests/helpers/utils";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeFakeDialogService, makeFakeRPCService } from "@web/../tests/helpers/mock_services";
import { NewViewDialog } from "@web_studio/client_action/editor/new_view_dialogs/new_view_dialog";
import { MapNewViewDialog } from "@web_studio/client_action/editor/new_view_dialogs/map_new_view_dialog";

const { mount } = owl;
const serviceRegistry = registry.category("services");

let env;
let parent;
let target;

QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(async () => {
        const fakeStudioService = {
            start() {
                return {
                    editedAction: {
                        res_model: 'my_model',
                    },
                };
            },
        };
        const fakeOrmService = {
            start() {
                return {
                    call: () =>  ({
                        creation_date: {
                            store: true,
                            type: "date",
                            string: "Creation Date",
                        },
                        finish_date: {
                            store: true,
                            type: "date",
                            string: "Finish Date",
                        },
                        best_partner: {
                            store: true,
                            type: "many2one",
                            string: "My beloved Partner",
                            relation: "res.partner",
                        },
                        worst_partner: {
                            store: true,
                            type: "many2one",
                            string: "My Worst Partner",
                            relation: "res.partner",
                        }
                    }),
                }
            },
        };

        target = getFixture();
        env = await makeTestEnv();
        env["_t"] = (value) =>  value; // NewViewDialog constructor uses Translation

        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("dialog", makeFakeDialogService());

        serviceRegistry.add("rpc", makeFakeRPCService());
        serviceRegistry.add("user", userService);
        serviceRegistry.add("studio", fakeStudioService);
        serviceRegistry.add("orm", fakeOrmService);
    });
    hooks.afterEach(() => {
        if (parent) {
            parent.unmount();
            parent = undefined;
        }
    });

    QUnit.module("NewViewDialog", () => {
        QUnit.test("is rendered with valid values", async (assert) => {
            assert.expect(5);

            parent = await mount(NewViewDialog, { env, target, props: {
                viewType: 'calendar',
                close: () => null,
            } });

            assert.strictEqual(
                target.querySelector(".modal-title").textContent,
                "Generate calendar View",
                "Title should used the given viewType"
            );

            const dateStartSelect = target.querySelector("select[name='date_stop']");
            assert.ok(dateStartSelect, "Default value should be set");
            assert.containsN(dateStartSelect, "option[value]", 2, "Only Date fields should be kept");

            const dateStopSelect = target.querySelector("select[name='date_stop']");
            assert.strictEqual(dateStopSelect.value, "creation_date", "Default value should be set");
            assert.containsN(dateStopSelect, "option[value]", 2, "Only Date fields should be kept");
        });

        QUnit.test("can be submitted", async (assert) => {
            assert.expect(1);

            parent = await mount(NewViewDialog, { env, target, props: {
                viewType: 'calendar',
                close: () => null,
                confirm: () => {
                    assert.deepEqual(Object.keys(parent.fieldsChoice),
                        ["date_start", "date_stop"],
                        "Only submit intended fields"
                    );
                },
            } });

            await click(target, ".modal-dialog button.btn-primary");
        });

        QUnit.module("Map");

        QUnit.test("is rendered with valid values", async (assert) => {
            assert.expect(3);

            parent = await mount(MapNewViewDialog, { env, target, props: {
                close: () => null,
            } });

            assert.strictEqual(
                target.querySelector(".modal-title").textContent,
                "Generate map View",
                "Viewtype must be set to map"
            );

            const dateStartSelect = target.querySelector("select[name='res_partner']");
            assert.ok(dateStartSelect.value, "Default value should be set");
            assert.containsN(dateStartSelect, "option[value]", 2, "Only Partner fields should be kept");
        });

        QUnit.test("can be submitted", async (assert) => {
            assert.expect(1);

            parent = await mount(MapNewViewDialog, { env, target, props: {
                close: () => null,
                confirm: () => {
                    assert.deepEqual(Object.keys(parent.fieldsChoice),
                        ["res_partner"],
                        "Only submit intended fields"
                    );
                },
            } });

            await click(target, ".modal-dialog button.btn-primary");
        });
    });
});


