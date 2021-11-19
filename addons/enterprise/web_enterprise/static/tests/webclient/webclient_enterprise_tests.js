/** @odoo-module **/

import {
    click,
    legacyExtraNextTick,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData, loadState } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { editView } from "@web/views/debug_items";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import testUtils from "web.test_utils";
import { makeFakeEnterpriseService } from "../mocks";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { errorService } from "@web/core/errors/error_service";
import { browser } from "@web/core/browser/browser";

let serverData;
const serviceRegistry = registry.category("services");

// Should test ONLY the webClient and features present in Enterprise
// Those tests rely on hidden view to be in CSS: display: none
QUnit.module("WebClient Enterprise", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        serviceRegistry.add("home_menu", homeMenuService);
        const fakeEnterpriseService = makeFakeEnterpriseService();
        serviceRegistry.add("enterprise", fakeEnterpriseService);
    });
    QUnit.module("basic flow with home menu", (hooks) => {
        let mockRPC;
        hooks.beforeEach((assert) => {
            serverData.menus[1].actionID = 4;
            serverData.menus.root.children = [1];
            serverData.views["partner,false,form"] = `<form>
          <field name="display_name"/>
          <field name="m2o"/>'
      </form>`;
            mockRPC = async (route) => {
                assert.step(route);
                if (route === "/web/dataset/call_kw/partner/get_formview_action") {
                    return {
                        type: "ir.actions.act_window",
                        res_model: "partner",
                        view_type: "form",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "current",
                        res_id: 2,
                    };
                }
            };
        });
        QUnit.test("1 -- start up", async function (assert) {
            assert.expect(7);
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            assert.ok(webClient.el.classList.contains("o_home_menu_background"));
            assert.ok(webClient.el.classList.contains("o_has_home_menu"));
            assert.containsOnce(webClient, ".o_home_menu");
            assert.isNotVisible(webClient.el.querySelector(".o_menu_toggle"));
            assert.containsOnce(webClient, ".o_app.o_menuitem");
        });
        QUnit.test("2 -- navbar updates on displaying an action", async function (assert) {
            assert.expect(12);
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(webClient.el.querySelector(".o_app.o_menuitem"));
            await nextTick(); // there is another tick to update navar and destroy HomeMenu
            await legacyExtraNextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ]);
            assert.notOk(webClient.el.classList.contains("o_home_menu_background"));
            //assert.containsNone(webClient, ".o_home_menu");
            assert.isNotVisible(webClient.el.querySelector(".o_home_menu"));
            //assert.containsOnce(webClient, ".o_kanban_view");
            assert.isVisible(webClient.el.querySelector(".o_kanban_view"));
            const menuToggle = webClient.el.querySelector(".o_menu_toggle");
            assert.isVisible(menuToggle);
            assert.ok(menuToggle.classList.contains("fa-th"));
            assert.notOk(menuToggle.classList.contains("fa-chevron-left"));
        });
        QUnit.test("3 -- push another action in the breadcrumb", async function (assert) {
            assert.expect(11);
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(webClient.el.querySelector(".o_app.o_menuitem"));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ]);
            await click(webClient.el.querySelector(".o_kanban_record"));
            await nextTick(); // there is another tick to update navbar and destroy HomeMenu
            await legacyExtraNextTick();
            assert.verifySteps(["/web/dataset/call_kw/partner/read"]);
            assert.isVisible(webClient.el.querySelector(".o_menu_toggle"));
            assert.containsOnce(webClient, ".o_form_view");
            assert.strictEqual(
                webClient.el.querySelector(".breadcrumb-item.active").textContent,
                "First record"
            );
        });
        QUnit.test("4 -- push a third action in the breadcrumb", async function (assert) {
            assert.expect(15);
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(webClient.el.querySelector(".o_app.o_menuitem"));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ]);
            await click(webClient.el.querySelector(".o_kanban_record"));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps(["/web/dataset/call_kw/partner/read"]);
            await click(webClient.el.querySelector('.o_field_widget[name="m2o"]'));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps([
                "/web/dataset/call_kw/partner/get_formview_action",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/call_kw/partner/read",
            ]);
            assert.containsOnce(webClient, ".o_form_view");
            assert.strictEqual(
                webClient.el.querySelector(".breadcrumb-item.active").textContent,
                "Second record"
            );
            assert.containsN(webClient, ".breadcrumb-item", 3);
        });
        QUnit.test(
            "5 -- switch to HomeMenu from an action with 2 breadcrumbs",
            async function (assert) {
                assert.expect(17);
                const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
                assert.verifySteps(["/web/webclient/load_menus"]);
                await click(webClient.el.querySelector(".o_app.o_menuitem"));
                await nextTick();
                await legacyExtraNextTick();
                assert.verifySteps([
                    "/web/action/load",
                    "/web/dataset/call_kw/partner/load_views",
                    "/web/dataset/search_read",
                ]);
                await click(webClient.el.querySelector(".o_kanban_record"));
                await nextTick();
                await legacyExtraNextTick();
                assert.verifySteps(["/web/dataset/call_kw/partner/read"]);
                await click(webClient.el.querySelector('.o_field_widget[name="m2o"]'));
                await nextTick();
                await legacyExtraNextTick();
                assert.verifySteps([
                    "/web/dataset/call_kw/partner/get_formview_action",
                    "/web/dataset/call_kw/partner/load_views",
                    "/web/dataset/call_kw/partner/read",
                ]);
                const menuToggle = webClient.el.querySelector(".o_menu_toggle");
                await click(menuToggle);
                await nextTick();
                assert.verifySteps([]);
                assert.notOk(menuToggle.classList.contains("fa-th"));
                assert.ok(menuToggle.classList.contains("fa-chevron-left"));
                assert.containsOnce(webClient, ".o_home_menu");
                assert.isNotVisible(webClient.el.querySelector(".o_form_view"));
            }
        );
        QUnit.test("6 -- back to underlying action with many breadcrumbs", async function (assert) {
            assert.expect(20);
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(webClient.el.querySelector(".o_app.o_menuitem"));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ]);
            await click(webClient.el.querySelector(".o_kanban_record"));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps(["/web/dataset/call_kw/partner/read"]);
            await click(webClient.el.querySelector('.o_field_widget[name="m2o"]'));
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps([
                "/web/dataset/call_kw/partner/get_formview_action",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/call_kw/partner/read",
            ]);
            const menuToggle = webClient.el.querySelector(".o_menu_toggle");
            await click(menuToggle);
            await click(menuToggle);
            // if we don't reload on going back to underlying action
            // assert.verifySteps(
            //   [],
            //   "the underlying view should not reload when toggling the HomeMenu to off"
            // );
            // endif
            // if we reload on going back to underlying action
            await nextTick();
            await legacyExtraNextTick();
            assert.verifySteps(
                ["/web/dataset/call_kw/partner/read"],
                "the underlying view should reload when toggling the HomeMenu to off"
            );
            // endif
            assert.containsNone(webClient, ".o_home_menu");
            assert.containsOnce(webClient, ".o_form_view");
            assert.ok(menuToggle.classList.contains("fa-th"));
            assert.notOk(menuToggle.classList.contains("fa-chevron-left"));
            assert.strictEqual(
                webClient.el.querySelector(".breadcrumb-item.active").textContent,
                "Second record"
            );
            assert.containsN(webClient, ".breadcrumb-item", 3);
        });
        QUnit.test("restore the newly created record in form view (legacy)", async (assert) => {
            assert.expect(7);
            const action = serverData.actions[6];
            delete action.res_id;
            action.target = "current";
            const webClient = await createEnterpriseWebClient({ serverData });

            await doAction(webClient, 6);
            let formEl = webClient.el.querySelector(".o_form_view");
            assert.isVisible(formEl);
            assert.ok(formEl.classList.contains("o_form_editable"));
            const input = webClient.el.querySelector("input.o_input");
            await testUtils.fields.editInput(input, "red right hand");
            await click(webClient.el.querySelector(".o_form_button_save"));
            assert.strictEqual(
                webClient.el.querySelector(".breadcrumb-item.active").textContent,
                "red right hand"
            );
            await click(webClient.el.querySelector(".o_menu_toggle"));
            assert.isNotVisible(webClient.el.querySelector(".o_form_view"));

            await click(webClient.el.querySelector(".o_menu_toggle"));
            await nextTick();
            await legacyExtraNextTick();
            formEl = webClient.el.querySelector(".o_form_view");
            assert.isVisible(formEl);
            assert.notOk(formEl.classList.contains("o_form_editable"));
            assert.strictEqual(
                webClient.el.querySelector(".breadcrumb-item.active").textContent,
                "red right hand"
            );
        });
        QUnit.skip("fast clicking on restore (implementation detail)", async (assert) => {
            assert.expect(6);

            let doVeryFastClick = false;

            class DelayedClientAction extends owl.Component {
                mounted() {
                    if (doVeryFastClick) {
                        doVeryFastClick = false;
                        click(webClient.el.querySelector(".o_menu_toggle"));
                    }
                }
            }
            DelayedClientAction.template = owl.tags.xml`<div class='delayed_client_action'>
                <button t-on-click="resolve">RESOLVE</button>
            </div>`;

            registry.category("actions").add("DelayedClientAction", DelayedClientAction);
            const webClient = await createEnterpriseWebClient({ serverData });
            await doAction(webClient, "DelayedClientAction");
            await nextTick();
            await click(webClient.el.querySelector(".o_menu_toggle"));
            assert.isVisible(webClient.el.querySelector(".o_home_menu"));
            assert.isNotVisible(webClient.el.querySelector(".delayed_client_action"));

            doVeryFastClick = true;
            await click(webClient.el.querySelector(".o_menu_toggle"));
            await nextTick();
            // off homemenu
            assert.isVisible(webClient.el.querySelector(".o_home_menu"));
            assert.isNotVisible(webClient.el.querySelector(".delayed_client_action"));

            await click(webClient.el.querySelector(".o_menu_toggle"));
            await nextTick();
            assert.isNotVisible(webClient.el.querySelector(".o_home_menu"));
            assert.isVisible(webClient.el.querySelector(".delayed_client_action"));
        });
    });
    QUnit.test("clear unCommittedChanges when toggling home menu", async function (assert) {
        assert.expect(7);
        // Edit a form view, don't save, toggle home menu
        // the autosave feature of the Form view is activated
        // and relied upon by this test

        const mockRPC = (route, args) => {
            if (args.method === "create") {
                assert.strictEqual(args.model, "partner");
                assert.deepEqual(args.args, [
                    {
                        display_name: "red right hand",
                        foo: false,
                    },
                ]);
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, 3, { viewType: "form" });
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_form_view.o_form_editable");
        const input = webClient.el.querySelector("input.o_input");
        await testUtils.fields.editInput(input, "red right hand");

        await click(webClient.el.querySelector(".o_menu_toggle"));
        await nextTick();
        assert.isNotVisible(webClient.el.querySelector(".o_form_view"));
        assert.containsNone(document.body, ".modal");
        assert.containsOnce(webClient, ".o_home_menu");
        assert.isVisible(webClient.el.querySelector(".o_home_menu"));
    });
    QUnit.test("can have HomeMenu and dialog action", async function (assert) {
        assert.expect(6);
        const webClient = await createEnterpriseWebClient({ serverData });
        await nextTick();
        assert.containsOnce(webClient, ".o_home_menu");
        assert.containsNone(webClient, ".modal .o_form_view");
        await doAction(webClient, 5);
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".modal .o_form_view");
        assert.isVisible(webClient.el.querySelector(".modal .o_form_view"));
        assert.containsOnce(webClient, ".o_home_menu");
        assert.isVisible(webClient.el.querySelector(".o_home_menu"));
    });
    QUnit.test("supports attachments of apps deleted", async function (assert) {
        assert.expect(1);
        // When doing a pg_restore without the filestore
        // LPE fixme: may not be necessary anymore since menus are not HomeMenu props anymore
        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: {
                id: 1,
                appID: 1,
                actionID: 1,
                xmlid: "",
                name: "Partners",
                children: [],
                webIconData: "",
                webIcon: "bloop,bloop",
            },
        };
        patchWithCleanup(odoo, { debug: "1" });
        const webClient = await createEnterpriseWebClient({ serverData });
        assert.containsOnce(webClient, ".o_home_menu");
    });
    QUnit.test(
        "debug manager resets to global items when home menu is displayed",
        async function (assert) {
            assert.expect(9);
            const debugRegistry = registry.category("debug");
            debugRegistry.category("view").add("editView", editView);
            debugRegistry.category("default").add("item_1", () => {
                return {
                    type: "item",
                    description: "globalItem",
                    callback: () => {},
                    sequence: 10,
                };
            });
            const mockRPC = async (route) => {
                if (route.includes("check_access_rights")) {
                    return true;
                }
            };
            patchWithCleanup(odoo, { debug: "1" });
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await click(webClient.el.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('globalItem')"
            );
            assert.containsNone(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
            await click(webClient.el.querySelector(".o_debug_manager .dropdown-toggle"));
            await doAction(webClient, 1);
            await click(webClient.el.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('globalItem')"
            );
            assert.containsOnce(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
            await click(webClient.el.querySelector(".o_menu_toggle"));
            await click(webClient.el.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('globalItem')"
            );
            assert.containsNone(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
            await click(webClient.el.querySelector(".o_debug_manager .dropdown-toggle"));
            await doAction(webClient, 3);
            await click(webClient.el.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('globalItem')"
            );
            assert.containsOnce(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('Edit View: List')"
            );
            assert.containsNone(
                webClient.el,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
        }
    );
    QUnit.test(
        "url state is well handled when going in and out of the HomeMenu",
        async function (assert) {
            assert.expect(4);

            const webClient = await createEnterpriseWebClient({ serverData });
            await nextTick();
            assert.deepEqual(webClient.env.services.router.current.hash, { action: "menu" });

            await click(webClient.el.querySelector(".o_app.o_menuitem:nth-child(2)"));
            await legacyExtraNextTick();
            assert.deepEqual(webClient.env.services.router.current.hash, {
                action: 1002,
                menu_id: 2,
            });

            await click(webClient.el.querySelector(".o_menu_toggle"));
            await nextTick();
            assert.deepEqual(webClient.env.services.router.current.hash, { action: "menu" });

            await click(webClient.el.querySelector(".o_menu_toggle"));
            // if we reload on going back to underlying action
            await legacyExtraNextTick();
            // end if
            assert.deepEqual(webClient.env.services.router.current.hash, {
                action: 1002,
                menu_id: 2,
            });
        }
    );
    QUnit.test(
        "underlying action's menu items are invisible when HomeMenu is displayed",
        async function (assert) {
            assert.expect(10);
            serverData.menus[1].children = [99];
            serverData.menus[99] = {
                id: 99,
                children: [],
                name: "SubMenu",
                appID: 1,
                actionID: 1002,
                xmlid: "",
                webIconData: undefined,
                webIcon: false,
            };
            const webClient = await createEnterpriseWebClient({ serverData });
            assert.containsNone(webClient.el, "nav .o_menu_sections");
            assert.containsNone(webClient.el, "nav .o_menu_brand");
            await click(webClient.el.querySelector(".o_app.o_menuitem:nth-child(1)"));
            await nextTick();
            assert.containsOnce(webClient.el, "nav .o_menu_sections");
            assert.containsOnce(webClient.el, "nav .o_menu_brand");
            assert.isVisible(webClient.el.querySelector(".o_menu_sections"));
            assert.isVisible(webClient.el.querySelector(".o_menu_brand"));
            await click(webClient.el.querySelector(".o_menu_toggle"));
            assert.containsOnce(webClient.el, "nav .o_menu_sections");
            assert.containsOnce(webClient.el, "nav .o_menu_brand");
            assert.isNotVisible(webClient.el.querySelector(".o_menu_sections"));
            assert.isNotVisible(webClient.el.querySelector(".o_menu_brand"));
        }
    );
    QUnit.test("loadState back and forth keeps relevant keys in state", async function (assert) {
        assert.expect(9);

        const webClient = await createEnterpriseWebClient({ serverData });

        await click(webClient.el.querySelector(".o_app.o_menuitem:nth-child(2)"));
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".test_client_action");
        assert.containsNone(webClient, ".o_home_menu");
        const state = webClient.env.services.router.current.hash;
        assert.deepEqual(state, {
            action: 1002,
            menu_id: 2,
        });

        await loadState(webClient, {});
        assert.containsNone(webClient, ".test_client_action");
        assert.containsOnce(webClient, ".o_home_menu");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "menu",
        });

        await loadState(webClient, state);
        assert.containsOnce(webClient, ".test_client_action");
        assert.containsNone(webClient, ".o_home_menu");
        assert.deepEqual(webClient.env.services.router.current.hash, state);
    });

    QUnit.test(
        "go back to home menu using browser back button (i.e. loadState)",
        async function (assert) {
            assert.expect(7);

            const webClient = await createEnterpriseWebClient({ serverData });
            assert.containsOnce(webClient, ".o_home_menu");
            assert.isNotVisible(webClient.el.querySelector(".o_main_navbar .o_menu_toggle"));

            await click(webClient.el.querySelector(".o_app.o_menuitem:nth-child(2)"));
            await legacyExtraNextTick();
            assert.containsOnce(webClient, ".test_client_action");
            assert.containsNone(webClient, ".o_home_menu");

            await loadState(webClient, { action: "menu" }); // FIXME: this might need to be changed
            assert.containsNone(webClient, ".test_client_action");
            assert.containsOnce(webClient, ".o_home_menu");
            assert.isNotVisible(webClient.el.querySelector(".o_main_navbar .o_menu_toggle"));
        }
    );

    QUnit.test("initial action crashes", async (assert) => {
        assert.expect(6);

        const handler = (ev) => {
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => window.removeEventListener("unhandledrejection", handler));

        patchWithCleanup(QUnit, {
            onUnhandledRejection: () => {},
        });

        browser.location.hash = "#action=__test__client__action__&menu_id=1";
        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                assert.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        registry.category("services").add("error", errorService);

        const webClient = await createEnterpriseWebClient({ serverData });
        assert.verifySteps(["clientAction setup"]);
        assert.containsOnce(webClient, "nav .o_menu_toggle.fa-th");
        assert.isVisible(webClient.el.querySelector("nav .o_menu_toggle.fa-th"));
        assert.strictEqual(webClient.el.querySelector(".o_action_manager").innerHTML, "");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "__test__client__action__",
            menu_id: 1,
        });
    });
});
