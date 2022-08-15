/** @odoo-module **/
import { legacyExtraNextTick, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { companyService } from "@web/webclient/company_service";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import testUtils from "web.test_utils";
import { openStudio, leaveStudio, registerStudioDependencies } from "@web_studio/../tests/helpers";
import { session } from "@web/session";

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

let serverData;

QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        registerStudioDependencies();
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("company", companyService);

        // tweak a bit the default config to better fit with studio needs:
        //  - add some menu items we can click on to test the navigation
        //  - add a one2many field in a form view to test the one2many edition
        serverData.menus = {
            root: { id: "root", children: [1, 2, 3], name: "root", appID: "root" },
            1: {
                id: 1,
                children: [11, 12],
                name: "Partners",
                appID: 1,
                actionID: 4,
                xmlid: "app_1",
            },
            11: {
                id: 11,
                children: [],
                name: "Partners (Action 4)",
                appID: 1,
                actionID: 4,
                xmlid: "menu_11",
            },
            12: {
                id: 12,
                children: [],
                name: "Partners (Action 3)",
                appID: 1,
                actionID: 3,
                xmlid: "menu_12",
            },
            2: {
                id: 2,
                children: [],
                name: "Ponies",
                appID: 2,
                actionID: 8,
                xmlid: "app_2",
            },
            3: {
                id: 3,
                children: [],
                name: "Client Action",
                appID: 3,
                actionID: 9,
                xmlid: "app_3",
            },
        };
        serverData.models.partner.fields.date = { string: "Date", type: "date" };
        serverData.models.partner.fields.pony_id = {
            string: "Pony",
            type: "many2one",
            relation: "pony",
        };
        serverData.models.pony.fields.partner_ids = {
            string: "Partners",
            type: "one2many",
            relation: "partner",
            relation_field: "pony_id",
        };
        serverData.views["pony,false,form"] = `
            <form>
                <field name="name"/>
                <field name='partner_ids'>
                    <form>
                        <sheet>
                            <field name='display_name'/>
                        </sheet>
                    </form>
                </field>
            </form>`;
    });

    QUnit.module("Studio Navigation");

    QUnit.test("Studio not available for non system users", async function (assert) {
        assert.expect(2);

        patchWithCleanup(session, { is_system: false });
        const webClient = await createEnterpriseWebClient({ serverData });
        assert.containsOnce(webClient, ".o_main_navbar");

        assert.containsNone(webClient, ".o_main_navbar .o_web_studio_navbar_item a");
    });

    QUnit.test("open Studio with act_window", async function (assert) {
        assert.expect(22);

        const mockRPC = async (route) => {
            assert.step(route);
        };
        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        assert.containsOnce(webClient, ".o_home_menu");

        // open app Partners (act window action)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await legacyExtraNextTick();

        assert.containsOnce(webClient, ".o_kanban_view");
        assert.verifySteps(
            [
                "/web/webclient/load_menus",
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ],
            "should have loaded the action"
        );
        assert.containsOnce(webClient, ".o_main_navbar .o_web_studio_navbar_item a");

        await openStudio(webClient);

        assert.verifySteps(
            [
                "/web_studio/activity_allowed",
                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/partner", // load_views with studio in context (from legacy code)
                "/web/dataset/search_read",
            ],
            "should have opened the action in Studio"
        );

        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_kanban_view_editor",
            "the kanban view should be opened"
        );
        assert.containsOnce(
            webClient,
            ".o_kanban_record:contains(yop)",
            "the first partner should be displayed"
        );
        assert.containsOnce(webClient, ".o_studio_navbar .o_web_studio_leave a");

        await leaveStudio(webClient);

        assert.verifySteps(
            [
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ],
            "should have reloaded the previous action edited by Studio"
        );

        assert.containsNone(webClient, ".o_web_studio_client_action", "Studio should be closed");
        assert.containsOnce(
            webClient,
            ".o_kanban_view .o_kanban_record:contains(yop)",
            "the first partner should be displayed in kanban"
        );
    });

    QUnit.test("open Studio with act_window and viewType", async function (assert) {
        assert.expect(4);

        const webClient = await createEnterpriseWebClient({ serverData });

        // open app Partners (act window action), sub menu Partners (action 3)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await legacyExtraNextTick();
        // the menu is rendered once the action is ready, so potentially in the next animation frame
        await testUtils.nextTick();
        await testUtils.dom.click(
            $(webClient.el).find('.o_menu_sections .o_nav_entry:contains("Partners (Action 3)")')
        );
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_list_view");

        await testUtils.dom.click(webClient.el.querySelector(".o_data_row")); // open a record
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_form_view");

        await openStudio(webClient);
        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_form_view_editor",
            "the form view should be opened"
        );
        assert.strictEqual(
            $(webClient.el).find('.o_field_widget[name="foo"]').text(),
            "yop",
            "the first partner should be displayed"
        );
    });

    QUnit.test("reload the studio view", async function (assert) {
        assert.expect(5);

        const webClient = await createEnterpriseWebClient({ serverData });

        // open app Partners (act window action), sub menu Partners (action 3)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $(webClient.el).find(".o_kanban_record:contains(yop)").length,
            1,
            "the first partner should be displayed"
        );

        await testUtils.dom.click(webClient.el.querySelector(".o_kanban_record")); // open a record
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_form_view");
        assert.strictEqual(
            $(webClient.el).find(".o_form_view span:contains(yop)").length,
            1,
            "should have open the same record"
        );

        await openStudio(webClient);
        await webClient.env.services.studio.reload();

        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_form_view_editor",
            "the studio view should be opened after reloading"
        );
        assert.strictEqual(
            $(webClient.el).find(".o_form_view span:contains(yop)").length,
            1,
            "should have open the same record"
        );
    });

    QUnit.test("switch view and close Studio", async function (assert) {
        assert.expect(6);

        const webClient = await createEnterpriseWebClient({ serverData });
        // open app Partners (act window action)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_kanban_view");

        await openStudio(webClient);
        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_kanban_view_editor"
        );

        // click on tab "Views"
        await testUtils.dom.click(
            webClient.el.querySelector(".o_web_studio_menu .o_web_studio_menu_item a")
        );
        assert.containsOnce(webClient, ".o_web_studio_action_editor");

        // open list view
        await testUtils.dom.click(
            webClient.el.querySelector(
                ".o_web_studio_views .o_web_studio_view_type[data-type=list] .o_web_studio_thumbnail"
            )
        );
        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_list_view_editor"
        );

        await leaveStudio(webClient);

        assert.containsNone(webClient, ".o_web_studio_client_action", "Studio should be closed");
        assert.containsOnce(webClient, ".o_list_view", "the list view should be opened");
    });

    QUnit.test("navigation in Studio with act_window", async function (assert) {
        assert.expect(28);

        const mockRPC = async (route) => {
            assert.step(route);
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        // open app Partners (act window action)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await legacyExtraNextTick();

        assert.verifySteps(
            [
                "/web/webclient/load_menus",
                "/web/action/load",
                "/web/dataset/call_kw/partner/load_views",
                "/web/dataset/search_read",
            ],
            "should have loaded the action"
        );

        await openStudio(webClient);

        assert.verifySteps(
            [
                "/web_studio/activity_allowed",
                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/partner", // load_views with studio in context
                "/web/dataset/search_read",
            ],
            "should have opened the action in Studio"
        );

        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_kanban_view_editor",
            "the kanban view should be opened"
        );
        assert.strictEqual(
            $(webClient.el).find(".o_kanban_record:contains(yop)").length,
            1,
            "the first partner should be displayed"
        );

        await testUtils.dom.click(webClient.el.querySelector(".o_studio_navbar .o_menu_toggle"));

        assert.containsOnce(webClient, ".o_studio_home_menu");

        // open app Ponies (act window action)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_2]"));
        await legacyExtraNextTick();

        assert.verifySteps(
            [
                "/web/action/load",
                "/web_studio/activity_allowed",
                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/pony", // load_views with studio in context
                "/web/dataset/search_read",
            ],
            "should have opened the navigated action in Studio"
        );

        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_list_view_editor",
            "the list view should be opened"
        );
        assert.strictEqual(
            $(webClient.el).find(".o_list_view .o_data_cell").text(),
            "Twilight SparkleApplejackFluttershy",
            "the list of ponies should be correctly displayed"
        );

        await leaveStudio(webClient);

        assert.verifySteps(
            [
                "/web/action/load",
                "/web/dataset/call_kw/pony/load_views",
                "/web/dataset/search_read",
            ],
            "should have reloaded the previous action edited by Studio"
        );

        assert.containsNone(webClient, ".o_web_studio_client_action", "Studio should be closed");
        assert.containsOnce(webClient, ".o_list_view", "the list view should be opened");
        assert.strictEqual(
            $(webClient.el).find(".o_list_view .o_data_cell").text(),
            "Twilight SparkleApplejackFluttershy",
            "the list of ponies should be correctly displayed"
        );
    });

    QUnit.test("keep action context when leaving Studio", async function (assert) {
        assert.expect(5);

        let nbLoadAction = 0;
        const mockRPC = async (route, args) => {
            if (route === "/web/action/load") {
                nbLoadAction++;
                if (nbLoadAction === 2) {
                    assert.strictEqual(
                        args.additional_context.active_id,
                        1,
                        "the context should be correctly passed when leaving Studio"
                    );
                }
            }
        };
        serverData.actions[4].context = "{'active_id': 1}";

        const webClient = await createEnterpriseWebClient({
            serverData,
            mockRPC,
        });
        // open app Partners (act window action)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await legacyExtraNextTick();

        assert.containsOnce(webClient, ".o_kanban_view");

        await openStudio(webClient);

        assert.containsOnce(webClient, ".o_web_studio_kanban_view_editor");

        await leaveStudio(webClient);

        assert.containsOnce(webClient, ".o_kanban_view");
        assert.strictEqual(nbLoadAction, 2, "the action should have been loaded twice");
    });

    QUnit.test("open same record when leaving form", async function (assert) {
        assert.expect(5);

        const webClient = await createEnterpriseWebClient({ serverData });
        // open app Ponies (act window action)
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_2]"));
        await legacyExtraNextTick();

        assert.containsOnce(webClient, ".o_list_view");

        await testUtils.dom.click(
            $(webClient.el).find(".o_list_view tbody tr:first td:contains(Twilight Sparkle)")
        );
        await legacyExtraNextTick();

        assert.containsOnce(webClient, ".o_form_view");

        await openStudio(webClient);

        assert.containsOnce(
            webClient,
            ".o_web_studio_client_action .o_web_studio_form_view_editor",
            "the form view should be opened"
        );

        await leaveStudio(webClient);
        assert.containsOnce(webClient, ".o_form_view", "the form view should be opened");
        assert.strictEqual(
            $(webClient.el).find(".o_form_view span:contains(Twilight Sparkle)").length,
            1,
            "should have open the same record"
        );
    });

    QUnit.test("open Studio with non editable view", async function (assert) {
        assert.expect(2);

        serverData.menus[99] = {
            id: 9,
            children: [],
            name: "Action with Grid view",
            appID: 9,
            actionID: 99,
            xmlid: "app_9",
        };
        serverData.menus.root.children.push(99);
        serverData.actions[99] = {
            id: 99,
            xml_id: "some.xml_id",
            name: "Partners Action 99",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [42, "grid"],
                [2, "list"],
                [false, "form"],
            ],
        };
        serverData.views["partner,42,grid"] = `
            <grid>
                <field name="foo" type="row"/>
                <field name="id" type="measure"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                </field>
            </grid>`;

        const webClient = await createEnterpriseWebClient({
            serverData,
            legacyParams: { withLegacyMockServer: true },
        });
        await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_9]"));
        await legacyExtraNextTick();

        assert.containsOnce(webClient, ".o_grid_view");

        await openStudio(webClient);

        assert.containsOnce(
            webClient,
            ".o_web_studio_action_editor",
            "action editor should be opened (grid is not editable)"
        );
    });

    QUnit.test(
        "open list view with sample data gives empty list view in studio",
        async function (assert) {
            assert.expect(2);

            serverData.models.pony.records = [];
            serverData.views["pony,false,list"] = `<tree sample="1"><field name="name"/></tree>`;

            const webClient = await createEnterpriseWebClient({
                serverData,
            });
            // open app Ponies (act window action)
            await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_2]"));
            await legacyExtraNextTick();

            assert.ok(
                [...webClient.el.querySelectorAll(".o_list_table .o_data_row")].length > 0,
                "there should be some sample data in the list view"
            );

            await openStudio(webClient);

            assert.containsNone(
                webClient,
                ".o_list_table .o_data_row",
                "the list view should not contain any data"
            );
        }
    );

    QUnit.test(
        "open Studio with editable form view and check context propagation",
        async function (assert) {
            assert.expect(6);

            serverData.menus[43] = {
                id: 43,
                children: [],
                name: "Form with context",
                appID: 43,
                actionID: 43,
                xmlid: "app_43",
            };
            serverData.menus.root.children.push(43);
            serverData.actions[43] = {
                id: 43,
                name: "Pony Action 43",
                res_model: "pony",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                context: "{'default_type': 'foo'}",
                res_id: 4,
                xml_id: "action_43",
            };

            const mockRPC = async (route, args) => {
                if (route === "/web/dataset/call_kw/pony/read") {
                    // We pass here twice: once for the "classic" action
                    // and once when entering studio
                    assert.strictEqual(args.kwargs.context.default_type, "foo");
                }
                if (route === "/web/dataset/call_kw/partner/onchange") {
                    assert.ok(
                        !("default_type" in args.kwargs.context),
                        "'default_x' context value should not be propaged to x2m model"
                    );
                }
            };

            const webClient = await createEnterpriseWebClient({
                serverData,
                mockRPC,
            });
            await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_43]"));
            await legacyExtraNextTick();

            assert.containsOnce(webClient, ".o_form_view");

            await openStudio(webClient);

            assert.containsOnce(
                webClient,
                ".o_web_studio_client_action .o_web_studio_form_view_editor",
                "the form view should be opened"
            );

            await testUtils.dom.click(
                webClient.el.querySelector(".o_web_studio_form_view_editor .o_field_one2many")
            );
            await testUtils.dom.click(
                webClient.el.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );

            assert.containsOnce(
                webClient,
                ".o_web_studio_client_action .o_web_studio_form_view_editor",
                "the form view should be opened"
            );
        }
    );

    QUnit.test(
        "concurrency: execute a non editable action and try to enter studio",
        async function (assert) {
            // the purpose of this test is to ensure that there's no time window
            // just after an action manager update during which the icon isn't
            // disabled even though the current action isn't editable
            assert.expect(5);

            const def = makeDeferred();
            serverData.actions[4].xml_id = false; // make action 4 non editable
            const webClient = await createEnterpriseWebClient({ serverData });
            assert.containsOnce(webClient, ".o_home_menu");

            webClient.env.bus.on("ACTION_MANAGER:UI-UPDATED", null, () => {
                assert.containsOnce(webClient, ".o_kanban_view");
                assert.hasClass(
                    webClient.el.querySelector(".o_web_studio_navbar_item"),
                    "o_disabled"
                );
                def.resolve();
            });

            // open app Partners (non editable act window action)
            await testUtils.dom.click(webClient.el.querySelector(".o_app[data-menu-xmlid=app_1]"));
            await def;

            assert.containsOnce(webClient, ".o_kanban_view");
            assert.hasClass(webClient.el.querySelector(".o_web_studio_navbar_item"), "o_disabled");
        }
    );
});
