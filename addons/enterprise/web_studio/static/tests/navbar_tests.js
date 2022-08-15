/** @odoo-module **/

import { StudioNavbar } from "@web_studio/client_action/navbar/navbar";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, nextTick, patchWithCleanup, legacyExtraNextTick } from "@web/../tests/helpers/utils";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { makeFakeDialogService } from "@web/../tests/helpers/mock_services";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registerStudioDependencies, openStudio, leaveStudio } from "./helpers";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { getActionManagerServerData, loadState } from "@web/../tests/webclient/helpers";
import { companyService } from "@web/webclient/company_service";

const { mount } = owl;
const serviceRegistry = registry.category("services");

QUnit.module("Studio > Navbar", (hooks) => {
    let baseConfig;
    hooks.beforeEach(() => {
        registerStudioDependencies();
        serviceRegistry.add("action", actionService);
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("menu", menuService);
        serviceRegistry.add("hotkey", hotkeyService);
        patchWithCleanup(browser, {
            setTimeout: (handler, delay, ...args) => handler(...args),
            clearTimeout: () => {},
        });
        const menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [10, 11, 12], name: "App0", appID: 1 },
            10: { id: 10, children: [], name: "Section 10", appID: 1 },
            11: { id: 11, children: [], name: "Section 11", appID: 1 },
            12: { id: 12, children: [120, 121, 122], name: "Section 12", appID: 1 },
            120: { id: 120, children: [], name: "Section 120", appID: 1 },
            121: { id: 121, children: [], name: "Section 121", appID: 1 },
            122: { id: 122, children: [], name: "Section 122", appID: 1 },
        };
        const serverData = { menus };
        baseConfig = { serverData };
    });

    QUnit.test("menu buttons will not be placed under 'more' menu", async (assert) => {
        assert.expect(12);

        class MyStudioNavbar extends StudioNavbar {
            async adapt() {
                const prom = super.adapt();
                const sectionsCount = this.currentAppSections.length;
                const hiddenSectionsCount = this.currentAppSectionsExtra.length;
                assert.step(`adapt -> hide ${hiddenSectionsCount}/${sectionsCount} sections`);
                return prom;
            }
        }

        const env = await makeTestEnv(baseConfig);
        patchWithCleanup(env.services.studio, {
            get mode() {
                // Will force the the navbar in the studio editor state
                return "editor";
            },
        });
        // Force the parent width, to make this test independent of screen size
        const target = getFixture();
        target.style.width = "100%";

        // Set menu and mount
        env.services.menu.setCurrentMenu(1);
        const navbar = await mount(MyStudioNavbar, { env, target });
        registerCleanup(() => navbar.destroy());
        await nextTick();

        assert.containsN(
            navbar.el,
            ".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)",
            3,
            "should have 3 menu sections displayed (that are not the 'more' menu)"
        );
        assert.containsNone(navbar.el, ".o_menu_sections_more", "the 'more' menu should not exist");
        assert.containsN(
            navbar.el,
            ".o-studio--menu > *",
            2,
            "should have 2 studio menu elements displayed"
        );
        assert.deepEqual(
            [...navbar.el.querySelectorAll(".o-studio--menu > *")].map((el) => el.innerText),
            ["Edit Menu", "New Model"]
        );

        // Force minimal width and dispatch window resize event
        navbar.el.style.width = "0%";
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        assert.containsOnce(
            navbar.el,
            ".o_menu_sections > *:not(.d-none)",
            "only one menu section should be displayed"
        );
        assert.containsOnce(
            navbar.el,
            ".o_menu_sections_more:not(.d-none)",
            "the displayed menu section should be the 'more' menu"
        );
        assert.containsN(
            navbar.el,
            ".o-studio--menu > *",
            2,
            "should have 2 studio menu elements displayed"
        );
        assert.deepEqual(
            [...navbar.el.querySelectorAll(".o-studio--menu > *")].map((el) => el.innerText),
            ["Edit Menu", "New Model"]
        );

        // Open the more menu
        await click(navbar.el, ".o_menu_sections_more .dropdown-toggle");
        assert.deepEqual(
            [...navbar.el.querySelectorAll(".dropdown-menu > *")].map((el) => el.textContent),
            ["Section 10", "Section 11", "Section 12", "Section 120", "Section 121", "Section 122"],
            "'more' menu should contain all hidden sections in correct order"
        );

        // Check the navbar adaptation calls
        assert.verifySteps(["adapt -> hide 0/3 sections", "adapt -> hide 3/3 sections"]);
    });

    QUnit.test("homemenu customizer rendering", async (assert) => {
        assert.expect(6);

        serviceRegistry.add("company", companyService);

        const fakeHTTPService = {
            start() {
                return {};
            },
        };
        serviceRegistry.add("http", fakeHTTPService);

        const env = await makeTestEnv(baseConfig);

        patchWithCleanup(env.services.studio, {
            get mode() {
                // Will force the navbar in the studio home_menu state
                return "home_menu";
            },
        });

        const target = getFixture();

        // Set menu and mount
        const navbar = await mount(StudioNavbar, { env, target });
        registerCleanup(() => navbar.destroy());
        await nextTick();

        assert.containsOnce(navbar.el, ".o_studio_navbar");
        assert.containsOnce(navbar.el, ".o_web_studio_home_studio_menu");

        await click(navbar.el.querySelector(".o_web_studio_home_studio_menu .dropdown-toggle"));

        assert.containsOnce(navbar.el, ".o_web_studio_change_background");
        assert.strictEqual(navbar.el.querySelector(".o_web_studio_change_background input").accept, "image/*", "Input should now only accept images");

        assert.containsOnce(navbar.el, ".o_web_studio_import");
        assert.containsOnce(navbar.el, ".o_web_studio_export");
    });
});

