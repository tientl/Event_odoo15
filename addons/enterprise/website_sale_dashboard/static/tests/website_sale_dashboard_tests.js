/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { makeView } from "@web/../tests/views/helpers";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

let serverData;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                test_report : {
                    fields: {},
                    records: [],
                },
            },
        };
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module('WebsiteSaleDashboardView');

    QUnit.test('basic rendering of the website sale dashboard view', async function (assert) {
        assert.expect(1);
        const dashboard = await makeView({
            serverData,
            resModel: "test_report",
            type: "dashboard",
            arch: `<dashboard js_class="website_sale_dashboard"/>`,
        });
        assert.containsOnce(dashboard.el, '.btn-primary[title="Go to Website"]',
            "the control panel should contain a 'Go to Website' button");
    });
});
