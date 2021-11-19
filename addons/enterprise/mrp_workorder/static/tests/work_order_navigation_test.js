odoo.define('mrp_workorder_navigation.tests', function (require) {
    "use strict";

    var testUtils = require("web.test_utils");
    const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
    const { legacyExtraNextTick } = require("@web/../tests/helpers/utils");

    let serverData;

    QUnit.module('mrp_workorder_tabletview_navigation', {
        beforeEach: function () {
            const models = {
                'mrp.workorder': {
                    fields: {
                        name: { string: "name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: 'Aladdin Name to SUNA hoga',
                        },
                    ],
                },
            };
            const views = {
              'mrp.workorder,false,form': '<form>' +
                  '<header>'+
                      '<button name="open_tablet_view" type="object" string="Process"/>'+
                  '</header>'+
                  '<group>' +
                          '<field name="name"/>' +
                  '</group>' +
                  '</form>',
              'mrp.workorder,1,form': '<form string="Production Workcenter" delete="0" create="0" class="o_workorder_tablet">' +
                  '<div class="workorder_bar">'+
                      '<div class="workorder_bar_left o_workorder_bar_content">'+
                          '<field name="id" class="o_workorder_icon_btn" widget="back_arrow" readonly="1"/>'+
                      '</div>'+
                  '</div>'+
                  '<group>' +
                          '<field name="name"/>' +
                  '</group>' +
                  '</form>',
              'mrp.workorder,false,search': '<search><field name="name" string="Foo"/></search>',
          };
            serverData = { models, views };
        },
    }, function() {
        QUnit.test("workorder navigation", async function (assert) {
            assert.expect(2);
            const webClient = await createWebClient({
                serverData,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_button' & args.method == "open_tablet_view") {
                        return Promise.resolve({
                            res_model: 'mrp.workorder',
                            type: 'ir.actions.act_window',
                            res_id: 1,
                            target: 'fullscreen',
                            flags: {
                                'withControlPanel': false,
                                'form_view_initial_mode': 'edit',
                            },
                            views: [[1, 'form']]
                        });
                    }
                    if (route === '/web/dataset/call_kw/mrp.workorder/action_back') {
                        return Promise.resolve(true);
                    }
                },
            });
            await doAction(webClient, {
                res_model: 'mrp.workorder',
                type: 'ir.actions.act_window',
                res_id: 1,
                views: [[false, 'form']]
            }); // open workorder form view action
            await testUtils.dom.click($('button[name="open_tablet_view"]'));
            await legacyExtraNextTick();
            assert.containsOnce(webClient, '.o_workorder_tablet', "tablet view should be opened");

            await testUtils.dom.click($('.btn.o_workorder_icon_btn'));
            await legacyExtraNextTick();
            assert.strictEqual($(webClient.el).find('.breadcrumb-item').length, 1, "there should be only one controller in actionManager");
        });
    });
});
