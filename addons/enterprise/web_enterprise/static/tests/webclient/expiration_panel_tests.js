/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { ormService } from "@web/core/orm_service";
import { patch, unpatch } from "@web/core/utils/patch";
import testUtils from "web.test_utils";
import { ExpirationPanel } from "@web_enterprise/webclient/home_menu/expiration_panel";
import { makeFakeEnterpriseService } from "../mocks";
import { unblockUI } from "web.framework";

const { mount } = owl;
const patchDate = testUtils.mock.patchDate;
const serviceRegistry = registry.category("services");

async function createExpirationPanel(params = {}) {
    const mockedCookieService = {
        name: "cookie",
        start() {
            return Object.assign(
                {
                    current: "",
                    setCookie() {},
                    deleteCookie() {},
                },
                params.cookie
            );
        },
    };

    serviceRegistry.add(mockedCookieService.name, mockedCookieService);
    serviceRegistry.add("orm", ormService);
    const mockedEnterpriseService = makeFakeEnterpriseService(params.enterprise);
    serviceRegistry.add(mockedEnterpriseService.name, mockedEnterpriseService);
    patch(browser, "mocked_browser", Object.assign({ location: "" }, params.browser));
    registerCleanup(() => unpatch(browser, "mocked_browser"));

    const env = await makeTestEnv({
        mockRPC: params.mockRPC,
    });

    patchWithCleanup($.blockUI.defaults, {
        fadeIn: 0,
        fadeOut: 0,
    });

    const target = getFixture();
    return mount(ExpirationPanel, { env, target });
}

