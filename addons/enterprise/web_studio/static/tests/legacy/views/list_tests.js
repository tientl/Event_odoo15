/** @odoo-module **/

import session from "web.session";
import { registry } from "@web/core/registry";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { click, patchWithCleanup } from "@web/../tests/helpers/utils";

import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";

import { registerStudioDependencies } from "@web_studio/../tests/helpers";
import { studioLegacyService } from "@web_studio/legacy/studio_legacy_service";

let serverData;

QUnit.module('Studio', (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        registerStudioDependencies();
        registry.category('services').add('studio_legacy', studioLegacyService);
        patchWithCleanup(session, { is_system: true });
    });

    QUnit.module('ListView');

    QUnit.test("add custom field button with other optional columns", async function (assert) {
        serverData.views["partner,false,list"] = `
            <tree>
                <field name="foo"/>
                <field name="bar" optional="hide"/>
            </tree>`;

        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, 3);

        assert.containsOnce(webClient.el, ".o_list_view");
        assert.containsOnce(webClient.el, ".o_list_view .o_optional_columns_dropdown_toggle");
        await click(webClient.el.querySelector('.o_optional_columns_dropdown_toggle'));
        assert.containsOnce(webClient, '.o_optional_columns div.dropdown-item');
        assert.containsOnce(webClient, '.o_optional_columns button.dropdown-item-studio');

        await click(webClient.el.querySelector('div.o_optional_columns button.dropdown-item-studio'));
        assert.containsNone(document.body, '.modal-studio');
        assert.containsOnce(webClient, '.o_studio .o_web_studio_editor .o_list_view');
    });


    QUnit.test("add custom field button without other optional columns", async function (assert) {
        // by default, the list in serverData doesn't contain optional fields
        const webClient = await createEnterpriseWebClient({ serverData });
        await doAction(webClient, 3);

        assert.containsOnce(webClient.el, ".o_list_view");
        assert.containsOnce(webClient.el, ".o_list_view .o_optional_columns_dropdown_toggle");
        await click(webClient.el.querySelector('.o_optional_columns_dropdown_toggle'));
        assert.containsNone(webClient, '.o_optional_columns div.dropdown-item');
        assert.containsOnce(webClient, '.o_optional_columns button.dropdown-item-studio');

        await click(webClient.el.querySelector('div.o_optional_columns button.dropdown-item-studio'));
        assert.containsNone(document.body, '.modal-studio');
        assert.containsOnce(webClient, '.o_studio .o_web_studio_editor .o_list_view');
    });
});
