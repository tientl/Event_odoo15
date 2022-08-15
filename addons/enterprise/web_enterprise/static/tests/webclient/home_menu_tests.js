/** @odoo-module **/
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import testUtils from "web.test_utils";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { makeFakeEnterpriseService } from "../mocks";
import { uiService } from "@web/core/ui/ui_service";

const { Component, core, hooks, mount, tags } = owl;
const { EventBus } = core;
const patchDate = testUtils.mock.patchDate;
const serviceRegistry = registry.category("services");

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

async function createHomeMenu(homeMenuProps) {
    class Parent extends Component {
        constructor() {
            super();
            this.homeMenuRef = hooks.useRef("home-menu");
            this.homeMenuProps = homeMenuProps;
        }
    }
    Parent.components = { HomeMenu };
    Parent.template = tags.xml`<HomeMenu t-ref="home-menu" t-props="homeMenuProps"/>`;
    const env = await makeTestEnv();
    const target = getFixture();
    const parent = await mount(Parent, { env, target });
    return parent.homeMenuRef.comp;
}

async function walkOn(assert, homeMenu, path) {
    for (const step of path) {
        await testUtils.dom.triggerEvent(window, "keydown", {
            key: step.key,
            shiftKey: step.shiftKey,
        });
        assert.hasClass(
            homeMenu.el.querySelectorAll(".o_menuitem")[step.index],
            "o_focused",
            `step ${step.number}`
        );
    }
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

let homeMenuProps;
let bus;
QUnit.module(
    "web_enterprise",
    {
        beforeEach: function () {
            homeMenuProps = {
                apps: [
                    {
                        actionID: 121,
                        appID: 1,
                        id: 1,
                        label: "Discuss",
                        parents: "",
                        webIcon: false,
                        xmlid: "app.1",
                    },
                    {
                        actionID: 122,
                        appID: 2,
                        id: 2,
                        label: "Calendar",
                        parents: "",
                        webIcon: false,
                        xmlid: "app.2",
                    },
                    {
                        actionID: 123,
                        appID: 3,
                        id: 3,
                        label: "Contacts",
                        parents: "",
                        webIcon: false,
                        xmlid: "app.3",
                    },
                ],
                menuItems: [
                    {
                        actionID: 124,
                        appID: 3,
                        id: 4,
                        label: "Contacts",
                        menuID: 4,
                        parents: "Contacts",
                        xmlid: "menu.4",
                    },
                    {
                        actionID: 125,
                        appID: 3,
                        id: 5,
                        label: "Configuration",
                        menuID: 5,
                        parents: "Contacts",
                        xmlid: "menu.5",
                    },
                    {
                        actionID: 126,
                        appID: 3,
                        id: 6,
                        label: "Contact Tags",
                        menuID: 6,
                        parents: "Contacts / Configuration",
                        xmlid: "menu.6",
                    },
                    {
                        actionID: 127,
                        appID: 3,
                        id: 7,
                        label: "Contact Titles",
                        menuID: 7,
                        parents: "Contacts / Configuration",
                        xmlid: "menu.7",
                    },
                    {
                        actionID: 128,
                        appID: 3,
                        id: 8,
                        label: "Localization",
                        menuID: 8,
                        parents: "Contacts / Configuration",
                        xmlid: "menu.8",
                    },
                    {
                        actionID: 129,
                        appID: 3,
                        id: 9,
                        label: "Countries",
                        menuID: 9,
                        parents: "Contacts / Configuration / Localization",
                        xmlid: "menu.9",
                    },
                    {
                        actionID: 130,
                        appID: 3,
                        id: 10,
                        label: "Fed. States",
                        menuID: 10,
                        parents: "Contacts / Configuration / Localization",
                        xmlid: "menu.10",
                    },
                ],
            };

            const fakeEnterpriseService = makeFakeEnterpriseService();
            bus = new EventBus();
            const fakeHomeMenuService = {
                name: "home_menu",
                start() {
                    return {
                        toggle(show) {
                            bus.trigger("toggle", show);
                        },
                    };
                },
            };
            const fakeMenuService = {
                name: "menu",
                start() {
                    return {
                        selectMenu(menu) {
                            bus.trigger("selectMenu", menu.id);
                        },
                        getMenu() {
                            return {};
                        },
                    };
                },
            };
            serviceRegistry.add("ui", uiService);
            serviceRegistry.add(fakeEnterpriseService.name, fakeEnterpriseService);
            serviceRegistry.add(fakeHomeMenuService.name, fakeHomeMenuService);
            serviceRegistry.add(fakeMenuService.name, fakeMenuService);
        },
    },
    function () {
        QUnit.module("HomeMenu");

        QUnit.test("ESC Support", async function (assert) {
            assert.expect(9);

            bus.on("toggle", null, (show) => {
                assert.step(`toggle ${show}`);
            });
            const homeMenu = await createHomeMenu(homeMenuProps);

            assert.hasClass(homeMenu.el, "o_search_hidden", "search bar must be hidden by default");

            const searchInput = homeMenu.el.querySelector(".o_menu_search_input");
            await testUtils.fields.editInput(searchInput, "dis");

            assert.containsOnce(homeMenu.el, ".o_menuitem.o_focused");
            assert.doesNotHaveClass(
                homeMenu.el,
                "o_search_hidden",
                "search must be visible after some input"
            );

            assert.strictEqual(
                searchInput.value,
                "dis",
                "search bar input must contain the input text"
            );

            await testUtils.dom.triggerEvent(window, "keydown", { key: "Escape" });
            assert.containsOnce(homeMenu.el, ".o_menuitem.o_focused");

            assert.strictEqual(searchInput.value, "", "search must have no text after ESC");

            assert.doesNotHaveClass(
                homeMenu.el,
                "o_search_hidden",
                "search must still become visible after clearing some non-empty text"
            );

            await testUtils.dom.triggerEvent(window, "keydown", { key: "Escape" });

            assert.verifySteps(["toggle false"]);

            homeMenu.destroy();
        });

        QUnit.test("Navigation and search in the home menu", async function (assert) {
            assert.expect(8);

            bus.on("selectMenu", null, (menuId) => {
                assert.step(`selectMenu ${menuId}`);
            });
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            await testUtils.dom.triggerEvent(input, "focus");
            await testUtils.fields.editInput(input, "a");

            assert.hasClass(homeMenu.el.querySelectorAll(".o_menuitem")[0], "o_focused");

            assert.doesNotHaveClass(
                homeMenu.el,
                "o_search_hidden",
                "search must be visible after some input"
            );

            assert.strictEqual(input.value, "a", "search bar input must contain the input text");

            const path = [
                { number: 1, key: "ArrowRight", index: 1 },
                { number: 2, key: "Tab", index: 2 },
                { number: 3, key: "ArrowUp", index: 0 },
            ];

            await walkOn(assert, homeMenu, path);

            // open first app (Calendar)
            await testUtils.dom.triggerEvent(window, "keydown", { key: "Enter" });

            assert.verifySteps(["selectMenu 2"]);

            homeMenu.destroy();
        });

        QUnit.test("Click on an app", async function (assert) {
            assert.expect(2);

            bus.on("selectMenu", null, (menuId) => {
                assert.step(`selectMenu ${menuId}`);
            });
            const homeMenu = await createHomeMenu(homeMenuProps);

            await testUtils.dom.click(homeMenu.el.querySelectorAll(".o_menuitem")[0]);
            assert.verifySteps(["selectMenu 1"]);

            homeMenu.destroy();
        });

        QUnit.test("Click on a menu item", async function (assert) {
            assert.expect(2);

            bus.on("selectMenu", null, (menuId) => {
                assert.step(`selectMenu ${menuId}`);
            });
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();

            await testUtils.fields.editInput(input, "a");

            await testUtils.dom.click(homeMenu.el.querySelectorAll(".o_menuitem")[2]);
            assert.verifySteps(["selectMenu 8"]);

            homeMenu.destroy();
        });

        QUnit.test("search displays matches in parents", async function (assert) {
            assert.expect(4);

            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();

            assert.containsN(homeMenu, '.o_menuitem.o_app', 3);
            assert.containsN(homeMenu.el, ".o_menuitem", 3);

            await testUtils.fields.editInput(input, "Conf");

            assert.containsN(homeMenu, '.o_menuitem.o_app', 0);
            assert.containsN(homeMenu.el, ".o_menuitem", 6);

            homeMenu.destroy();
        });

        QUnit.test("navigate to a non app item and open it", async function (assert) {
            assert.expect(5);

            bus.on("selectMenu", null, (menuId) => {
                assert.step(`selectMenu ${menuId}`);
            });
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();

            assert.containsN(homeMenu.el, ".o_menuitem", 3);

            await testUtils.fields.editInput(input, "Cont");

            assert.containsN(homeMenu.el, ".o_menuitem", 8);

            // go down
            await testUtils.dom.triggerEvent(window, "keydown", { key: "ArrowDown" });

            assert.hasClass(homeMenu.el.querySelectorAll(".o_menuitem")[1], "o_focused");

            // press ENTER
            await testUtils.dom.triggerEvent(window, "keydown", { key: "Enter" });

            assert.verifySteps(["selectMenu 4"]);

            homeMenu.destroy();
        });

        QUnit.test("Display Expiration Panel (no module installed)", async function (assert) {
            assert.expect(3);

            const unpatchDate = patchDate(2019, 9, 10, 0, 0, 0);

            const mockedEnterpriseService = {
                name: "enterprise",
                start() {
                    return {
                        expirationDate: "2019-11-01 12:00:00",
                        expirationReason: "",
                        isMailInstalled: false,
                        warning: "admin",
                    };
                },
            };
            let cookie = false;
            const mockedCookieService = {
                name: "cookie",
                start() {
                    return {
                        get current() {
                            return cookie;
                        },
                        setCookie() {
                            cookie = true;
                        },
                    };
                },
            };

            serviceRegistry.add(mockedEnterpriseService.name, mockedEnterpriseService, {
                force: true,
            });
            serviceRegistry.add(mockedCookieService.name, mockedCookieService);
            serviceRegistry.add("orm", ormService);

            const homeMenu = await createHomeMenu(homeMenuProps);

            assert.containsOnce(homeMenu.el, ".database_expiration_panel");
            assert.strictEqual(
                homeMenu.el.querySelector(".database_expiration_panel .oe_instance_register")
                    .innerText,
                "You will be able to register your database once you have installed your first app.",
                "There should be an expiration panel displayed"
            );

            // Close the expiration panel
            await testUtils.dom.click(
                homeMenu.el.querySelector(".database_expiration_panel .oe_instance_hide_panel")
            );
            assert.containsNone(homeMenu.el, ".database_expiration_panel");

            homeMenu.destroy();
            unpatchDate();
        });

        QUnit.test("Navigation (only apps, only one line)", async function (assert) {
            assert.expect(8);

            homeMenuProps = {
                apps: new Array(3).fill().map((x, i) => {
                    return {
                        actionID: 120 + i,
                        appID: i + 1,
                        id: i + 1,
                        label: `0${i}`,
                        parents: "",
                        webIcon: false,
                        xmlid: `app.${i}`,
                    };
                }),
                menuItems: [],
            };
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();
            await testUtils.nextTick();
            // we make possible full navigation (i.e. also TAB management)
            await testUtils.fields.editInput(input, "0");

            // begin with focus on first app
            assert.hasClass(homeMenu.el.querySelectorAll(".o_menuitem")[0], "o_focused");

            const path = [
                { number: 1, key: "ArrowRight", index: 1 },
                { number: 2, key: "Tab", index: 2 },
                { number: 3, key: "ArrowRight", index: 0 },
                { number: 4, key: "Tab", shiftKey: true, index: 2 },
                { number: 5, key: 'ArrowLeft', index: 1 },
                { number: 6, key: 'ArrowDown', index: 1 },
                { number: 7, key: 'ArrowUp', index: 1 },
            ];

            await walkOn(assert, homeMenu, path);

            homeMenu.destroy();
        });

        QUnit.test("Navigation (only apps, two lines, one incomplete)", async function (assert) {
            assert.expect(19);

            homeMenuProps = {
                apps: new Array(8).fill().map((x, i) => {
                    return {
                        actionID: 121,
                        appID: i + 1,
                        id: i + 1,
                        label: `0${i}`,
                        parents: "",
                        webIcon: false,
                        xmlid: `app.${i}`,
                    };
                }),
                menuItems: [],
            };
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();
            await testUtils.nextTick();
            // allow navigation (without TAB management)
            await testUtils.fields.editInput(input, "");

            // begin with focus on first app
            assert.hasClass(homeMenu.el.querySelectorAll(".o_menuitem")[0], "o_focused");

            const path = [
                { number: 1, key: "ArrowUp", index: 6 },
                { number: 2, key: "ArrowUp", index: 0 },
                { number: 3, key: "ArrowDown", index: 6 },
                { number: 4, key: "ArrowDown", index: 0 },
                { number: 5, key: "ArrowRight", index: 1 },
                { number: 6, key: "ArrowRight", index: 2 },
                { number: 7, key: "ArrowUp", index: 7 },
                { number: 8, key: "ArrowUp", index: 1 },
                { number: 9, key: "ArrowRight", index: 2 },
                { number: 10, key: "ArrowDown", index: 7 },
                { number: 11, key: "ArrowDown", index: 1 },
                { number: 12, key: "ArrowUp", index: 7 },
                { number: 13, key: "ArrowRight", index: 6 },
                { number: 14, key: "ArrowLeft", index: 7 },
                { number: 15, key: "ArrowUp", index: 1 },
                { number: 16, key: "ArrowLeft", index: 0 },
                { number: 17, key: "ArrowLeft", index: 5 },
                { number: 18, key: "ArrowRight", index: 0 },
            ];

            await walkOn(assert, homeMenu, path);

            homeMenu.destroy();
        });

        QUnit.test(
            "Navigation (only apps, two lines, one incomplete, no searchbar)",
            async function (assert) {
                assert.expect(19);

                homeMenuProps = {
                    apps: new Array(8).fill().map((x, i) => {
                        return {
                            actionID: 121,
                            appID: i + 1,
                            id: i + 1,
                            label: `0${i}`,
                            parents: "",
                            webIcon: false,
                            xmlid: `app.${i}`,
                        };
                    }),
                    menuItems: [],
                };
                const homeMenu = await createHomeMenu(homeMenuProps);

                async function walkOnButCheckFocus(path) {
                    for (let i = 0; i < path.length; i++) {
                        const step = path[i];
                        await testUtils.dom.triggerEvent(window, "keydown", {
                            key: step.key,
                            shiftKey: step.shiftKey,
                        });
                        assert.ok(
                            homeMenu.el.querySelectorAll(".o_menuitem")[step.index] ===
                                document.activeElement,
                            `step ${i + 1}`
                        );
                    }
                }

                const path = [
                    { number: 1, key: "ArrowRight", index: 0 },
                    { number: 2, key: "ArrowUp", index: 6 },
                    { number: 3, key: "ArrowUp", index: 0 },
                    { number: 4, key: "ArrowDown", index: 6 },
                    { number: 5, key: "ArrowDown", index: 0 },
                    { number: 6, key: "ArrowRight", index: 1 },
                    { number: 7, key: "ArrowRight", index: 2 },
                    { number: 8, key: "ArrowUp", index: 7 },
                    { number: 9, key: "ArrowUp", index: 1 },
                    { number: 10, key: "ArrowRight", index: 2 },
                    { number: 11, key: "ArrowDown", index: 7 },
                    { number: 12, key: "ArrowDown", index: 1 },
                    { number: 13, key: "ArrowUp", index: 7 },
                    { number: 14, key: "ArrowRight", index: 6 },
                    { number: 15, key: "ArrowLeft", index: 7 },
                    { number: 16, key: "ArrowUp", index: 1 },
                    { number: 17, key: "ArrowLeft", index: 0 },
                    { number: 18, key: "ArrowLeft", index: 5 },
                    { number: 19, key: "ArrowRight", index: 0 },
                ];

                await walkOnButCheckFocus(path);

                homeMenu.destroy();
            }
        );

        QUnit.test("Navigation (only 3 menuItems)", async function (assert) {
            assert.expect(9);

            homeMenuProps = {
                apps: [],
                menuItems: new Array(3).fill().map((x, i) => {
                    return {
                        actionID: 120 + i,
                        appID: 0,
                        id: i + 1,
                        menuID: i + 1,
                        label: `0${i}`,
                        parents: "0",
                        xmlid: `menu_${i}`,
                    };
                }),
            };
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();
            await testUtils.nextTick();
            // allow navigation (without TAB management)
            await testUtils.fields.editInput(input, "0");

            // begin with focus on first app
            assert.hasClass(homeMenu.el.querySelectorAll(".o_menuitem")[0], "o_focused");

            const path = [
                { number: 1, key: "ArrowUp", index: 2 },
                { number: 2, key: "ArrowUp", index: 1 },
                { number: 3, key: "ArrowUp", index: 0 },
                { number: 4, key: "ArrowDown", index: 1 },
                { number: 5, key: "ArrowDown", index: 2 },
                { number: 6, key: "ArrowDown", index: 0 },
                { number: 7, key: "ArrowRight", index: 0 },
                { number: 8, key: "ArrowLeft", index: 0 },
            ];

            await walkOn(assert, homeMenu, path);

            homeMenu.destroy();
        });

        QUnit.test("Navigation (one line of 3 apps and 2 menuItems)", async function (assert) {
            assert.expect(12);

            homeMenuProps = {
                apps: new Array(3).fill().map((x, i) => {
                    return {
                        actionID: 120 + i,
                        appID: i + 1,
                        id: i + 1,
                        label: `0${i}`,
                        parents: "",
                        webIcon: false,
                        xmlid: `app.${i}`,
                    };
                }),
                menuItems: new Array(2).fill().map((x, i) => {
                    return {
                        actionID: 120 + i,
                        appID: 1,
                        id: i + 3,
                        label: `0${i}`,
                        menuID: i,
                        parents: "",
                        xmlid: `menu_${i}`,
                    };
                }),
            };
            const homeMenu = await createHomeMenu(homeMenuProps);

            const input = homeMenu.el.querySelector(".o_menu_search_input");
            input.focus();
            await testUtils.nextTick();
            // allow navigation (without TAB management)
            await testUtils.fields.editInput(input, "0");

            // begin with focus on first app
            assert.hasClass(homeMenu.el.querySelectorAll(".o_menuitem")[0], "o_focused");

            const path = [
                { number: 1, key: "ArrowRight", index: 1 },
                { number: 2, key: "ArrowRight", index: 2 },
                { number: 3, key: "ArrowRight", index: 0 },
                { number: 4, key: "ArrowDown", index: 3 },
                { number: 5, key: "ArrowDown", index: 4 },
                { number: 6, key: "ArrowDown", index: 0 },
                { number: 7, key: "ArrowRight", index: 1 },
                { number: 8, key: "ArrowUp", index: 4 },
                { number: 9, key: "ArrowUp", index: 3 },
                { number: 10, key: "ArrowUp", index: 0 },
                { number: 11, key: 'ArrowLeft', index: 2 },
            ];

            await walkOn(assert, homeMenu, path);

            homeMenu.destroy();
        });

        QUnit.test("Scroll bar padding", async function (assert) {
            assert.expect(3);

            const target = getFixture();
            target.style.height = "300px";

            const homeMenu = await createHomeMenu(homeMenuProps);

            const scrollable = document.querySelector(".o_home_menu_scrollable");
            const input = document.querySelector(".o_menu_search_input");

            function getPaddingLeft() {
                return Number(scrollable.style.paddingLeft.split("px")[0]);
            }

            assert.strictEqual(getPaddingLeft(), 0);

            await testUtils.dom.triggerEvent(input, "focus");
            await testUtils.fields.editInput(input, "a");

            assert.ok(getPaddingLeft() > 0); // Browser dependant

            await testUtils.dom.triggerEvent(window, "keydown", { key: "Escape" });

            assert.strictEqual(getPaddingLeft(), 0);

            homeMenu.destroy();
        });

        QUnit.test("The HomeMenu input always takes the focus when you press a key", async function (assert) {
            const homeMenu = await createHomeMenu(homeMenuProps);

            homeMenu.env.services.ui.activateElement("");
            await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
            await nextTick();
            const input = homeMenu.el.querySelector(".o_menu_search_input");
            assert.strictEqual(document.activeElement, input);
        });

        QUnit.test('focus stay on search input (to avoid IME disabling issue) [REQUIRE FOCUS]', async function (assert) {
            assert.expect(12);
            const homeMenu = await createHomeMenu(homeMenuProps);

            // auto-focus when attached
            assert.strictEqual(document.activeElement, homeMenu.inputRef.el);

            // refocus after focus on non-interactive element
            homeMenu.inputRef.el.blur();
            assert.strictEqual(document.activeElement, document.body);
            await testUtils.nextTick();
            assert.strictEqual(document.activeElement, homeMenu.inputRef.el);

            // searching select first matching app without losing focus
            assert.containsNone(homeMenu, '.o_focused');
            await testUtils.fields.editInput(homeMenu.inputRef.el, 'a');
            assert.strictEqual(document.activeElement, homeMenu.inputRef.el);
            assert.containsOnce(homeMenu, '.o_app.o_focused[data-menu-xmlid="app.2"]');

            // switching between selected app do not lose focus
            await testUtils.fields.triggerKeydown(homeMenu.el, 'TAB');
            assert.containsOnce(homeMenu, '.o_app.o_focused[data-menu-xmlid="app.3"]');
            assert.strictEqual(document.activeElement, homeMenu.inputRef.el);
            await testUtils.fields.triggerKeydown(homeMenu.el, 'left');
            assert.containsOnce(homeMenu, '.o_app.o_focused[data-menu-xmlid="app.2"]');
            assert.strictEqual(document.activeElement, homeMenu.inputRef.el);

            // clearing input with ESCAPE key should not lose focus
            await testUtils.fields.triggerKeydown(homeMenu.el, 'ESCAPE');
            assert.strictEqual(document.activeElement, homeMenu.inputRef.el);

            // focusing on interactive element lose focus: this is still an issue
            // but we can't steal focus from elements such as top-left user menu
            homeMenu.el.querySelector('.o_app').focus()
            await testUtils.nextTick();
            assert.notEqual(document.activeElement, homeMenu.inputRef.el);

            homeMenu.destroy();
        });

    }
);
