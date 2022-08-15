/** @odoo-module **/

import { getActionManagerServerData, doAction } from "@web/../tests/webclient/helpers";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { makeFakeEnterpriseService } from "../mocks";
import { registry } from "@web/core/registry";
import { createEnterpriseWebClient } from "../helpers";
import { click, legacyExtraNextTick, getFixture } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

QUnit.module("WebClient Mobile", (hooks) => {
    let serverData;
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        serviceRegistry.add("home_menu", homeMenuService);
        const fakeEnterpriseService = makeFakeEnterpriseService();
        serviceRegistry.add("enterprise", fakeEnterpriseService);
    });

    QUnit.test("scroll position is kept", async (assert) => {
        // This test relies on the fact that the scrollable element in mobile
        // is the html node.
        assert.expect(6);

        const record = serverData.models.partner.records[0];
        serverData.models.partner.records = [];

        for (let i = 0; i < 80; i++) {
            const rec = Object.assign({}, record);
            rec.id = i + 1;
            rec.display_name = `Record ${rec.id}`;
            serverData.models.partner.records.push(rec);
        }

        // force the html node to be scrollable element
        const target = getFixture();
        target.style.position = "initial";
        const webClient = await createEnterpriseWebClient({ serverData, target });

        await doAction(webClient, 3); // partners in list/kanban
        assert.containsOnce(webClient, ".o_kanban_view");

        window.scrollTo(0, 123);
        await click(webClient.el.querySelectorAll(".o_kanban_record")[20]);
        await legacyExtraNextTick();
        assert.containsOnce(webClient, ".o_form_view");
        assert.containsNone(webClient, ".o_kanban_view");

        window.scrollTo(0, 0);
        await click(webClient.el.querySelector(".o_control_panel .o_back_button"));
        await legacyExtraNextTick();
        assert.containsNone(webClient, ".o_form_view");
        assert.containsOnce(webClient, ".o_kanban_view");

        assert.strictEqual(document.firstElementChild.scrollTop, 123);
    });
});
