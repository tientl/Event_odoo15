/** @odoo-module **/
import { click, legacyExtraNextTick } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { BurgerMenu } from "@web_enterprise/webclient/burger_menu/burger_menu";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { companyService } from "@web/webclient/company_service";
import { makeFakeEnterpriseService } from "../mocks";

let serverData;

const serviceRegistry = registry.category("services");

QUnit.module("Burger Menu", {
    beforeEach() {
        serverData = getActionManagerServerData();

        serviceRegistry.add("enterprise", makeFakeEnterpriseService());
        serviceRegistry.add("company", companyService);
        serviceRegistry.add("home_menu", homeMenuService);

        registry.category("systray").add("burgerMenu", {
            Component: BurgerMenu,
            isDisplayed: (env) => env.isSmall,
        });
    },
});

QUnit.test("Burger menu can be opened and closed", async (assert) => {
    assert.expect(2);

    const wc = await createEnterpriseWebClient({ serverData });

    await click(wc.el, ".o_mobile_menu_toggle");
    assert.containsOnce(wc, ".o_burger_menu");

    await click(wc.el, ".o_burger_menu_close");
    assert.containsNone(wc, ".o_burger_menu");
});

QUnit.test("Burger Menu on home menu", async (assert) => {
    assert.expect(7);

    const wc = await createEnterpriseWebClient({ serverData });
    assert.containsNone(wc, ".o_burger_menu");
    assert.isVisible(wc.el.querySelector(".o_home_menu"));

    await click(wc.el, ".o_mobile_menu_toggle");
    assert.containsOnce(wc, ".o_burger_menu");
    assert.containsOnce(wc, ".o_user_menu_mobile");
    assert.containsOnce(wc, ".o_burger_menu_user");
    assert.containsNone(wc, ".o_burger_menu_app");
    await click(wc.el, ".o_burger_menu_close");
    assert.containsNone(wc, ".o_burger_menu");
});

QUnit.test("Burger Menu on an App", async (assert) => {
    assert.expect(8);

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

    const wc = await createEnterpriseWebClient({ serverData });
    await click(wc.el, ".o_app:first-of-type");
    await legacyExtraNextTick();

    assert.containsNone(wc, ".o_burger_menu");
    assert.isNotVisible(wc.el.querySelector(".o_home_menu"));

    await click(wc.el, ".o_mobile_menu_toggle");
    assert.containsOnce(wc, ".o_burger_menu");
    assert.containsOnce(wc, ".o_burger_menu .o_burger_menu_app .o_menu_sections .dropdown-item");
    assert.strictEqual(
        wc.el.querySelector(".o_burger_menu .o_burger_menu_app .o_menu_sections .dropdown-item")
            .textContent,
        "SubMenu"
    );
    assert.hasClass(wc.el.querySelector(".o_burger_menu_content"), "o_burger_menu_dark");

    await click(wc.el, ".o_burger_menu_topbar");
    assert.doesNotHaveClass(wc.el.querySelector(".o_burger_menu_content"), "o_burger_menu_dark");

    await click(wc.el, ".o_burger_menu_topbar");
    assert.hasClass(wc.el.querySelector(".o_burger_menu_content"), "o_burger_menu_dark");
});

QUnit.test("Burger Menu on an App without SubMenu", async (assert) => {
    assert.expect(6);

    const wc = await createEnterpriseWebClient({ serverData });
    await click(wc.el, ".o_app:first-of-type");
    await legacyExtraNextTick();

    assert.containsNone(wc, ".o_burger_menu");

    await click(wc.el, ".o_mobile_menu_toggle");
    assert.containsOnce(wc, ".o_burger_menu");
    assert.containsOnce(wc, ".o_user_menu_mobile");
    assert.containsOnce(wc, ".o_burger_menu_user");
    assert.containsNone(wc, ".o_burger_menu_app");
    await click(wc.el, ".o_burger_menu_close");
    assert.containsNone(wc, ".o_burger_menu");
});

QUnit.test("Burger menu closes when an action is requested", async (assert) => {
    assert.expect(3);

    const wc = await createEnterpriseWebClient({ serverData });

    await click(wc.el, ".o_mobile_menu_toggle");
    assert.containsOnce(wc, ".o_burger_menu");

    await doAction(wc, 1);
    await legacyExtraNextTick();
    assert.containsNone(wc, ".o_burger_menu");
    assert.containsOnce(wc, ".o_kanban_view");
});
