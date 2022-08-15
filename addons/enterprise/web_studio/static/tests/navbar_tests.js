/** @odoo-module **/

import { StudioNavbar } from "@web_studio/client_action/navbar/navbar";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { makeFakeDialogService } from "@web/../tests/helpers/mock_services";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registerStudioDependencies } from "./helpers";

const { mount } = owl;
const serviceRegistry = registry.category("services");

let baseConfig;

QUnit.module("Studio > Navbar", {
    async beforeEach() {
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
    },
});

QUnit.test("menu buttons will not be placed under 'more' menu", async (assert) => {
    assert.expect(12);

    patchWithCleanup(StudioNavbar.prototype, {
        async adapt() {
            await this._super();
            const sectionsCount = this.currentAppSections.length;
            const hiddenSectionsCount = this.currentAppSectionsExtra.length;
            assert.step(`adapt -> hide ${hiddenSectionsCount}/${sectionsCount} sections`);
        },
    });

    const env = await makeTestEnv(baseConfig);
    patchWithCleanup(env.services.studio, {
        get mode() {
            // Will force the the navbar in the studio editor state
            return "editor";
        },
    });

    // Force the parent width, to make this test independent of screen size
    const target = getFixture();
    target.style.width = "1080px";

    // Set menu and mount
    env.services.menu.setCurrentMenu(1);
    const navbar = await mount(StudioNavbar, { env, target });
    registerCleanup(() => navbar.destroy());

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