QUnit.module("web_enterprise", {}, function () {
    QUnit.module("Expiration Panel");

    QUnit.test("Expiration Panel one app installed", async function (assert) {
        assert.expect(3);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-11-09 12:00:00",
                expirationReason: "",
                isMailInstalled: true,
                warning: "admin",
            },
        });

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This database will expire in 1 month."
        );

        // Color should be grey
        assert.hasClass(panel.el, "alert-info");

        // Close the expiration panel
        await testUtils.dom.click(panel.el.querySelector(".oe_instance_hide_panel"));

        assert.strictEqual(panel.el.innerHTML, "");

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("Expiration Panel one app installed, buy subscription", async function (assert) {
        assert.expect(6);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-24 12:00:00",
                expirationReason: "demo",
                isMailInstalled: true,
                warning: "admin",
            },
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/res.users/search_count") {
                    return 7;
                }
            },
        });

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This demo database will expire in 14 days. Register your subscription or buy a subscription."
        );

        assert.hasClass(panel.el, "alert-warning", "Color should be orange");
        assert.containsOnce(
            panel.el,
            ".oe_instance_register_show",
            "Part 'Register your subscription'"
        );
        assert.containsOnce(panel.el, ".oe_instance_buy", "Part 'buy a subscription'");
        assert.containsNone(
            panel.el,
            ".oe_instance_register_form",
            "There should be no registration form"
        );

        // Click on 'buy subscription'
        await testUtils.dom.click(panel.el.querySelector(".oe_instance_buy"));

        assert.strictEqual(
            browser.location,
            "https://www.odoo.com/odoo-enterprise/upgrade?num_users=7"
        );

        panel.destroy();
        unpatchDate();
    });

    QUnit.test(
        "Expiration Panel one app installed, try several times to register subscription",
        async function (assert) {
            assert.expect(47);

            const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

            let callToGetParamCount = 0;

            const panel = await createExpirationPanel({
                enterprise: {
                    expirationDate: "2019-10-15 12:00:00",
                    expirationReason: "trial",
                    isMailInstalled: true,
                    warning: "admin",
                },
                cookie: {
                    setCookie() {
                        assert.step("setCookie");
                    },
                },
                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/ir.config_parameter/get_param") {
                        assert.step("get_param");
                        if (args.args[0] === "database.already_linked_subscription_url") {
                            return false;
                        }
                        if (args.args[0] === "database.already_linked_email") {
                            return "super_company_admin@gmail.com";
                        }
                        assert.strictEqual(args.args[0], "database.expiration_date");
                        callToGetParamCount++;
                        if (callToGetParamCount <= 3) {
                            return "2019-10-15 12:00:00";
                        } else {
                            return "2019-11-15 12:00:00";
                        }
                    }
                    if (route === "/web/dataset/call_kw/ir.config_parameter/set_param") {
                        assert.step("set_param");
                        assert.strictEqual(args.args[0], "database.enterprise_code");
                        if (callToGetParamCount === 1) {
                            assert.strictEqual(args.args[1], "ABCDEF");
                        } else {
                            assert.strictEqual(args.args[1], "ABC");
                        }
                        return true;
                    }
                    if (
                        route ===
                        "/web/dataset/call_kw/publisher_warranty.contract/update_notification"
                    ) {
                        assert.step("update_notification");
                        assert.ok(args.args[0] instanceof Array && args.args[0].length === 0);
                        return true;
                    }
                },
            });

            assert.strictEqual(
                panel.el.querySelector(".oe_instance_register").innerText,
                "This database will expire in 5 days. Register your subscription or buy a subscription."
            );

            assert.hasClass(panel.el, "alert-danger", "Color should be red");

            assert.containsOnce(
                panel.el,
                ".oe_instance_register_show",
                "Part 'Register your subscription'"
            );
            assert.containsOnce(panel.el, ".oe_instance_buy", "Part 'buy a subscription'");
            assert.containsNone(
                panel.el,
                ".oe_instance_register_form",
                "There should be no registration form"
            );

            // Click on 'register your subscription'
            await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_show"));

            assert.containsOnce(
                panel.el,
                ".oe_instance_register_form",
                "there should be a registration form"
            );
            assert.containsOnce(
                panel.el,
                '.oe_instance_register_form input[placeholder="Paste code here"]',
                "with an input with place holder 'Paste code here'"
            );
            assert.containsOnce(
                panel.el,
                ".oe_instance_register_form button",
                "and a button 'REGISTER'"
            );
            assert.strictEqual(
                panel.el.querySelector(".oe_instance_register_form button").innerText,
                "REGISTER"
            );

            await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_form button"));

            assert.containsOnce(
                panel.el,
                ".oe_instance_register_form",
                "there should be a registration form"
            );
            assert.containsOnce(
                panel.el,
                '.oe_instance_register_form input[placeholder="Your subscription code"]',
                "with an input with place holder 'Paste code here'"
            );
            assert.containsOnce(
                panel.el,
                ".oe_instance_register_form button",
                "and a button 'REGISTER'"
            );

            await testUtils.fields.editInput(
                panel.el.querySelector(".oe_instance_register_form input"),
                "ABCDEF"
            );
            await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_form button"));

            assert.strictEqual(
                panel.el.querySelector(".oe_instance_register").innerText,
                "Something went wrong while registering your database. You can try again or contact Odoo Support."
            );
            assert.hasClass(panel.el, "alert-danger", "Color should be red");
            assert.containsOnce(panel.el, "span.oe_instance_error");
            assert.containsOnce(
                panel.el,
                ".oe_instance_register_form",
                "there should be a registration form"
            );
            assert.containsOnce(
                panel.el,
                '.oe_instance_register_form input[placeholder="Your subscription code"]',
                "with an input with place holder 'Paste code here'"
            );
            assert.containsOnce(
                panel.el,
                ".oe_instance_register_form button",
                "and a button 'REGISTER'"
            );
            assert.strictEqual(
                panel.el.querySelector(".oe_instance_register_form button").innerText,
                "RETRY"
            );

            await testUtils.fields.editInput(
                panel.el.querySelector(".oe_instance_register_form input"),
                "ABC"
            );
            await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_form button"));

            assert.strictEqual(
                panel.el.querySelector(".oe_instance_register.oe_instance_success").innerText,
                "Thank you, your registration was successful! Your database is valid until November 15, 2019."
            );
            assert.hasClass(panel.el, "alert-success", "Color should be green");
            assert.containsNone(panel.el, ".oe_instance_register_form button");

            assert.verifySteps([
                // second try to submit
                "get_param",
                "set_param",
                "get_param",
                "get_param",
                "setCookie",
                "update_notification",
                "get_param",
                // third try
                "get_param",
                "set_param",
                "get_param",
                "get_param",
                "setCookie",
                "update_notification",
                "get_param",
            ]);

            panel.destroy();
            unpatchDate();
        }
    );

    QUnit.test(
        "Expiration Panel one app installed, subscription already linked",
        async function (assert) {
            assert.expect(13);

            const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);
            // There are some line breaks mismatches between local and runbot test instances.
            // Since they don't affect the layout and we're only interested in the text itself,
            // we normalize whitespaces and line breaks from both the expected and end result
            const formatWhiteSpaces = (text) =>
                text
                    .split(/[\n\s]/)
                    .filter((w) => w !== "")
                    .join(" ");

            let getExpirationDateCount = 0;

            const panel = await createExpirationPanel({
                enterprise: {
                    expirationDate: "2019-10-15 12:00:00",
                    expirationReason: "trial",
                    isMailInstalled: true,
                    warning: "admin",
                },
                cookie: {
                    setCookie() {
                        assert.step("setCookie");
                    },
                },
                mockRPC(route, args) {
                    if (route === "/already/linked/send/mail/url") {
                        return {
                            result: false,
                            reason: "By design",
                        };
                    }
                    assert.step(args.method);
                    if (args.args[0] === "database.expiration_date") {
                        getExpirationDateCount++;
                        if (getExpirationDateCount === 1) {
                            return "2019-10-15 12:00:00";
                        } else {
                            return "2019-11-17 12:00:00";
                        }
                    }
                    if (args.args[0] === "database.already_linked_subscription_url") {
                        return "www.super_company.com";
                    }
                    if (args.args[0] === "database.already_linked_send_mail_url") {
                        return "/already/linked/send/mail/url";
                    }
                    if (args.args[0] === "database.already_linked_email") {
                        return "super_company_admin@gmail.com";
                    }
                    return true;
                },
            });

            assert.strictEqual(
                panel.el.querySelector(".oe_instance_register").innerText,
                "This database will expire in 5 days. Register your subscription or buy a subscription."
            );

            // Click on 'register your subscription'
            await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_show"));
            await testUtils.fields.editInput(
                panel.el.querySelector(".oe_instance_register_form input"),
                "ABC"
            );
            await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_form button"));

            assert.strictEqual(
                formatWhiteSpaces(
                    panel.el.querySelector(".oe_instance_register.oe_database_already_linked")
                        .innerText
                ),
                formatWhiteSpaces(
                    `Your subscription is already linked to a database.
                To unlink it you can either:
                - Login to your Odoo.com dashboard then unlink your previous database: www.super_company.com
                - Click here to send an email to the subscription owner (email: super_company_admin@gmail.com) with the instructions to follow`
                )
            );

            await testUtils.dom.click(panel.el.querySelector("a.oe_contract_send_mail"));

            assert.hasClass(panel.el, "alert-danger", "Color should be red");

            assert.strictEqual(
                formatWhiteSpaces(
                    panel.el.querySelector(".oe_instance_register.oe_database_already_linked")
                        .innerText
                ),
                formatWhiteSpaces(
                    `Your subscription is already linked to a database.
                To unlink it you can either:
                - Login to your Odoo.com dashboard then unlink your previous database: www.super_company.com
                - Click here to send an email to the subscription owner (email: super_company_admin@gmail.com) with the instructions to follow
                Unable to send the instructions by email, please contact the Odoo Support
                Error reason: By design`
                )
            );

            assert.verifySteps([
                "get_param",
                "set_param",
                "get_param",
                "get_param",
                "setCookie",
                "update_notification",
                "get_param",
                "get_param",
            ]);

            panel.destroy();
            unpatchDate();
        }
    );

    QUnit.test("One app installed, database expired", async function (assert) {
        assert.expect(13);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        let callToGetParamCount = 0;

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-08 12:00:00",
                expirationReason: "trial",
                isMailInstalled: true,
                warning: "admin",
            },
            cookie: {
                setCookie() {
                    assert.step("setCookie");
                    assert.strictEqual(arguments[0], "oe_instance_hide_panel");
                    assert.strictEqual(arguments[1], "");
                    assert.strictEqual(arguments[2], -1);
                },
            },
            mockRPC(route, args) {
                if (args.method === "get_param") {
                    if (args.args[0] === "database.already_linked_subscription_url") {
                        return false;
                    }
                    callToGetParamCount++;
                    if (callToGetParamCount === 1) {
                        return "2019-10-09 12:00:00";
                    } else {
                        return "2019-11-09 12:00:00";
                    }
                }
                return true;
            },
        });

        assert.hasClass(document.body, "o_ui_blocked", "UI should be blocked");
        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This database has expired. Register your subscription or buy a subscription."
        );

        assert.hasClass(panel.el, "alert-danger", "Color should be red");
        assert.containsOnce(
            panel.el,
            ".oe_instance_register_show",
            "Part 'Register your subscription'"
        );
        assert.containsOnce(panel.el, ".oe_instance_buy", "Part 'buy a subscription'");

        assert.containsNone(panel.el, ".oe_instance_register_form");

        // Click on 'Register your subscription'
        await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_show"));
        await testUtils.fields.editInput(
            panel.el.querySelector(".oe_instance_register_form input"),
            "ABC"
        );
        await testUtils.dom.click(panel.el.querySelector(".oe_instance_register_form button"));

        assert.doesNotHaveClass(document.body, "o_ui_blocked", "UI should be no longer be blocked");
        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "Thank you, your registration was successful! Your database is valid until November 9, 2019."
        );

        assert.verifySteps(["setCookie"]);

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, renew with success", async function (assert) {
        assert.expect(14);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        let callToGetParamCount = 0;

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-20 12:00:00",
                expirationReason: "renewal",
                isMailInstalled: true,
                warning: "admin",
            },
            cookie: {
                setCookie() {
                    assert.step("setCookie");
                },
            },
            mockRPC(route, args) {
                if (args.method === "get_param") {
                    assert.step("get_param");
                    callToGetParamCount++;
                    if (callToGetParamCount === 1) {
                        return "2019-10-20 12:00:00";
                    } else if (callToGetParamCount === 2) {
                        assert.strictEqual(args.args[0], "database.expiration_date");
                        return "2019-11-09 12:00:00";
                    } else {
                        assert.strictEqual(args.args[0], "database.enterprise_code");
                        return "ABC";
                    }
                }
                if (args.method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This database will expire in 10 days. Renew your subscription"
        );

        assert.hasClass(panel.el, "alert-warning", "Color should be red");
        assert.containsOnce(panel.el, ".oe_instance_renew", "Part 'Register your subscription'");
        assert.containsOnce(
            panel.el,
            "a.check_enterprise_status",
            "there should be a button for status checking"
        );

        assert.containsNone(panel.el, ".oe_instance_register_form");

        // Click on 'Renew your subscription'
        await testUtils.dom.click(panel.el.querySelector(".oe_instance_renew"));

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register.oe_instance_success").innerText,
            "Thank you, your registration was successful! Your database is valid until November 9, 2019."
        );

        assert.verifySteps([
            "get_param",
            "setCookie",
            "update_notification",
            "get_param",
            "get_param",
        ]);

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, check status and get success", async function (assert) {
        assert.expect(8);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        let callToGetParamCount = 0;

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-20 12:00:00",
                expirationReason: "renewal",
                isMailInstalled: true,
                warning: "admin",
            },
            mockRPC(route, args) {
                if (args.method === "get_param") {
                    assert.step("get_param");
                    assert.strictEqual(args.args[0], "database.expiration_date");
                    callToGetParamCount++;
                    if (callToGetParamCount === 1) {
                        return "2019-10-20 12:00:00";
                    } else {
                        return "2019-10-24 12:00:00";
                    }
                }
                if (args.method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        // click on "Refresh subscription status"
        const refreshButton = panel.el.querySelector("a.check_enterprise_status");
        assert.strictEqual(refreshButton.getAttribute("aria-label"), "Refresh subscription status");
        await testUtils.dom.click(refreshButton);

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register.oe_subscription_updated").innerText,
            "Your subscription was updated and is valid until October 24, 2019."
        );

        assert.verifySteps(["get_param", "update_notification", "get_param"]);

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, check status and get page reload", async function (assert) {
        assert.expect(5);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-20 12:00:00",
                expirationReason: "renewal",
                isMailInstalled: true,
                warning: "admin",
            },
            browser: {
                location: {
                    reload: () => assert.step("reloadPage"),
                },
            },
            mockRPC(route, args) {
                if (args.method === "get_param") {
                    assert.step("get_param");
                    return "2019-10-20 12:00:00";
                }
                if (args.method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        // click on "Refresh subscription status"
        await testUtils.dom.click(panel.el.querySelector("a.check_enterprise_status"));

        assert.verifySteps(["get_param", "update_notification", "get_param", "reloadPage"]);

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, upgrade database", async function (assert) {
        assert.expect(6);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-20 12:00:00",
                expirationReason: "upsell",
                isMailInstalled: true,
                warning: "admin",
            },
            browser: {
                location: {
                    reload: () => assert.step("reloadPage"),
                },
            },
            mockRPC(route, args) {
                if (args.method === "get_param") {
                    assert.step("get_param");
                    assert.strictEqual(args.args[0], "database.enterprise_code");
                    return "ABC";
                }
                if (args.method === "search_count") {
                    assert.step("search_count");
                    return 13;
                }
                return true;
            },
        });

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This database will expire in 10 days. You have more users or more apps installed than your subscription allows.\n" +
                "Upgrade your subscription"
        );

        // click on "Upgrade your subscription"
        await testUtils.dom.click(panel.el.querySelector("a.oe_instance_upsell"));

        assert.verifySteps(["get_param", "search_count"]);
        assert.strictEqual(
            browser.location,
            "https://www.odoo.com/odoo-enterprise/upsell?num_users=13&contract=ABC"
        );

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, message for non admin user", async function (assert) {
        assert.expect(2);

        const unpatchDate = patchDate(2019, 9, 10, 12, 0, 0);

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-11-08 12:00:00",
                expirationReason: "",
                isMailInstalled: true,
                warning: "user",
            },
        });

        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This database will expire in 29 days. Log in as an administrator to correct the issue."
        );

        assert.hasClass(panel.el, "alert-info", "Color should be grey");

        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, navigation to renewal page", async function (assert) {
        assert.expect(15);

        const unpatchDate = patchDate(2019, 11, 10, 0, 0, 0);

        let callToGetParamCount = 0;

        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-20 12:00:00",
                expirationReason: "renewal",
                isMailInstalled: true,
                warning: "admin",
            },
            cookie: {
                setCookie() {
                    assert.step("setCookie");
                },
            },
            mockRPC(route, args) {
                if (args.method === "get_param") {
                    assert.step("get_param");
                    callToGetParamCount++;
                    if (callToGetParamCount === 1) {
                        return "2019-10-20 12:00:00";
                    } else if (callToGetParamCount === 2) {
                        assert.strictEqual(args.args[0], "database.expiration_date");
                        return "2019-11-09 12:00:00";
                    } else {
                        assert.strictEqual(args.args[0], "database.enterprise_code");
                        return "ABC";
                    }
                }
                if (args.method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        assert.hasClass(document.body, "o_ui_blocked", "UI should be blocked");
        assert.strictEqual(
            panel.el.querySelector(".oe_instance_register").innerText,
            "This database has expired. Renew your subscription"
        );

        assert.hasClass(panel.el, "alert-danger");
        assert.containsOnce(panel.el, ".oe_instance_renew", "Part 'Register your subscription'");
        assert.containsOnce(
            panel.el,
            "a.check_enterprise_status",
            "there should be a button for status checking"
        );

        assert.containsNone(panel.el, ".oe_instance_register_form");

        // Click on 'Renew your subscription'
        await testUtils.dom.click(panel.el.querySelector(".oe_instance_renew"));

        assert.strictEqual(
            browser.location,
            "https://www.odoo.com/odoo-enterprise/renew?contract=ABC"
        );

        assert.verifySteps([
            "get_param",
            "setCookie",
            "update_notification",
            "get_param",
            "get_param",
        ]);

        unblockUI();
        panel.destroy();
        unpatchDate();
    });

    QUnit.test("One app installed, different locale (arabic)", async function (assert) {
        assert.expect(1);

        const unpatchDate = patchDate(2019, 9, 25, 12, 0, 0);
        patchWithCleanup(luxon.Settings, {
            defaultLocale: "ar-001",
            defaultNumberingSystem: "arab",
        });

        let callToGetParamCount = 0;

        const target = getFixture(true);
        const panel = await createExpirationPanel({
            enterprise: {
                expirationDate: "2019-10-20 12:00:00",
                expirationReason: "renewal",
                isMailInstalled: true,
                warning: "admin",
            },
            async mockRPC(route, { method }) {
                if (method === "get_param") {
                    callToGetParamCount++;
                    if (callToGetParamCount === 1) {
                        return "2019-10-20 12:00:00";
                    } else if (callToGetParamCount === 2) {
                        return "2019-11-09 12:00:00";
                    }
                }
                return true;
            },
        });

        await click(document.body, ".oe_instance_renew");

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "Thank you, your registration was successful! Your database is valid until ٩ نوفمبر ٢٠١٩."
        );

        panel.destroy();
        unpatchDate();
    });
});
