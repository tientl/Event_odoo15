/** @odoo-module **/

import { createWebClient, doAction, getActionManagerServerData, loadState } from "@web/../tests/webclient/helpers";
import { click, legacyExtraNextTick } from "@web/../tests/helpers/utils";

const { loadJS } = owl.utils;

let serverData;

QUnit.module('ActionManager', {
    beforeEach() {
        serverData = getActionManagerServerData();
        Object.assign(serverData, {
            actions: {
                1: {
                    id: 1,
                    name: 'Partners Action 1',
                    res_model: 'partner',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
                },
                2: {
                    id: 2,
                    name: 'Partners Action 2',
                    res_model: 'partner',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list'], [false, 'form']],
                },
            },
            views: {
                'partner,false,kanban': `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                'partner,false,list': '<tree><field name="foo"/></tree>',
                'partner,false,form':
                    `<form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
                'partner,false,search': '<search><field name="foo" string="Foo"/></search>',
            },
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [
                        { id: 1, display_name: "First record", foo: "yop" },
                    ],
                },
            },
        });
    },
});

QUnit.test('uses a mobile-friendly view by default (if possible)', async function (assert) {
    assert.expect(4);

    const webClient = await createWebClient({ serverData });
    // should default on a mobile-friendly view (kanban) for action 1
    await doAction(webClient, 1);

    assert.containsNone(webClient, '.o_list_view');
    assert.containsOnce(webClient, '.o_kanban_view');

    // there is no mobile-friendly view for action 2, should use the first one (list)
    await doAction(webClient, 2);

    assert.containsOnce(webClient, '.o_list_view');
    assert.containsNone(webClient, '.o_kanban_view');
});

QUnit.test('lazy load mobile-friendly view', async function (assert) {
    assert.expect(12);

    const mockRPC = (route, args) => {
        assert.step(args.method || route);
    };

    const webClient = await createWebClient({ serverData, mockRPC });

    await loadState(webClient, {
        action: 1,
        view_type: 'form',
    });

    assert.containsNone(webClient, '.o_list_view');
    assert.containsNone(webClient, '.o_kanban_view');
    assert.containsOnce(webClient, '.o_form_view');

    // this lib is normally lazy loaded in the kanban view initialization.
    await loadJS("/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js");

    // go back to lazy loaded view
    await click(webClient.el, '.o_control_panel .breadcrumb .o_back_button');
    await legacyExtraNextTick();
    assert.containsNone(webClient, '.o_form_view');
    assert.containsNone(webClient, '.o_list_view');
    assert.containsOnce(webClient, '.o_kanban_view');

    assert.verifySteps([
        '/web/webclient/load_menus',
        '/web/action/load',
        'load_views',
        'onchange', // default_get/onchange to open form view
        '/web/dataset/search_read', // search read when coming back to Kanban
    ]);
});

QUnit.test('view switcher button should be displayed in dropdown on mobile screens', async function (assert) {
    assert.expect(7);

    const webClient = await createWebClient({ serverData });

    await doAction(webClient, 1);

    assert.containsOnce(webClient.el.querySelector('.o_control_panel'), '.o_cp_switch_buttons > button');
    assert.containsNone(webClient.el.querySelector('.o_control_panel'), '.o_cp_switch_buttons .o_switch_view.o_kanban');
    assert.containsNone(webClient.el.querySelector('.o_control_panel'), '.o_cp_switch_buttons button.o_switch_view');

    assert.hasClass(webClient.el.querySelector('.o_control_panel .o_cp_switch_buttons > button > span'), 'fa-th-large');
    await click(webClient.el, '.o_control_panel .o_cp_switch_buttons > button');

    assert.hasClass(webClient.el.querySelector('.o_cp_switch_buttons button.o_switch_view.o_kanban'), 'active');
    assert.doesNotHaveClass(webClient.el.querySelector('.o_cp_switch_buttons button.o_switch_view.o_list'), 'active');
    assert.hasClass(webClient.el.querySelector('.o_cp_switch_buttons button.o_switch_view.o_kanban'), 'fa-th-large');
});