QUnit.module("Studio > navbar coordination", (hooks) => {
    let serverData;
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        registerStudioDependencies();
        serviceRegistry.add("company", companyService);
    });

    QUnit.test("adapt navbar when leaving studio", async (assert) => {
        assert.expect(8);

        patchWithCleanup(browser, {
            setTimeout: (handler, delay, ...args) => handler(...args),
            clearTimeout: () => {},
        });

        const target = getFixture();
        target.style.width = "1080px";

        serverData.menus[1].actionID = 1;
        serverData.actions[1].xml_id = "action_xml_id";

        const webClient = await createEnterpriseWebClient({ serverData, target });
        webClient.el.style.width = "1080px";
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        await nextTick();
        await click(webClient.el.querySelector(".o_app[data-menu-xmlid=menu_1]"));
        await legacyExtraNextTick();
        await nextTick();
        await nextTick();
        assert.containsNone(webClient, ".o_menu_sections .o_menu_sections_more");

        await openStudio(webClient);
        await legacyExtraNextTick();
        await nextTick();
        await nextTick();
        await nextTick();
        assert.containsOnce(webClient, ".o_studio .o_menu_sections");
        assert.containsNone(webClient, ".o_studio .o_menu_sections .o_menu_sections_more");

        Object.assign(serverData.menus, {
            10: { id: 10, children: [], name: "The chain", appID: 1, actionID: 1001, xmlid: "menu_1" },
            11: { id: 11, children: [111], name: "Running in the shadows, damn your love, damn your lies", appID: 1, actionID: 1001, xmlid: "menu_1" },
            12: { id: 12, children: [], name: "You would never break the chain (Never break the chain)", appID: 1, actionID: 1001, xmlid: "menu_1" },
            13: { id: 13, children: [], name: "Chain keep us together (running in the shadow)", appID: 1, actionID: 1001, xmlid: "menu_1" },
            111: { id: 111, children: [], name: "You will never love me again", appID: 1, actionID: 1001, xmlid: "menu_1" },
        });
        serverData.menus[1].children = [10, 11, 12, 13];
        await webClient.env.services.menu.reload();
        // two ticks to allow the navbar to adapt
        await nextTick();
        await nextTick();
        assert.strictEqual(webClient.el.querySelectorAll(".o_studio header .o_menu_sections > *:not(.d-none)").length, 3);
        assert.containsOnce(webClient, ".o_studio .o_menu_sections .o_menu_sections_more");

        await leaveStudio(webClient);
        await legacyExtraNextTick();
        // two more ticks to allow the navbar to adapt
        await nextTick();
        await nextTick();
        assert.containsNone(webClient, ".o_studio");
        assert.strictEqual(webClient.el.querySelectorAll("header .o_menu_sections > *:not(.d-none)").length, 4);
        assert.containsOnce(webClient, ".o_menu_sections .o_menu_sections_more");
    });

    QUnit.test("adapt navbar when refreshing studio (loadState)", async (assert) => {
        assert.expect(7);

        const target = getFixture();
        target.style.width = "1080px";

        const adapted = [];
        patchWithCleanup(StudioNavbar.prototype, {
            async adapt() {
                const prom = this._super();
                adapted.push(prom);
                return prom;
            }
        });

        serverData.menus[1].actionID = 1;
        serverData.actions[1].xml_id = "action_xml_id";
        serverData.actions[1].id = 1;
        serverData.menus[1].children = [10, 11, 12, 13];

        Object.assign(serverData.menus, {
            10: { id: 10, children: [], name: "The chain", appID: 1, actionID: 1001, xmlid: "menu_1" },
            11: { id: 11, children: [111], name: "Running in the shadows, damn your love, damn your lies", appID: 1, actionID: 1001, xmlid: "menu_1" },
            12: { id: 12, children: [], name: "You would never break the chain (Never break the chain)", appID: 1, actionID: 1001, xmlid: "menu_1" },
            13: { id: 13, children: [], name: "Chain keep us together (running in the shadow)", appID: 1, actionID: 1001, xmlid: "menu_1" },
            111: { id: 111, children: [], name: "You will never love me again", appID: 1, actionID: 1001, xmlid: "menu_1" },
        });

        const webClient = await createEnterpriseWebClient({ serverData, target });
        webClient.el.style.width = "1080px";
        window.dispatchEvent(new Event("resize"));
        await Promise.all(adapted);
        await click(webClient.el.querySelector(".o_app[data-menu-xmlid=menu_1]"));
        await legacyExtraNextTick();
        await Promise.all(adapted);
        await nextTick();
        await nextTick();
        assert.containsNone(webClient, ".o_studio");
        assert.strictEqual(webClient.el.querySelectorAll("header .o_menu_sections > *:not(.d-none)").length, 4);
        assert.containsOnce(webClient, ".o_menu_sections .o_menu_sections_more");

        await openStudio(webClient);
        await Promise.all(adapted);
        assert.strictEqual(webClient.el.querySelectorAll(".o_studio header .o_menu_sections > *:not(.d-none)").length, 3);
        assert.containsOnce(webClient, ".o_studio .o_menu_sections .o_menu_sections_more");

        const state = webClient.env.services.router.current.hash;
        console.log(state);
        await loadState(webClient, state);
        await Promise.all(adapted);
        assert.strictEqual(webClient.el.querySelectorAll(".o_studio header .o_menu_sections > *:not(.d-none)").length, 3);
        assert.containsOnce(webClient, ".o_studio .o_menu_sections .o_menu_sections_more");
    });
});
