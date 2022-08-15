/** @odoo-module **/

import AbstractView from "web.AbstractView";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    legacyExtraNextTick,
    nextTick,
    patchDate,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import {
    editFavoriteName,
    getFacetTexts,
    isItemSelected,
    isOptionSelected,
    removeFacet,
    saveFavorite,
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
    switchView,
    toggleAddCustomFilter,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    validateSearch,
} from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { GraphView } from "@web/views/graph/graph_view";
import { actionService } from "@web/webclient/actions/action_service";
import { companyService } from "@web/webclient/company_service";
import { DashboardModel } from "@web_dashboard/dashboard_model";
import { FieldFloat } from "web.basic_fields";
import legacyFieldRegistry from "web.field_registry";
import legacyViewRegistry from "web.view_registry";
import PieChart from "web.PieChart";
import Widget from "web.Widget";
import widgetRegistry from "web.widget_registry";

const serviceRegistry = registry.category("services");

QUnit.module("Views", (hooks) => {
    let serverData;

    hooks.beforeEach(async () => {
        serverData = {
            models: {
                test_report: {
                    fields: {
                        categ_id: {
                            string: "categ_id",
                            type: "many2one",
                            relation: "test_report",
                            store: true,
                            sortable: true,
                        },
                        sold: { string: "Sold", type: "float", store: true, group_operator: "sum", sortable: true },
                        untaxed: {
                            string: "Untaxed",
                            type: "float",
                            group_operator: "sum",
                            store: true,
                            sortable: true,
                        },
                    },
                    records: [
                        {
                            display_name: "First",
                            id: 1,
                            sold: 5,
                            untaxed: 10,
                            categ_id: 1,
                        },
                        {
                            display_name: "Second",
                            id: 2,
                            sold: 3,
                            untaxed: 20,
                            categ_id: 2,
                        },
                    ],
                },
                test_time_range: {
                    fields: {
                        categ_id: { string: "categ_id", type: "many2one", relation: "test_report", sortable: true },
                        sold: { string: "Sold", type: "float", store: true, group_operator: "sum", sortable: true },
                        untaxed: {
                            string: "Untaxed",
                            type: "float",
                            group_operator: "sum",
                            store: true,
                            sortable: true,
                        },
                        date: { string: "Date", type: "date", store: true, sortable: true },
                        transformation_date: {
                            string: "Transformation Date",
                            type: "datetime",
                            store: true,
                            sortable: true,
                        },
                    },
                    records: [
                        {
                            display_name: "First",
                            id: 1,
                            sold: 5,
                            untaxed: 10,
                            categ_id: 1,
                            date: "1983-07-15",
                            transformation_date: "2018-07-30 04:56:00",
                        },
                        {
                            display_name: "Second",
                            id: 2,
                            sold: 3,
                            untaxed: 20,
                            categ_id: 2,
                            date: "1984-12-15",
                            transformation_date: "2018-12-15 14:07:03",
                        },
                    ],
                },
            },
            views: {
                "test_report,false,dashboard": `<dashboard/>`,
            },
        };
        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("company", companyService);
        serviceRegistry.add("user", makeFakeUserService());
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        patchWithCleanup(session, {
            companies_currency_id: {
                1: 11,
            },
            currencies: {
                11: {
                    digits: [69, 2],
                    position: "before",
                    symbol: "$",
                },
            },
        });
    });

    QUnit.module("DashboardView");

    QUnit.test("basic rendering of a dashboard with groups", async function (assert) {
        const dashboard = await makeView({
            serverData,
            type: "dashboard",
            resModel: "test_report",
            arch: `
                <dashboard>
                    <group>
                        <group></group>
                    </group>
                </dashboard>
            `,
        });
        assert.hasClass(dashboard.el, "o_dashboard_view");
        assert.containsN(dashboard, ".o_group", 2, "should have rendered two groups");
        assert.hasClass(
            dashboard.el.querySelector(".o_group .o_group"),
            "o_group_col_2",
            "inner group should have className o_group_col_2"
        );
    });

    QUnit.test(
        "basic rendering of a dashboard with quotes in string attributes",
        async function (assert) {
            assert.expect(4);

            serverData.models.test_report.fields.my_field = {
                type: "float",
                group_operator: "sum",
            };
            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <group>
                            <aggregate
                                name='my_field'
                                string='test " 1'
                                value_label='test " 2'
                                help='test " 3'
                                field="my_field"
                            />
                        </group>
                    </dashboard>
                `,
            });
            const agg = dashboard.el.querySelector(".o_aggregate");
            const tooltipInfo = JSON.parse(agg.dataset.tooltipInfo);
            assert.strictEqual(tooltipInfo.name, "my_field", "the help value should be `my_field`");
            assert.strictEqual(
                tooltipInfo.displayName,
                'test " 1',
                'the help value should be `test " 1`'
            );
            assert.strictEqual(
                tooltipInfo.valueLabel,
                'test " 2',
                'the valueLabel should be `test " 2`'
            );
            assert.strictEqual(tooltipInfo.help, 'test " 3', 'the help value should be `test " 3`');
        }
    );

    QUnit.test("basic rendering of a widget tag", async function (assert) {
        assert.expect(1);

        const MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
                this._super.apply(this, arguments);
            },
            start: function () {
                this.$el.text(JSON.stringify(this.data));
            },
        });
        widgetRegistry.add("test", MyWidget);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <widget name="test"/>
                </dashboard>
            `,
        });

        assert.containsOnce(dashboard, ".o_widget", "there should be a node with widget class");
    });

    QUnit.test("basic rendering of a pie chart widget", async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        assert.expect(7);

        let pieChart = null;
        patchWithCleanup(PieChart.prototype, {
            init() {
                pieChart = this;
                this._super(...arguments);
            },
        });

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <widget name="pie_chart" title="Products sold" attrs="{'measure': 'sold', 'groupby': 'categ_id'}"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/test_report/read_group") {
                    assert.deepEqual(args.args, []);
                    assert.deepEqual(args.model, "test_report");
                    assert.deepEqual(args.method, "read_group");
                    assert.deepEqual(args.kwargs, {
                        context: {
                            allowed_company_ids: [1],
                            fill_temporal: true,
                            lang: "en",
                            tz: "taht",
                            uid: 7,
                        },
                        domain: [],
                        fields: ["categ_id", "sold"],
                        groupby: ["categ_id"],
                        lazy: false,
                    });
                }
            },
            legacyParams: { withLegacyMockServer: true },
        });

        assert.strictEqual($(".o_widget").length, 1, "there should be a node with o_widget class");
        const chartTitle = dashboard.el.querySelector(".o_pie_chart .o_legacy_graph_renderer label")
            .textContent;
        assert.strictEqual(
            chartTitle,
            "Products sold",
            "the title of the graph should be displayed"
        );
        const chart = pieChart.controller.renderer.componentRef.comp.chart;
        const legendText = $(chart.generateLegend()).text().trim();
        assert.strictEqual(legendText, "FirstSecond", "there should be two legend items");
    });

    QUnit.test("basic rendering of empty pie chart widget", async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        serverData.models.test_time_range.records = [];
        serverData.models.test_report.records = [];

        let pieChart = null;
        patchWithCleanup(PieChart.prototype, {
            init() {
                pieChart = this;
                this._super(...arguments);
            },
        });

        await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <widget name="pie_chart" attrs="{'measure': 'sold', 'groupby': 'categ_id'}"/>
                </dashboard>
            `,
            legacyParams: { withLegacyMockServer: true },
        });
        const chart = pieChart.controller.renderer.componentRef.comp.chart;
        const legendText = $(chart.generateLegend()).text().trim();
        assert.strictEqual(legendText, "No data", "the legend should contain the item 'No data'");
    });

    QUnit.test(
        "pie chart mode, groupby, and measure not altered by favorite filters",
        async function (assert) {
            // Pie Chart is rendered asynchronously.
            // concurrency.delay is a fragile way that we use to wait until the
            // graph is rendered.
            // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
            assert.expect(7);

            let pieChart = null;
            patchWithCleanup(PieChart.prototype, {
                init() {
                    pieChart = this;
                    this._super(...arguments);
                },
            });

            await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                context: {
                    graph_mode: "line",
                    graph_measure: "untaxed",
                    graph_groupbys: [],
                },
                arch: `
                    <dashboard>
                        <widget name="pie_chart" title="Products sold" attrs="{'measure': 'sold', 'groupby': 'categ_id'}"/>
                    </dashboard>
                `,
                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/test_report/read_group") {
                        assert.deepEqual(args.args, []);
                        assert.deepEqual(args.model, "test_report");
                        assert.deepEqual(args.method, "read_group");
                        assert.deepEqual(args.kwargs, {
                            context: {
                                allowed_company_ids: [1],
                                fill_temporal: true,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            domain: [],
                            fields: ["categ_id", "sold"],
                            groupby: ["categ_id"],
                            lazy: false,
                        });
                    }
                },
                legacyParams: { withLegacyMockServer: true },
            });
            assert.strictEqual(
                $(".o_widget").length,
                1,
                "there should be a node with o_widget class"
            );
            assert.strictEqual(
                $(".o_pie_chart .o_legacy_graph_renderer label").text(),
                "Products sold",
                "the title of the graph should be displayed"
            );

            const chart = pieChart.controller.renderer.componentRef.comp.chart;
            const legendText = $(chart.generateLegend()).text().trim();
            assert.strictEqual(legendText, "FirstSecond", "there should be two legend items");
        }
    );

    QUnit.test("rendering of a pie chart widget and comparison active", async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        assert.expect(13);

        const searchViewArch = `<search><filter name="date" date="date" /></search>`;

        patchDate(2017, 2, 22, 1, 0, 0);

        const readGroupDomains = [
            [],
            ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
            ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
            ["&", ["date", ">=", "2017-02-01"], ["date", "<=", "2017-02-28"]],
        ];

        const mockRPC = async (route, args) => {
            assert.step(args.method);
            assert.deepEqual(args.kwargs.domain, readGroupDomains.shift());
        };

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            searchViewArch,
            mockRPC,
            arch: `
                <dashboard>
                    <widget name="pie_chart" title="Products sold" attrs="{'measure': 'sold', 'groupby': 'categ_id'}"/>
                </dashboard>
            `,
        });

        assert.verifySteps(["read_group"]);

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "date");
        await toggleMenuItemOption(dashboard, "date", "March");
        assert.verifySteps(["read_group"]);
        await toggleFilterMenu(dashboard); // Close the filter menu

        // Apply range with today and comparison with previous period
        await toggleComparisonMenu(dashboard);
        await toggleMenuItem(dashboard, "date: Previous period");
        assert.verifySteps(["read_group", "read_group"]);

        assert.strictEqual($(".o_widget").length, 1, "there should be a node with o_widget class");
        const chartTitle = $(".o_pie_chart .o_legacy_graph_renderer label").text();
        assert.strictEqual(
            chartTitle,
            "Products sold",
            "the title of the graph should be displayed"
        );
    });

    QUnit.test("basic rendering of an aggregate tag inside a group", async function (assert) {
        assert.expect(8);
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["sold:sum(sold)"],
                        "should read the correct field"
                    );
                    assert.deepEqual(args.kwargs.domain, [], "should send the correct domain");
                    assert.deepEqual(args.kwargs.groupby, [], "should send the correct groupby");
                }
            },
        });

        assert.containsOnce(dashboard, ".o_aggregate", "should have rendered an aggregate");
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate > label").textContent,
            "sold",
            "should have correctly rendered the aggregate's label"
        );
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate > .o_value").textContent.trim(),
            "8.00",
            "should correctly display the aggregate's value"
        );
        assert.verifySteps(["read_group"]);
    });

    QUnit.test(
        "aggregate group_operator from the arch overrides the one on the field",
        async function (assert) {
            assert.expect(3);

            serverData.models.test_report.fields.sold.group_operator = "fromField";
            await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <group>
                            <aggregate name="sold" field="sold" group_operator="fromArch"/>
                        </group>
                    </dashboard>
                `,
                mockRPC(route, args) {
                    assert.step(args.method || route);
                    if (args.method === "read_group") {
                        assert.deepEqual(
                            args.kwargs.fields,
                            ["sold:fromArch(sold)"],
                            "should read the correct field"
                        );
                        return [{}];
                    }
                },
            });
            assert.verifySteps(["read_group"]);
        }
    );

    QUnit.test("aggregate group_operator from field", async function (assert) {
        assert.expect(3);

        serverData.models.test_report.fields.sold.group_operator = "fromField";
        await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["sold:fromField(sold)"],
                        "should read the correct field"
                    );
                    return [{}];
                }
            },
        });
        assert.verifySteps(["read_group"]);
    });

    QUnit.test("basic rendering of a aggregate tag with widget attribute", async function (assert) {
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold" widget="float_time"/>
                    </group>
                </dashboard>
            `,
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent.trim(),
            "08:00",
            "should correctly display the aggregate's value"
        );
    });

    QUnit.test("Aggregates are not transmitted to the control panel", async function (assert) {
        serverData.models.test_report.fields.sold.searchable = true;
        const dashboard = await makeView({
            type: "dashboard",
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold_aggregate" field="sold"/>
                    </group>
                </dashboard>
            `,
            serverData,
            resModel: "test_report",
        });

        await toggleFilterMenu(dashboard);
        await toggleAddCustomFilter(dashboard);

        assert.containsOnce(dashboard, ".o_generator_menu_field > option[value=sold]");
        assert.containsNone(dashboard, ".o_generator_menu_field > option[value=sold_aggregate]");
    });

    QUnit.test("basic rendering of a formula tag inside a group", async function (assert) {
        assert.expect(8);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold"/>
                        <aggregate name="untaxed" field="untaxed"/>
                        <formula name="formula" string="Some label" value="record.sold * record.untaxed"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["sold:sum(sold)", "untaxed:sum(untaxed)"],
                        "should read the correct fields"
                    );
                    assert.deepEqual(args.kwargs.domain, [], "should send the correct domain");
                    assert.deepEqual(args.kwargs.groupby, [], "should send the correct groupby");
                }
            },
        });

        assert.containsOnce(dashboard, '[name="formula"]', "should have rendered a formula");
        assert.strictEqual(
            dashboard.el.querySelector('[name="formula"] > label').textContent,
            "Some label",
            "should have correctly rendered the label"
        );
        assert.strictEqual(
            dashboard.el.querySelector('[name="formula"] > .o_value').textContent.trim(),
            "240.00",
            "should have correctly computed the formula value"
        );
        assert.verifySteps(["read_group"]);
    });

    QUnit.test("basic rendering of a graph tag", async function (assert) {
        assert.expect(9);

        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id"/>
                <field name="sold" type="measure"/>
            </graph>
        `;

        const dashboard = await makeView({
            serverData,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["categ_id", "sold"],
                        "should read the correct fields"
                    );
                    assert.deepEqual(
                        args.kwargs.groupby,
                        ["categ_id"],
                        "should group by the correct field"
                    );
                }
            },
            resModel: "test_report",
            type: "dashboard",
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>
            `,
        });

        assert.containsOnce(dashboard, ".o_subview[type='graph'] .o_graph_view");
        assert.containsNone(dashboard, ".o_subview .o_graph_view .o_control_panel .o_cp_top_left");
        assert.containsNone(dashboard, ".o_subview .o_graph_view .o_control_panel .o_cp_top_right");
        assert.containsOnce(
            dashboard,
            ".o_subview .o_graph_view .o_control_panel .o_cp_bottom_left"
        );
        assert.containsNone(
            dashboard,
            ".o_subview .o_graph_view .o_control_panel .o_cp_bottom_right"
        );
        assert.containsOnce(
            dashboard,
            ".o-web-dashboard-view-wrapper--switch-button",
            "should have rendered an additional switch button"
        );

        assert.verifySteps(["load_views", "web_read_group"]);
    });

    QUnit.test("graph tag without aggregate and invisible field", async function (assert) {
        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id"/>
                <field name="sold" invisible="1"/>
            </graph>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>
            `,
        });
        await toggleMenu(dashboard, "Measures");
        assert.containsNone(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be invisible in the measures"
        );
    });

    QUnit.test("graph tag with aggregate and invisible field", async function (assert) {
        assert.expect(2);
        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id" invisible="1"/>
            </graph>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                    <group>
                        <aggregate name="categ_id_agg" field="categ_id"/>
                    </group>
                </dashboard>
            `,
        });
        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be available as a graph measure"
        );
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("categ_id")',
            "the categ_id field should be available as a graph measure"
        );
    });

    QUnit.test("graph tag with no aggregate and invisible field", async function (assert) {
        assert.expect(2);
        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id" invisible="1"/>
            </graph>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>`,
        });

        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be available as a graph measure"
        );
        assert.containsNone(
            dashboard,
            '.o_menu_item:contains("categ_id")',
            "the categ field should not be available as a graph measure"
        );
    });

    QUnit.test("graph tag and date aggregate", async function (assert) {
        assert.expect(2);
        serverData.views["test_time_range,some_xmlid,graph"] = `<graph/>`;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                    <group>
                        <aggregate name="date_agg" group_operator="max" field="date"/>
                    </group>
                </dashboard>`,
            mockRPC: function (route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve([
                        {
                            __count: 1,
                            date: "1983-07-15",
                        },
                    ]);
                }
            },
        });

        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be available as a graph measure"
        );
        assert.containsNone(
            dashboard,
            '.o_menu_item:contains("Date")',
            "the Date field should not be available as a graph measure"
        );
    });

    QUnit.test("basic rendering of a pivot tag", async function (assert) {
        assert.expect(10);
        serverData.views["test_report,some_xmlid,pivot"] = `
            <pivot>
                <field name="categ_id" type="row"/>
                <field name="sold" type="measure"/>
            </pivot>
        `;
        let nbReadGroup = 0;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="pivot" ref="some_xmlid"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    nbReadGroup++;
                    const groupBy = nbReadGroup === 1 ? [] : ["categ_id"];
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["sold:sum"],
                        "should read the correct fields"
                    );
                    assert.deepEqual(
                        args.kwargs.groupby,
                        groupBy,
                        "should group by the correct field"
                    );
                }
            },
        });

        assert.containsOnce(
            dashboard,
            ".o-web-dashboard-view-wrapper--switch-button",
            "should have rendered an additional switch button"
        );
        assert.containsOnce(dashboard, ".o_subview .o_pivot", "should have rendered a pivot view");

        assert.verifySteps(["load_views", "read_group", "read_group"]);
    });

    QUnit.test("pivot tag without aggregate and invisible field", async function (assert) {
        serverData.views["test_report,some_xmlid,pivot"] = `
            <pivot>
                <field name="categ_id" type="row"/>
                <field name="sold" invisible="1"/>
            </pivot>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="pivot" ref="some_xmlid"/>
                </dashboard>
            `,
        });

        await toggleMenu(dashboard, "Measures");
        assert.containsNone(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be invisible in the measures"
        );
    });

    QUnit.test("pivot tag with aggregate and invisible field", async function (assert) {
        assert.expect(2);
        serverData.views["test_report,some_xmlid,pivot"] = `
            <pivot>
                <field name="categ_id" invisible="1" type="measure"/>
            </pivot>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="pivot" ref="some_xmlid"/>
                    <group>
                        <aggregate name="categ_id_agg" field="categ_id"/>
                    </group>
                </dashboard>
            `,
        });

        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be available as a pivot measure"
        );
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("categ_id")',
            "the categ_id field should be available as a pivot measure"
        );
    });

    QUnit.test("basic rendering of a cohort tag", async function (assert) {
        assert.expect(5);
        serverData.views["test_report,some_xmlid,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>
        `;
        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";

        const readGroups = [[], ["categ_id"]];
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    const groupBy = readGroups.shift();
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["sold"],
                        "should read the correct fields"
                    );
                    assert.deepEqual(
                        args.kwargs.groupby,
                        groupBy,
                        "should group by the correct field"
                    );
                }
            },
        });

        assert.containsOnce(
            dashboard,
            ".o-web-dashboard-view-wrapper--switch-button",
            "should have rendered an additional switch button"
        );
        assert.containsOnce(
            dashboard,
            ".o_subview[type='cohort'] .o_cohort_view",
            "should have rendered a cohort view"
        );

        assert.verifySteps(["load_views", "get_cohort_data"]);
    });

    QUnit.test("cohort tag without aggregate and invisible field", async function (assert) {
        serverData.views["test_report,some_xmlid,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week">
                <field name="sold" invisible="1"/>
            </cohort>
        `;
        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                </dashboard>
            `,
        });

        await toggleMenu(dashboard, "Measures");
        assert.containsNone(
            dashboard,
            '.o_cohort_measures_list button[data-field="sold"]',
            "the sold field should be invisible in the measures"
        );
    });

    QUnit.test("cohort tag with aggregate and invisible field", async function (assert) {
        serverData.views["test_report,some_xmlid,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week">
                <field name="categ_id" invisible="1"/>
            </cohort>
        `;
        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                    <group>
                        <aggregate name="categ_id_agg" field="categ_id"/>
                    </group>
                </dashboard>
            `,
        });

        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            '.o_menu_item:contains("Sold")',
            "the sold field should be in the measures"
        );
        assert.containsNone(
            dashboard,
            '.o_cohort_measures_list button[data-field="categ_id"]',
            "the categ_id field should not be in the measures"
        ); // this is wrong and should be fixed!
    });

    QUnit.test("rendering of an aggregate with widget monetary", async function (assert) {
        patchWithCleanup(session, {
            companies_currency_id: {
                1: 44,
            },
            currencies: {
                44: {
                    digits: [69, 2],
                    position: "after",
                    symbol: "€",
                },
            },
        });

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold" widget="monetary"/>
                    </group>
                </dashboard>
            `,
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent.trim(),
            "8.00 €",
            "should format the amount with the correct currency"
        );
    });

    QUnit.test(
        "rendering of an aggregate with widget monetary in multi-company",
        async function (assert) {
            assert.expect(1);

            patchWithCleanup(browser, {
                location: Object.assign({}, browser.location, { hash: "#cids=3%2C1" }),
            });

            patchWithCleanup(session, {
                companies_currency_id: {
                    1: 11,
                    3: 33,
                },
                currencies: {
                    11: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$",
                    },
                    33: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "£",
                    },
                },
                user_companies: Object.assign({}, session.user_companies, {
                    allowed_companies: Object.assign({}, session.user_companies.allowed_companies, {
                        3: { id: 3, name: "Cinnamon Girl" },
                    }),
                }),
            });

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <group>
                            <aggregate name="sold" field="sold" widget="monetary"/>
                        </group>
                    </dashboard>
                `,
            });

            assert.strictEqual(
                dashboard.el.querySelector(".o_value").textContent.trim(),
                "£ 8.00",
                "should format the amount with the correct currency"
            );
        }
    );

    QUnit.test("rendering of an aggregate with value label", async function (assert) {
        serverData.models.test_report.fields.days = { string: "Days to Confirm", type: "float" };
        serverData.models.test_report.records[0].days = 5.3;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="days" field="days" value_label="days"/>
                        <aggregate name="sold" field="sold"/>
                    </group>
                </dashboard>
            `,
        });

        assert.strictEqual(
            dashboard.el.querySelectorAll(".o_value")[0].textContent,
            "5.30 days",
            "should have a value label"
        );
        assert.strictEqual(
            dashboard.el.querySelectorAll(".o_value")[1].textContent.trim(),
            "8.00",
            "shouldn't have any value label"
        );
    });

    QUnit.test("rendering of field of type many2one", async function (assert) {
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                       <aggregate name="categ_id" field="categ_id"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["categ_id:count_distinct(categ_id)"],
                        "should specify 'count_distinct' group operator"
                    );
                    return [{ categ_id: 2 }];
                }
            },
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent.trim(),
            "2",
            "should correctly display the value, formatted as an integer"
        );
    });

    QUnit.test("rendering of formula with widget attribute (formatter)", async function (assert) {
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <aggregate name="sold" field="sold" invisible="1"/>
                    <aggregate name="untaxed" field="untaxed" invisible="1"/>
                    <formula label="Some value" value="record.sold / record.untaxed" widget="percentage"/>
                </dashboard>
            `,
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent.trim(),
            "26.67%",
            "should correctly display the value"
        );
    });

    QUnit.test(
        "rendering of formula with widget attribute (widget legacy)",
        async function (assert) {
            assert.expect(3);

            const MyWidget = FieldFloat.extend({
                start: function () {
                    this.$el.text("The value is " + this._formatValue(this.value));
                },
            });
            legacyFieldRegistry.add("test", MyWidget);

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                <dashboard>
                    <aggregate name="sold" field="sold" invisible="1"/>
                    <aggregate name="untaxed" field="untaxed" invisible="1"/>
                    <formula name="some_value" value="record.sold / record.untaxed" widget="test"/>
                </dashboard>
            `,
            });
            await legacyExtraNextTick();
            assert.containsOnce(dashboard, ".o_value");
            assert.isVisible(dashboard.el.querySelector(".o_value"));
            assert.strictEqual(
                dashboard.el.querySelector(".o_value").textContent,
                "The value is 0.27",
                "should have used the specified widget (as there is no 'test' formatter)"
            );

            delete legacyFieldRegistry.map.test;
        }
    );

    QUnit.test("invisible attribute on a field", async function (assert) {
        assert.expect(2);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold" invisible="1"/>
                    </group>
                </dashboard>
            `,
        });

        assert.containsNone(dashboard, ".o_group > div");
        assert.containsNone(dashboard, ".o_aggregate[name=sold]");
    });

    QUnit.test("invisible attribute on a formula", async function (assert) {
        assert.expect(1);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <formula name="formula" value="2" invisible="1"/>
                </dashboard>
            `,
        });

        assert.containsNone(dashboard, ".o_formula");
        // assert.hasClass(
        //     // Idem as before
        //     dashboard.el.querySelector(".o_formula"),
        //     "o_invisible_modifier",
        //     "the formula should be invisible"
        // );
    });

    QUnit.test("invisible modifier on an aggregate", async function (assert) {
        assert.expect(1);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="untaxed" field="untaxed" />
                        <aggregate name="sold" field="sold"  attrs="{'invisible': [('untaxed','=',30)]}"/>
                    </group>
                </dashboard>
            `,
        });

        assert.containsNone(dashboard, ".o_aggregate[name=sold]");
        // assert.hasClass(
        //     dashboard.el.querySelector(".o_aggregate[name=sold]"),
        //     "o_invisible_modifier",
        //     "the aggregate 'sold' should be invisible"
        // );
    });

    QUnit.test("invisible modifier on a formula", async function (assert) {
        assert.expect(1);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold"/>
                        <aggregate name="untaxed" field="untaxed"/>
                        <formula label="Some value" value="record.sold / record.untaxed" attrs="{'invisible': [('untaxed','=',30)]}"/>
                    </group>
                </dashboard>
            `,
        });

        assert.containsNone(dashboard, ".o_formula");
        // assert.hasClass(
        //     dashboard.el.querySelector(".o_formula"),
        //     "o_invisible_modifier",
        //     "the formula should be invisible"
        // );
    });

    QUnit.test("rendering of aggregates with domain attribute", async function (assert) {
        assert.expect(11);

        let nbReadGroup = 0;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="untaxed" field="untaxed"/>
                        <aggregate name="sold" field="sold" domain="[('categ_id', '=', 1)]"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "read_group") {
                    nbReadGroup++;
                    if (nbReadGroup === 1) {
                        assert.deepEqual(
                            args.kwargs.fields,
                            ["untaxed:sum(untaxed)"],
                            "should read the correct field"
                        );
                        assert.deepEqual(args.kwargs.domain, [], "should send the correct domain");
                        assert.deepEqual(
                            args.kwargs.groupby,
                            [],
                            "should send the correct groupby"
                        );
                    } else {
                        assert.deepEqual(
                            args.kwargs.fields,
                            ["sold:sum(sold)"],
                            "should read the correct field"
                        );
                        assert.deepEqual(
                            args.kwargs.domain,
                            [["categ_id", "=", 1]],
                            "should send the correct domain"
                        );
                        assert.deepEqual(
                            args.kwargs.groupby,
                            [],
                            "should send the correct groupby"
                        );
                    }
                }
            },
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate[name=untaxed] .o_value").textContent.trim(),
            "30.00",
            "should correctly display the aggregate's value"
        );
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate[name=sold] .o_value").textContent.trim(),
            "5.00",
            "should correctly display the aggregate's value"
        );

        assert.verifySteps(["read_group", "read_group"]);
    });

    QUnit.test(
        "two aggregates with the same field attribute with different domain",
        async function (assert) {
            assert.expect(11);

            let nbReadGroup = 0;
            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <group>
                            <aggregate name="sold" field="sold"/>
                            <aggregate name="sold_categ_1" field="sold" domain="[('categ_id', '=', 1)]"/>
                        </group>
                    </dashboard>
                `,
                mockRPC(route, args) {
                    assert.step(args.method || route);
                    if (args.method === "read_group") {
                        nbReadGroup++;
                        if (nbReadGroup === 1) {
                            assert.deepEqual(
                                args.kwargs.fields,
                                ["sold:sum(sold)"],
                                "should read the correct field"
                            );
                            assert.deepEqual(
                                args.kwargs.domain,
                                [],
                                "should send the correct domain"
                            );
                            assert.deepEqual(
                                args.kwargs.groupby,
                                [],
                                "should send the correct groupby"
                            );
                        } else {
                            assert.deepEqual(
                                args.kwargs.fields,
                                ["sold_categ_1:sum(sold)"],
                                "should read the correct field"
                            );
                            assert.deepEqual(
                                args.kwargs.domain,
                                [["categ_id", "=", 1]],
                                "should send the correct domain"
                            );
                            assert.deepEqual(
                                args.kwargs.groupby,
                                [],
                                "should send the correct groupby"
                            );
                            // mockReadGroup doesn't handle this kind of requests yet, so we hardcode
                            // the result in the test
                            return [{ sold_categ_1: 5 }];
                        }
                    }
                },
            });

            assert.strictEqual(
                dashboard.el.querySelector(".o_aggregate[name=sold] .o_value").textContent.trim(),
                "8.00",
                "should correctly display the aggregate's value"
            );
            assert.strictEqual(
                dashboard.el
                    .querySelector(".o_aggregate[name=sold_categ_1] .o_value")
                    .textContent.trim(),
                "5.00",
                "should correctly display the aggregate's value"
            );

            assert.verifySteps(["read_group", "read_group"]);
        }
    );

    QUnit.test("formula based on same field with different domains", async function (assert) {
        assert.expect(1);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="untaxed_categ_1" field="untaxed"  domain="[('categ_id', '=', 1)]"/>
                        <aggregate name="untaxed_categ_2" field="untaxed"  domain="[('categ_id', '=', 2)]"/>
                        <formula label="Ratio" value="record.untaxed_categ_1 / record.untaxed_categ_2"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    // mockReadGroup doesn't handle this kind of requests yet, so we hardcode
                    // the result in the test
                    const name = args.kwargs.fields[0].split(":")[0];
                    return [{ [name]: name === "untaxed_categ_1" ? 10.0 : 20.0 }];
                }
            },
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_formula .o_value").textContent.trim(),
            "0.50",
            "should have correctly computed and displayed the formula"
        );
    });

    QUnit.test("clicking on an aggregate", async function (assert) {
        assert.expect(17);
        serverData.views = {
            "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                    <field name="sold" type="measure"/>
                </graph>
                `,
            "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                    <field name="sold" type="measure"/>
                </pivot>
                `,
        };
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="untaxed" field="untaxed"/>
                        <aggregate name="sold" field="sold"/>
                    </group>
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    for (const i in args.kwargs.fields) {
                        assert.step(args.kwargs.fields[i]);
                    }
                }
            },
        });

        let graph = dashboard.el.querySelector(".o_subview[type='graph']");
        let pivot = dashboard.el.querySelector(".o_subview[type='pivot']");
        await toggleMenu(graph, "Measures");
        assert.ok(isItemSelected(graph, "Sold"), "sold measure should be active in graph view");

        assert.notOk(
            isItemSelected(graph, "Untaxed"),
            "untaxed measure should not be active in graph view"
        );

        await toggleMenu(pivot, "Measures");

        assert.ok(isItemSelected(pivot, "Sold"), "sold measure should be active in pivot view");

        assert.notOk(
            isItemSelected(pivot, "Untaxed"),
            "untaxed measure should not be active in pivot view"
        );

        // click on the 'untaxed' field: it should activate the 'untaxed' measure in both subviews
        await click(dashboard.el.querySelector(".o_aggregate[name=untaxed]"));
        graph = dashboard.el.querySelector(".o_subview[type='graph']");
        pivot = dashboard.el.querySelector(".o_subview[type='pivot']");
        await toggleMenu(graph, "Measures");
        assert.ok(
            isItemSelected(graph, "Untaxed"),
            "untaxed measure should be active in graph view"
        );

        assert.notOk(
            isItemSelected(graph, "Sold"),
            "sold measure should not be active in graph view"
        );

        await toggleMenu(pivot, "Measures");

        assert.ok(
            isItemSelected(pivot, "Untaxed"),
            "Untaxed measure should be active in pivot view"
        );

        assert.notOk(
            isItemSelected(pivot, "Sold"),
            "Sold measure should not be active in pivot view"
        );

        assert.verifySteps([
            "untaxed:sum(untaxed)",
            "sold:sum(sold)", // fields
            "sold:sum", // pivot
            "sold:sum", // pivot
            "untaxed:sum(untaxed)",
            "sold:sum(sold)", // fields
            "untaxed:sum", // pivot
            "untaxed:sum", // pivot
        ]);
    });

    QUnit.test("clicking on an aggregate interaction with cohort", async function (assert) {
        assert.expect(11);

        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";
        serverData.views["test_report,false,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week" measure="sold"/>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="untaxed" field="untaxed"/>
                        <aggregate name="sold" field="sold"/>
                    </group>
                    <view type="cohort"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    for (const i in args.kwargs.fields) {
                        assert.step(args.kwargs.fields[i]);
                    }
                }
                if (args.method === "get_cohort_data") {
                    assert.step(args.kwargs.measure);
                }
            },
        });

        await toggleMenu(dashboard, "Measures");
        assert.ok(
            isItemSelected(dashboard, "Sold"),
            "Sold measure should be active in cohort view"
        );

        assert.notOk(
            isItemSelected(dashboard, "Untaxed"),
            "untaxed measure should not be active in cohort view"
        );

        // click on the 'untaxed' field: it should activate the 'untaxed' measure in cohort subview
        await click(dashboard.el.querySelector(".o_aggregate[name=untaxed]"));

        await toggleMenu(dashboard, "Measures");
        assert.ok(
            isItemSelected(dashboard, "Untaxed"),
            "untaxed measure should be active in cohort view"
        );

        assert.notOk(
            isItemSelected(dashboard, "Sold"),
            "sold measure should not be active in cohort view"
        );

        assert.verifySteps([
            "untaxed:sum(untaxed)",
            "sold:sum(sold)", // fields
            "sold", // cohort
            "untaxed:sum(untaxed)",
            "sold:sum(sold)", // fields
            "untaxed", // cohort
        ]);
    });

    QUnit.test("clicking on aggregate with domain attribute", async function (assert) {
        assert.expect(15);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="untaxed" field="untaxed" domain="[('categ_id', '=', 2)]" domain_label="Category 2"/>
                        <aggregate name="sold" field="sold" domain="[('categ_id', '=', 1)]"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    assert.step(args.kwargs.fields[0]);
                    assert.step(args.kwargs.domain.join(""));
                }
            },
        });

        // click on the 'untaxed' field: it should update the domain
        await click(dashboard.el.querySelector(".o_aggregate[name=untaxed]"));
        assert.strictEqual(
            dashboard.el.querySelector(".o_control_panel .o_facet_values").textContent.trim(),
            "Category 2",
            "should correctly display the filter in the search view"
        );

        // click on the 'sold' field: it should update the domain
        await click(dashboard.el.querySelector(".o_aggregate[name=sold]"));
        assert.strictEqual(
            dashboard.el.querySelector(".o_control_panel .o_facet_values").textContent.trim(),
            "sold",
            "should correctly display the filter in the search view"
        );

        assert.verifySteps([
            // initial read_groups
            "untaxed:sum(untaxed)",
            "categ_id,=,2",
            "sold:sum(sold)",
            "categ_id,=,1",
            // 'untaxed' field clicked
            "untaxed:sum(untaxed)",
            "&categ_id,=,2categ_id,=,2",
            "sold:sum(sold)",
            "&categ_id,=,1categ_id,=,2",
            // 'sold' field clicked
            "untaxed:sum(untaxed)",
            "&categ_id,=,2categ_id,=,1",
            "sold:sum(sold)",
            "&categ_id,=,1categ_id,=,1",
        ]);
    });

    QUnit.test(
        "clicking on an aggregate with domain excluding all records for another an aggregate does not cause a crash with formulas",
        async function (assert) {
            assert.expect(12);

            serverData.models.test_report.fields.untaxed_2 = {
                string: "Untaxed_2",
                type: "float",
                store: true,
                sortable: true,
            };
            serverData.models.test_report.records.forEach((record) => (record.untaxed_2 = 3.1415));

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <aggregate name="untaxed" field="untaxed" domain="[('categ_id', '=', 2)]"/>
                        <aggregate name="untaxed_2" field="untaxed_2" domain="[('categ_id', '=', 1)]"/>
                        <formula name="formula" value="1 / record.untaxed_2"/>
                        <formula name="formula_2" value="record.untaxed_2 / record.untaxed_2"/>
                    </dashboard>
                `,
                mockRPC(route, args) {
                    if (args.method === "read_group") {
                        assert.step(args.kwargs.fields[0]);
                        assert.step(args.kwargs.domain.join(""));
                    }
                },
            });

            // click on the 'untaxed' field: we should see zeros displayed as values
            await click(dashboard.el.querySelector(".o_aggregate[name=untaxed]"));
            assert.strictEqual(
                dashboard.el
                    .querySelector('.o_aggregate[name="untaxed_2"] > .o_value')
                    .textContent.trim(),
                "0.00",
                "should display zero as no record satisfies constrains"
            );
            assert.strictEqual(
                dashboard.el
                    .querySelector('.o_formula[name="formula"] > .o_value')
                    .textContent.trim(),
                "-",
                "Should display '-'"
            );
            assert.strictEqual(
                dashboard.el
                    .querySelector('.o_formula[name="formula_2"] > .o_value')
                    .textContent.trim(),
                "-",
                "Should display '-'"
            );

            assert.verifySteps([
                "untaxed:sum(untaxed)",
                "categ_id,=,2",
                "untaxed_2:sum(untaxed_2)",
                "categ_id,=,1",
                "untaxed:sum(untaxed)",
                "&categ_id,=,2categ_id,=,2",
                "untaxed_2:sum(untaxed_2)",
                "&categ_id,=,1categ_id,=,2",
            ]);
        }
    );

    QUnit.test("open a graph view fullscreen", async function (assert) {
        assert.expect(9);
        const views = {
            "test_report,false,dashboard": `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>
            `,
            "test_report,some_xmlid,graph": `
                <graph>
                    <field name="categ_id"/>
                    <field name="sold" type="measure"/>
                </graph>
            `,
            "test_report,false,search": `
                <search>
                    <filter name="categ" help="Category 1" domain="[('categ_id', '=', 1)]"/>
                </search>
            `,
        };
        Object.assign(serverData, { views });

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    if (args.kwargs.domain[0]) {
                        assert.step(args.kwargs.domain[0].join(""));
                    } else {
                        assert.step("initial web_read_group");
                    }
                }
            },
        });

        await doAction(webClient, {
            name: "Dashboard",
            res_model: "test_report",
            type: "ir.actions.act_window",
            views: [[false, "dashboard"]],
        });

        assert.strictEqual(
            webClient.el.querySelector(".breadcrumb-item").textContent,
            "Dashboard",
            "'Dashboard' should be displayed in the breadcrumbs"
        );

        // activate 'Category 1' filter
        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, 0);
        assert.deepEqual(getFacetTexts(webClient), ["Category 1"]);

        // open graph in fullscreen
        await click(webClient.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));
        await nextTick();
        assert.strictEqual(
            $(webClient.el).find(".o_control_panel .breadcrumb-item:nth(1)").text(),
            "Graph Analysis",
            "'Graph Analysis' should have been stacked in the breadcrumbs"
        );
        assert.deepEqual(
            getFacetTexts(webClient),
            ["Category 1"],
            "the filter should have been kept"
        );

        // go back using the breadcrumbs
        await click(webClient.el.querySelector(".breadcrumb-item.o_back_button"));
        await nextTick();
        assert.verifySteps([
            "initial web_read_group",
            "categ_id=1", // dashboard view after applying the filter
            "categ_id=1", // graph view opened fullscreen
            "categ_id=1", // dashboard after coming back
        ]);
    });

    QUnit.test("open a cohort view fullscreen", async function (assert) {
        assert.expect(9);

        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";

        const views = {
            "test_report,false,dashboard": `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                </dashboard>
            `,
            "test_report,some_xmlid,cohort": `
                <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>
            `,
            "test_report,false,search": `
                <search>
                    <filter name="categ" help="Category 1" domain="[('categ_id', '=', 1)]"/>
                </search>
            `,
        };
        Object.assign(serverData, { views });

        const webClient = await createWebClient({
            serverData,
            legacyParams: { withLegacyMockServer: true },
            mockRPC(route, args) {
                if (args.method === "get_cohort_data") {
                    if (args.kwargs.domain[0]) {
                        assert.step(args.kwargs.domain[0].join(""));
                    } else {
                        assert.step("initial get_cohort_data");
                    }
                }
            },
        });

        await doAction(webClient, {
            name: "Dashboard",
            res_model: "test_report",
            type: "ir.actions.act_window",
            views: [[false, "dashboard"]],
        });

        assert.strictEqual(
            webClient.el.querySelector(".breadcrumb-item").textContent,
            "Dashboard",
            "'Dashboard' should be displayed in the breadcrumbs"
        );

        // activate 'Category 1' filter
        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, 0);
        assert.deepEqual(getFacetTexts(webClient), ["Category 1"]);

        // open cohort in fullscreen
        await click(webClient.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));
        await nextTick();
        assert.strictEqual(
            $(".o_control_panel .breadcrumb li:nth(1)").text(),
            "Cohort Analysis",
            "'Cohort Analysis' should have been stacked in the breadcrumbs"
        );
        assert.deepEqual(getFacetTexts(webClient), ["Category 1"]);

        // go back using the breadcrumbs
        await click(webClient.el.querySelector(".breadcrumb-item.o_back_button"));
        await nextTick();

        assert.verifySteps([
            "initial get_cohort_data",
            "categ_id=1", // dashboard view after applying the filter
            "categ_id=1", // cohort view opened fullscreen
            "categ_id=1", // dashboard after coming back
        ]);
    });

    QUnit.test("interact with a graph view and open it fullscreen", async function (assert) {
        assert.expect(9);

        let graph = null;
        patchWithCleanup(GraphView.prototype, {
            setup() {
                graph = this;
                this._super();
            },
        });
        let activeMeasure = "sold";
        serverData.views["test_report,false,graph"] = `
            <graph>
                <field name="categ_id"/>
                <field name="sold" type="measure"/>
            </graph>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.fields,
                        ["categ_id", activeMeasure],
                        "should read the correct measure"
                    );
                }
            },
        });
        patchWithCleanup(graph.env.services.action, {
            doAction(action, options) {
                assert.step("doAction");
                assert.step(options.props.state.metaData.groupBy[0].fieldName);
                assert.step(options.props.state.metaData.measure);
                assert.step(options.props.state.metaData.mode);
                const expectedAction = {
                    context: {
                        allowed_company_ids: [1],
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    },
                    domain: [],
                    name: "Graph Analysis",
                    res_model: "test_report",
                    type: "ir.actions.act_window",
                    useSampleModel: false,
                    views: [[false, "graph"]],
                };
                assert.deepEqual(
                    action,
                    expectedAction,
                    "should execute an action with correct params"
                );
            },
        });
        assert.strictEqual(
            graph.model.metaData.mode,
            "bar",
            'should have rendered the graph in "bar" mode'
        );
        // switch to pie mode
        await click(dashboard.el.querySelector("button[data-mode=pie]"));
        assert.strictEqual(
            graph.model.metaData.mode,
            "pie",
            'should have rendered the graph in "pie" mode'
        );

        // select 'untaxed' as measure
        activeMeasure = "untaxed";
        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            ".dropdown-item:contains(Untaxed)",
            "should have 'untaxed' in the list of measures"
        );
        await toggleMenuItem(dashboard, "Untaxed");

        // open graph in fullscreen
        await click(dashboard.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));
        assert.verifySteps(["doAction", "categ_id", "untaxed", "pie"]);
    });

    QUnit.test("interact with a cohort view and open it fullscreen", async function (assert) {
        assert.expect(8);

        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";
        serverData.views["test_report,false,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week" measure="sold"/>
        `;

        let activeMeasure = "sold";
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="cohort"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "get_cohort_data") {
                    assert.deepEqual(
                        args.kwargs.measure,
                        activeMeasure,
                        "should read the correct measure"
                    );
                }
            },
        });

        patchWithCleanup(dashboard.env.services.action, {
            doAction(action, options) {
                assert.step("doAction");
                assert.step(options.props.state.metaData.measure);
                assert.step(options.props.state.metaData.interval);
                const expectedAction = {
                    context: {
                        allowed_company_ids: [1],
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    },
                    domain: [],
                    name: "Cohort Analysis",
                    res_model: "test_report",
                    type: "ir.actions.act_window",
                    useSampleModel: false,
                    views: [[false, "cohort"]],
                };
                assert.deepEqual(
                    action,
                    expectedAction,
                    "should execute an action with correct params"
                );
            },
        });
        // select 'untaxed' as measure
        activeMeasure = "untaxed";
        await toggleMenu(dashboard, "Measures");
        assert.containsOnce(
            dashboard,
            ".dropdown-item:contains(Untaxed)",
            "should have 'untaxed' in the list of measures"
        );
        await toggleMenuItem(dashboard, "Untaxed");

        // open cohort in fullscreen
        await click(dashboard.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));
        assert.verifySteps(["doAction", "untaxed", "week"]);
    });

    QUnit.test(
        "aggregates of type many2one should be measures of subviews",
        async function (assert) {
            assert.expect(5);

            // Define an aggregate on many2one field
            serverData.models.test_report.fields.product_id = {
                string: "Product",
                type: "many2one",
                relation: "product",
                store: true,
                sortable: true,
            };
            serverData.models.product = {
                fields: {
                    name: { string: "Product Name", type: "char" },
                },
                records: [
                    {
                        id: 37,
                        display_name: "xphone",
                    },
                    {
                        id: 41,
                        display_name: "xpad",
                    },
                ],
            };
            serverData.models.test_report.records[0].product_id = 37;
            serverData.models.test_report.records[0].product_id = 41;
            serverData.views = {
                "test_report,false,graph": `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
                "test_report,false,pivot": `
                    <pivot>
                        <field name="sold" type="measure"/>
                    </pivot>
                `,
            };

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <aggregate name="product_id_something" field="product_id"/>
                        <view type="graph"/>
                        <view type="pivot"/>
                    </dashboard>
                `,
            });

            patchWithCleanup(dashboard.env.services.action, {
                doAction(action, options) {
                    assert.step("doAction");
                    assert.deepEqual(
                        options.props.state.metaData.additionalMeasures,
                        ["product_id"],
                        "should have passed additional measures in fullscreen"
                    );
                },
            });

            await toggleMenu(dashboard.el.querySelector(".o_subview[type='graph']"), "Measures");
            assert.containsOnce(
                dashboard,
                ".dropdown-item:contains(Product)",
                "should have 'Product' as a measure in the graph view"
            );

            await toggleMenu(dashboard.el.querySelector(".o_subview[type='pivot']"), "Measures");
            assert.containsOnce(
                dashboard,
                ".dropdown-item:contains(Product)",
                "should have 'Product' as measure in the pivot view"
            );

            // open graph in fullscreen
            click(dashboard.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));

            assert.verifySteps(["doAction"]);
        }
    );

    QUnit.test(
        "interact with subviews, open one fullscreen and come back",
        async function (assert) {
            assert.expect(14);

            const views = {
                "test_report,false,dashboard": `
                    <dashboard>
                        <view type="graph"/>
                        <view type="pivot"/>
                    </dashboard>
                `,
                "test_report,false,graph": `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
                "test_report,false,pivot": `
                    <pivot>
                        <field name="sold" type="measure"/>
                    </pivot>
                `,
                "test_report,false,search": `<search></search>`,
            };
            Object.assign(serverData, { views });

            const webClient = await createWebClient({
                serverData,
                mockRPC(route, args) {
                    if (args.method === "read_group") {
                        for (const i in args.kwargs.fields) {
                            assert.step(args.kwargs.fields[i]);
                        }
                    }
                    if (args.method === "web_read_group") {
                        if (args.kwargs.groupby) {
                            assert.step(args.kwargs.groupby[0]);
                        }
                        assert.step(args.kwargs.fields[1]);
                    }
                },
            });

            await doAction(webClient, {
                name: "Dashboard",
                res_model: "test_report",
                type: "ir.actions.act_window",
                views: [[false, "dashboard"]],
            });

            const graph = webClient.el.querySelector(".o_subview[type='graph']");
            const pivot = webClient.el.querySelector(".o_subview[type='pivot']");
            // select 'untaxed' as measure in graph view
            await toggleMenu(graph, "Measures");
            await toggleMenuItem(graph, "Untaxed");

            // select 'untaxed' as additional measure in pivot view
            await toggleMenu(pivot, "Measures");
            await toggleMenuItem(pivot, "Untaxed");

            // open pivot in fullscreen
            await click(pivot.querySelector(".o-web-dashboard-view-wrapper--switch-button"));

            // go back using the breadcrumbs
            await click(webClient.el.querySelector(".breadcrumb-item.o_back_button"));

            assert.verifySteps([
                // initial read_group
                "categ_id",
                "sold:sum", // graph in dashboard
                "sold:sum", // pivot in dashboard

                // after changing the measure in graph
                "categ_id",
                "untaxed:sum", // graph in dashboard

                // after changing the measures in pivot
                "sold:sum",
                "untaxed:sum", // pivot in dashboard

                // pivot opened fullscreen
                "sold:sum",
                "untaxed:sum",

                // after coming back
                "categ_id",
                "untaxed:sum", // graph in dashboard
                "sold:sum",
                "untaxed:sum", // pivot in dashboard
            ]);
        }
    );

    QUnit.test("open subview fullscreen, update domain and come back", async function (assert) {
        assert.expect(8);

        const views = {
            "test_report,false,dashboard": `
                <dashboard>
                    <view type="graph"/>
                </dashboard>
            `,
            "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                    <field name="sold" type="measure"/>
                </graph>
            `,
            "test_report,false,search": `
                <search>
                    <filter name="sold" help="Sold" domain="[('sold', '=', 10)]"/>
                    <filter name="buy" help="Buy" domain="[('sold', '=', -10)]"/>
                </search>
            `,
        };
        Object.assign(serverData, { views });

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    assert.step(args.kwargs.domain[0] ? args.kwargs.domain[0].join("") : " ");
                }
            },
        });

        await doAction(webClient, {
            name: "Dashboard",
            res_model: "test_report",
            type: "ir.actions.act_window",
            views: [[false, "dashboard"]],
        });

        // open graph in fullscreen
        await click(webClient.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));

        // filter on bar
        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, 0);
        assert.deepEqual(getFacetTexts(webClient), ["Sold"]);

        // go back using the breadcrumbs
        await click(webClient.el.querySelector(".breadcrumb-item.o_back_button"));

        assert.deepEqual(getFacetTexts(webClient), []);

        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, 1);

        assert.verifySteps([
            " ", // graph in dashboard
            " ", // graph full screen
            "sold=10", // graph full screen with first filter applied
            " ", // graph in dashboard after coming back
            "sold=-10", // graph in dashboard with second filter applied
        ]);
    });

    QUnit.test(
        "action domain is kept when going back and forth to fullscreen subview",
        async function (assert) {
            assert.expect(4);

            const views = {
                "test_report,false,dashboard": `
                    <dashboard>
                        <view type="graph"/>
                    </dashboard>
                `,
                "test_report,false,graph": `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
                "test_report,false,search": `<search></search>`,
            };
            Object.assign(serverData, { views });

            const webClient = await createWebClient({
                serverData,
                mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        assert.step(args.kwargs.domain[0].join(""));
                    }
                },
            });

            await doAction(webClient, {
                name: "Dashboard",
                domain: [["categ_id", "=", 1]],
                res_model: "test_report",
                type: "ir.actions.act_window",
                views: [[false, "dashboard"]],
            });

            // open graph in fullscreen
            await click(webClient.el.querySelector(".o-web-dashboard-view-wrapper--switch-button"));

            // go back using the breadcrumbs
            await click(webClient.el.querySelector(".breadcrumb-item.o_back_button"));

            assert.verifySteps([
                "categ_id=1", // First rendering of dashboard view
                "categ_id=1", // Rendering of graph view in full screen
                "categ_id=1", // Second rendering of dashboard view
            ]);
        }
    );

    QUnit.test("getContext correctly returns graph subview context", async function (assert) {
        assert.expect(2);

        const expectedContexts = [
            {
                graph: {
                    graph_mode: "bar",
                    graph_measure: "__count",
                    graph_groupbys: ["categ_id"],
                },
                group_by: [],
            },
            {
                graph: {
                    graph_mode: "line",
                    graph_measure: "sold",
                    graph_groupbys: ["categ_id"],
                },
                group_by: [],
            },
        ];
        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id"/>
            </graph>
        `;
        let serverId = 1;
        const dashboard = await makeView({
            mockRPC: function (_, args) {
                if (args.method === "create_or_replace") {
                    const favorite = args.args[0];
                    assert.deepEqual(favorite.context, expectedContexts.shift());
                    return serverId++;
                }
            },
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                    <dashboard>
                        <view type="graph" ref="some_xmlid"/>
                    </dashboard>
                `,
        });

        await toggleFavoriteMenu(dashboard);
        await toggleSaveFavorite(dashboard);
        await editFavoriteName(dashboard, "First Favorite");
        await saveFavorite(dashboard);

        await toggleMenu(dashboard, "Measures");
        await toggleMenuItem(dashboard, "Sold");
        await click(dashboard.el.querySelector('button[data-mode="line"]'));

        await toggleFavoriteMenu(dashboard);
        await toggleSaveFavorite(dashboard);
        await editFavoriteName(dashboard, "Second Favorite");
        await saveFavorite(dashboard);
    });

    QUnit.test("getContext correctly returns pivot subview context", async function (assert) {
        assert.expect(2);

        serverData.views["test_report,some_xmlid,pivot"] = `
            <pivot>
                <field name="categ_id" type="row"/>
            </pivot>
        `;
        const expectedContexts = [
            {
                group_by: [],
                pivot: {
                    pivot_column_groupby: [],
                    pivot_measures: ["__count"],
                    pivot_row_groupby: ["categ_id"],
                },
            },
            {
                group_by: [],
                pivot: {
                    pivot_column_groupby: ["categ_id"],
                    pivot_measures: ["__count", "sold"],
                    pivot_row_groupby: [],
                },
            },
        ];
        let serverId = 1;
        const dashboard = await makeView({
            mockRPC: function (_, args) {
                if (args.method === "create_or_replace") {
                    const favorite = args.args[0];
                    assert.deepEqual(favorite.context, expectedContexts.shift());
                    return serverId++;
                }
            },
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                    <dashboard>
                        <view type="pivot" ref="some_xmlid"/>
                    </dashboard>
                `,
        });

        await toggleFavoriteMenu(dashboard);
        await toggleSaveFavorite(dashboard);
        await editFavoriteName(dashboard, "First Favorite");
        await saveFavorite(dashboard);

        await toggleMenu(dashboard, "Measures");
        await toggleMenuItem(dashboard, "Sold");
        await click(dashboard.el.querySelector(".o_pivot_flip_button"));

        await toggleFavoriteMenu(dashboard);
        await toggleSaveFavorite(dashboard);
        await editFavoriteName(dashboard, "Second Favorite");
        await saveFavorite(dashboard);
    });

    QUnit.test("getContext correctly returns cohort subview context", async function (assert) {
        assert.expect(2);

        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";

        serverData.views["test_report,some_xmlid,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>
        `;
        const expectedContexts = [
            {
                cohort: {
                    cohort_measure: "__count",
                    cohort_interval: "week",
                },
                group_by: [],
            },
            {
                cohort: {
                    cohort_measure: "sold",
                    cohort_interval: "month",
                },
                group_by: [],
            },
        ];
        let serverId = 1;
        const dashboard = await makeView({
            mockRPC: function (_, args) {
                if (args.method === "create_or_replace") {
                    const favorite = args.args[0];
                    assert.deepEqual(favorite.context, expectedContexts.shift());
                    return serverId++;
                }
            },
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                    <dashboard>
                        <view type="cohort" ref="some_xmlid"/>
                    </dashboard>
                `,
        });

        await toggleFavoriteMenu(dashboard);
        await toggleSaveFavorite(dashboard);
        await editFavoriteName(dashboard, "First Favorite");
        await saveFavorite(dashboard);

        await toggleMenu(dashboard, "Measures");
        await toggleMenuItem(dashboard, "Sold");
        await click(dashboard.el.querySelectorAll(".o_cohort_interval_button")[2]);

        await toggleFavoriteMenu(dashboard);
        await toggleSaveFavorite(dashboard);
        await editFavoriteName(dashboard, "Second Favorite");
        await saveFavorite(dashboard);
    });

    QUnit.test("correctly uses graph_ keys from the context", async function (assert) {
        assert.expect(6);

        let graph = null;
        patchWithCleanup(GraphView.prototype, {
            setup() {
                graph = this;
                this._super();
            },
        });

        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id"/>
                <field name="sold" type="measure"/>
            </graph>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    if (args.kwargs.groupby) {
                        assert.step(args.kwargs.groupby[0]);
                    }
                    assert.step(args.kwargs.fields[1]);
                }
            },
            context: {
                graph: {
                    graph_measure: "untaxed",
                    graph_mode: "line",
                    graph_groupbys: ["categ_id"],
                },
            },
        });

        // check mode
        assert.strictEqual(graph.model.metaData.mode, "line", "should be in line chart mode");
        assert.doesNotHaveClass(
            dashboard.el.querySelector('button[data-mode="bar"]'),
            "active",
            "bar chart button should not be active"
        );
        assert.hasClass(
            dashboard.el.querySelector('button[data-mode="line"]'),
            "active",
            "line chart button should be active"
        );
        assert.verifySteps(["categ_id", "untaxed:sum"], "should fetch data for untaxed");
    });

    QUnit.test("correctly uses pivot_ keys from the context", async function (assert) {
        assert.expect(8);

        serverData.views["test_report,some_xmlid,pivot"] = `
            <pivot>
                <field name="categ_id" type="col"/>
                <field name="untaxed" type="measure"/>
            </pivot>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="pivot" ref="some_xmlid"/>
                </dashboard>
            `,
            context: {
                pivot: {
                    pivot_measures: ["sold"],
                    pivot_column_groupby: ["untaxed"],
                    pivot_row_groupby: ["categ_id"],
                },
            },
        });

        await toggleMenu(dashboard, "Measures");
        assert.ok(isItemSelected(dashboard, "Sold"), "Sold measure should be active in pivot view");

        assert.containsOnce(
            dashboard,
            "thead .o_pivot_header_cell_opened",
            "column: should have one opened header"
        );
        assert.strictEqual(
            dashboard.el.querySelector("thead .o_pivot_header_cell_closed").textContent,
            "10",
            "column: should display one closed header with '10'"
        );
        assert.strictEqual(
            dashboard.el.querySelectorAll("thead .o_pivot_header_cell_closed")[1].textContent,
            "20",
            "column: should display one closed header with '20'"
        );

        assert.containsOnce(
            dashboard,
            "tbody .o_pivot_header_cell_opened",
            "row: should have one opened header"
        );
        assert.strictEqual(
            dashboard.el.querySelector("tbody .o_pivot_header_cell_closed").textContent,
            "First",
            "row: should display one closed header with 'First'"
        );
        assert.strictEqual(
            dashboard.el.querySelectorAll("tbody .o_pivot_header_cell_closed")[1].textContent,
            "Second",
            "row: should display one closed header with 'Second'"
        );

        assert.strictEqual(
            dashboard.el.querySelectorAll("tbody tr td")[2].textContent,
            "8.00",
            "selected measure should be 'Sold', with total 8"
        );
    });

    QUnit.test("correctly uses cohort_ keys from the context", async function (assert) {
        assert.expect(2);

        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";

        serverData.views["test_report,some_xmlid,cohort"] = `
            <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "get_cohort_data") {
                    assert.deepEqual(
                        args.kwargs.measure,
                        "untaxed",
                        "should fetch data for untaxed"
                    );
                }
            },
            context: {
                cohort: {
                    cohort_measure: "untaxed",
                    cohort_interval: "year",
                },
            },
        });

        assert.strictEqual(
            dashboard.el.querySelector("button.o_cohort_interval_button.active").textContent,
            "Year",
            "year interval button should be active"
        );
    });

    QUnit.test("correctly uses graph_ keys from the context (at reload)", async function (assert) {
        assert.expect(5);

        serverData.views["test_report,some_xmlid,graph"] = `
            <graph>
                <field name="categ_id"/>
                <field name="sold" type="measure"/>
            </graph>
        `;
        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            irFilters: [
                {
                    user_id: [2, "Mitchell Admin"],
                    name: "My favorite",
                    id: 1,
                    context: `{
                        "graph": {
                            "graph_measure": "untaxed",
                            "graph_mode": "line",
                            "graph_groupbys": ["categ_id"],
                        },
                    }`,
                    sort: "[]",
                    domain: "",
                    is_default: false,
                    model_id: "test_report",
                    action_id: false,
                },
            ],
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    if (args.kwargs.groupby) {
                        assert.step(args.kwargs.groupby[0]);
                    }
                    assert.step(args.kwargs.fields[1]);
                }
            },
        });

        // activate the unique existing favorite
        await toggleFavoriteMenu(dashboard);
        await toggleMenuItem(dashboard, 0);

        assert.verifySteps([
            "categ_id",
            "sold:sum", // first load
            "categ_id",
            "untaxed:sum", // reload
        ]);
    });

    QUnit.test("correctly uses cohort_ keys from the context (at reload)", async function (assert) {
        assert.expect(3);

        serverData.models.test_report.fields.create_date = {
            type: "date",
            string: "Creation Date",
        };
        serverData.models.test_report.fields.transformation_date = {
            type: "date",
            string: "Transormation Date",
        };

        serverData.models.test_report.records[0].create_date = "2018-05-01";
        serverData.models.test_report.records[1].create_date = "2018-05-01";
        serverData.models.test_report.records[0].transformation_date = "2018-07-03";
        serverData.models.test_report.records[1].transformation_date = "2018-06-23";
        serverData.views["test_report,some_xmlid,cohort"] = `
                <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>
            `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                    <dashboard>
                        <view type="cohort" ref="some_xmlid"/>
                    </dashboard>
                `,
            irFilters: [
                {
                    user_id: [2, "Mitchell Admin"],
                    name: "My favorite",
                    id: 1,
                    context: `{
                            "cohort": {
                                "cohort_measure": "untaxed",
                                "cohort_interval": "year",
                            },
                        }`,
                    sort: "[]",
                    domain: "",
                    is_default: false,
                    model_id: "test_report",
                    action_id: false,
                },
            ],
            mockRPC(route, args) {
                if (args.method === "get_cohort_data") {
                    assert.step(args.kwargs.measure);
                }
            },
        });

        // activate the unique existing favorite
        await toggleFavoriteMenu(dashboard);
        await toggleMenuItem(dashboard, 0);

        assert.verifySteps([
            "__count", // first load
            "untaxed", // reload
        ]);
    });

    QUnit.test(
        "changes in search view do not affect measure selection in graph subview",
        async function (assert) {
            assert.expect(2);
            serverData.views = {
                "test_report,some_xmlid,graph": `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
            };
            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <view type="graph" ref="some_xmlid"/>
                    </dashboard>
                `,
                searchViewArch: `
                    <search>
                        <field name="categ_id" string="Label"/>
                        <filter string="categ" name="positive" domain="[('categ_id', '>=', 0)]"/>
                    </search>
                `,
            });

            await toggleMenu(dashboard, "Measures");
            await toggleMenuItem(dashboard, "Untaxed");

            assert.ok(isItemSelected(dashboard, "Untaxed"), "Untaxed should be selected");

            await nextTick();
            await toggleFilterMenu(dashboard);
            await toggleMenuItem(dashboard, 0);

            await toggleMenu(dashboard, "Measures");
            await toggleMenuItem(dashboard, "Untaxed");

            assert.ok(isItemSelected(dashboard, "Untaxed"), "Untaxed should be selected");
        }
    );

    QUnit.test(
        "When there is a measure attribute we use it to filter the graph and pivot",
        async function (assert) {
            assert.expect(2);
            serverData.views = {
                "test_report,false,graph": `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
                "test_report,false,pivot": `
                    <pivot>
                        <field name="categ_id" type="row"/>
                        <field name="sold" type="measure"/>
                    </pivot>
                `,
            };

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <view type="graph"/>
                        <group>
                            <aggregate name="number" field="id" group_operator="count" measure="__count__"/>
                            <aggregate name="untaxed" field="untaxed"/>
                        </group>
                        <view type="pivot"/>
                    </dashboard>
                `,
            });

            // click on aggregate to activate count measure
            await click(dashboard.el.querySelector(".o_aggregate"));

            const graph = dashboard.el.querySelector(".o_subview[type='graph']");
            const pivot = dashboard.el.querySelector(".o_subview[type='pivot']");
            await toggleMenu(graph, "Measures");
            assert.ok(
                isItemSelected(graph, "Count"),
                "count measure should be selected in graph view"
            );

            await toggleMenu(pivot, "Measures");
            assert.ok(
                isItemSelected(pivot, "Count"),
                "count measure should be selected in pivot view"
            );
        }
    );

    QUnit.test(
        "When no measure is given in the aggregate we use the field as measure",
        async function (assert) {
            assert.expect(3);

            serverData.views = {
                "test_report,false,graph": `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
                "test_report,false,pivot": `
                    <pivot>
                        <field name="categ_id" type="row"/>
                        <field name="sold" type="measure"/>
                    </pivot>
                `,
            };

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <view type="graph"/>
                        <group>
                            <aggregate name="number" field="id" group_operator="count" measure="__count__"/>
                            <aggregate name="untaxed" field="untaxed"/>
                        </group>
                        <view type="pivot"/>
                    </dashboard>
                `,
            });

            await toggleMenu(dashboard.el.querySelector(".o_subview[type='graph']"), "Measures");
            assert.ok(isItemSelected(dashboard, "Sold"));

            // click on aggregate to activate untaxed measure
            await click(dashboard.el.querySelectorAll(".o_aggregate")[1].querySelector(".o_value"));
            await toggleMenu(dashboard.el.querySelector(".o_subview[type='graph']"), "Measures");
            assert.ok(isItemSelected(dashboard, "Untaxed"));

            await toggleMenu(dashboard.el.querySelector(".o_subview[type='pivot']"), "Measures");
            assert.ok(isItemSelected(dashboard, "Untaxed"));
        }
    );

    QUnit.test(
        "changes in search view do not affect measure selection in cohort subview",
        async function (assert) {
            assert.expect(2);

            serverData.models.test_report.fields.create_date = {
                type: "date",
                string: "Creation Date",
            };
            serverData.models.test_report.fields.transformation_date = {
                type: "date",
                string: "Transormation Date",
            };

            serverData.models.test_report.records[0].create_date = "2018-05-01";
            serverData.models.test_report.records[1].create_date = "2018-05-01";
            serverData.models.test_report.records[0].transformation_date = "2018-07-03";
            serverData.models.test_report.records[1].transformation_date = "2018-06-23";
            serverData.views["test_report,some_xmlid,cohort"] = `
                    <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>
            `;

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <view type="cohort" ref="some_xmlid"/>
                    </dashboard>
                `,
                searchViewArch: `
                    <search>
                        <field name="categ_id" string="Label"/>
                        <filter string="categ" name="positive" domain="[('categ_id', '>=', 0)]"/>
                    </search>
                `,
            });

            await toggleMenu(dashboard, "Measures");
            await toggleMenuItem(dashboard, "Untaxed");

            assert.ok(isItemSelected(dashboard, "Untaxed"), "Untaxed should be selected");

            await nextTick();
            await toggleFilterMenu(dashboard);
            await toggleMenuItem(dashboard, 0);

            await toggleMenu(dashboard, "Measures");
            await toggleMenuItem(dashboard, "Untaxed");

            assert.ok(isItemSelected(dashboard, "Untaxed"), "Untaxed should be selected");
        }
    );

    QUnit.test("render aggregate node using clickable attribute", async function (assert) {
        assert.expect(5);

        serverData.views = {
            "test_report,xml_id,graph": `
                <graph>
                    <field name="categ_id"/>
                    <field name="sold" type="measure"/>
                </graph>
            `,
        };

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="xml_id"/>
                    <group>
                        <aggregate name="a" field="categ_id"/>
                        <aggregate name="b" field="sold" clickable="true"/>
                        <aggregate name="c" field="untaxed" clickable="false"/>
                    </group>
                </dashboard>
            `,
        });

        assert.hasClass(
            dashboard.el.querySelector('div[name="a"]'),
            "o_clickable",
            "By default aggregate should be clickable"
        );
        assert.hasClass(
            dashboard.el.querySelector('div[name="b"]'),
            "o_clickable",
            "Clickable = true aggregate should be clickable"
        );
        assert.doesNotHaveClass(
            dashboard.el.querySelector('div[name="c"]'),
            "o_clickable",
            "Clickable = false aggregate should not be clickable"
        );

        await toggleMenu(dashboard, "Measures");
        assert.ok(isItemSelected(dashboard, "Sold"));

        await click(dashboard.el.querySelector('div[name="c"]'));
        await toggleMenu(dashboard, "Measures");
        assert.ok(isItemSelected(dashboard, "Sold"));
    });

    QUnit.test("rendering of aggregate with widget attribute (widget)", async function (assert) {
        assert.expect(3);

        const MyWidget = FieldFloat.extend({
            start: function () {
                this.$el.text("The value is " + this._formatValue(this.value));
            },
        });
        legacyFieldRegistry.add("test", MyWidget);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <aggregate name="some_value" field="sold" widget="test"/>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return Promise.resolve([{ some_value: 8 }]);
                }
            },
        });

        await legacyExtraNextTick();
        assert.containsOnce(dashboard, ".o_value");
        assert.isVisible(dashboard.el.querySelector(".o_value"));
        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent,
            "The value is 8.00",
            "should have used the specified widget (as there is no 'test' formatter)"
        );

        delete legacyFieldRegistry.map.test;
    });

    QUnit.test(
        "rendering of aggregate with widget attribute (widget legacy) and comparison active",
        async function (assert) {
            assert.expect(16);

            const MyWidget = FieldFloat.extend({
                start: function () {
                    this.$el.text("The value is " + this._formatValue(this.value));
                },
            });
            legacyFieldRegistry.add("test", MyWidget);

            let nbReadGroup = 0;

            patchWithCleanup(MockServer.prototype, {
                async mockReadGroup(model, kwargs) {
                    const result = await this._super(...arguments);
                    nbReadGroup++;
                    if (nbReadGroup === 1) {
                        assert.deepEqual(
                            kwargs.fields,
                            ["some_value:sum(sold)"],
                            "should read the correct field"
                        );
                        assert.deepEqual(kwargs.domain, [], "should send the correct domain");
                        assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
                        result[0].some_value = 8;
                    }
                    if (nbReadGroup === 2 || nbReadGroup === 3) {
                        assert.deepEqual(
                            kwargs.fields,
                            ["some_value:sum(sold)"],
                            "should read the correct field"
                        );
                        assert.deepEqual(
                            kwargs.domain,
                            ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
                            "should send the correct domain"
                        );
                        assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
                        result[0].some_value = 16;
                    }
                    if (nbReadGroup === 4) {
                        assert.deepEqual(
                            kwargs.fields,
                            ["some_value:sum(sold)"],
                            "should read the correct field"
                        );
                        assert.deepEqual(
                            kwargs.domain,
                            ["&", ["date", ">=", "2017-02-01"], ["date", "<=", "2017-02-28"]],
                            "should send the correct domain"
                        );
                        assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
                        result[0].some_value = 4;
                    }
                    return result;
                },
            });

            patchDate(2017, 2, 22, 1, 0, 0);

            const searchViewArch = `
                <search>
                    <filter name="date" date="date" string="Date"/>
                </search>
            `;

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_time_range",
                serverData,
                arch: `
                    <dashboard>
                        <aggregate name="some_value" field="sold" string="Some Value" widget="test"/>
                    </dashboard>
                `,
                searchViewArch,
            });

            assert.containsOnce(dashboard, ".o_aggregate .o_value");

            // Apply time range with today
            await toggleFilterMenu(dashboard);
            await toggleMenuItem(dashboard, "Date");
            await toggleMenuItemOption(dashboard, "Date", "March");
            assert.containsOnce(dashboard, ".o_aggregate .o_value");

            // Apply range with today and comparison with previous period
            await toggleComparisonMenu(dashboard);
            await toggleMenuItem(dashboard, "Date: Previous period");
            assert.strictEqual(
                dashboard.el.querySelector(".o_aggregate .o_variation").textContent,
                "300%"
            );
            assert.strictEqual(
                dashboard.el.querySelector(".o_aggregate .o_comparison").textContent,
                "The value is 16.00 vs The value is 4.00"
            );

            delete legacyFieldRegistry.map.test;
        }
    );

    QUnit.test("rendering of a cohort tag with comparison active", async function (assert) {
        assert.expect(1);

        patchDate(2016, 11, 20, 1, 0, 0);

        serverData.views = {
            "test_time_range,some_xmlid,cohort": `
                <cohort string="Cohort" date_start="date" date_stop="transformation_date" interval="week"/>
            `,
        };

        const searchViewArch = `<search>
                <filter name="date" date="date" string="Date"/>
            </search>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                </dashboard>
            `,
            searchViewArch,
        });

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "Date");
        await toggleMenuItemOption(dashboard, "Date", "October");

        await toggleComparisonMenu(dashboard);
        await toggleMenuItem(dashboard, "Date: Previous period");

        assert.containsOnce(dashboard, ".o_cohort_view div.o_view_nocontent");
    });

    QUnit.test("rendering of an aggregate with comparison active", async function (assert) {
        assert.expect(27);

        let nbReadGroup = 0;

        patchDate(2017, 2, 22, 1, 0, 0);

        const searchViewArch = `<search>
                <filter name="date" date="date" string="Date"/>
            </search>
        `;

        function assertReadGroupDomain(kwargs, expectedDomain) {
            assert.deepEqual(
                kwargs.fields,
                ["some_value:sum(sold)"],
                "should read the correct field"
            );
            assert.deepEqual(kwargs.domain, expectedDomain, "should send the correct domain");
            assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
        }

        patchWithCleanup(MockServer.prototype, {
            async mockReadGroup(model, kwargs) {
                const result = await this._super(...arguments);

                nbReadGroup++;
                if (nbReadGroup === 1) {
                    assertReadGroupDomain(kwargs, []);
                    result[0].some_value = 8;
                }
                if (nbReadGroup === 2 || nbReadGroup === 3) {
                    assertReadGroupDomain(kwargs, [
                        "&",
                        ["date", ">=", "2017-03-01"],
                        ["date", "<=", "2017-03-31"],
                    ]);
                    result[0].some_value = 16;
                }
                if (nbReadGroup === 4) {
                    assertReadGroupDomain(kwargs, [
                        "&",
                        ["date", ">=", "2017-02-01"],
                        ["date", "<=", "2017-02-28"],
                    ]);
                    result[0].some_value = 4;
                }
                if (nbReadGroup === 5) {
                    assertReadGroupDomain(kwargs, [
                        "&",
                        ["date", ">=", "2017-03-01"],
                        ["date", "<=", "2017-03-31"],
                    ]);
                    result[0].some_value = 4;
                }
                if (nbReadGroup === 6) {
                    assertReadGroupDomain(
                        kwargs,
                        ["&", ["date", ">=", "2016-03-01"], ["date", "<=", "2016-03-31"]],
                        16
                    );
                    result[0].some_value = 16;
                }
                return result;
            },
        });

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="some_value" field="sold" string="Some Value"/>
                    </group>
                </dashboard>
            `,
            searchViewArch,
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_value").textContent.trim(),
            "8.00"
        );

        // Apply time range with today
        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "Date");
        await toggleMenuItemOption(dashboard, "Date", "March");

        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_value").textContent.trim(),
            "16.00"
        );
        assert.containsOnce(dashboard, ".o_aggregate .o_value");

        // Apply range with this month and comparison with previous period
        await toggleComparisonMenu(dashboard);
        await toggleMenuItem(dashboard, "Date: Previous period");

        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_variation").textContent,
            "300%"
        );
        assert.hasClass(dashboard.el.querySelector(".o_aggregate"), "border-success");
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_comparison").textContent.trim(),
            "16.00 vs 4.00"
        );

        // Apply range with this month and comparison with last year
        await toggleMenuItem(dashboard, "Date: Previous year");
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_variation").textContent,
            "-75%"
        );
        assert.hasClass(dashboard.el.querySelector(".o_aggregate"), "border-danger");
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_comparison").textContent.trim(),
            "4.00 vs 16.00"
        );
    });

    QUnit.test("basic rendering of aggregates with big values", async function (assert) {
        assert.expect(12);

        patchWithCleanup(session, {
            companies_currency_id: {
                1: 11,
            },
            currencies: {
                11: {
                    digits: [69, 2],
                    position: "before",
                    symbol: "",
                },
            },
        });

        let readGroupNo = -3;
        const results = [
            "0.02",
            "0.15",
            "1.52",
            "15.23",
            "152.35",
            "1.52k",
            "15.23k",
            "152.35k",
            "1.52M",
            "15.23M",
            "152.35M",
            "1.52G",
        ];

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold" field="sold" widget="monetary"/>
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    readGroupNo++;
                    return Promise.resolve([{ sold: Math.pow(10, readGroupNo) * 1.52346 }]);
                }
            },
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent.trim(),
            results.shift(),
            "should correctly display the aggregate's value"
        );

        for (let i = 0; i < 11; i++) {
            await validateSearch(dashboard);
            assert.strictEqual(
                dashboard.el.querySelector(".o_value").textContent.trim(),
                results.shift(),
                "should correctly display the aggregate's value"
            );
        }
    });

    QUnit.test("basic rendering of a date aggregate and empty result set", async function (assert) {
        assert.expect(1);

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="date_max" field="date" group_operator="max" />
                    </group>
                </dashboard>
            `,
            mockRPC(route, args) {
                if (args.method === "read_group") {
                    return [{ date_max: null, __count: 0 }];
                }
            },
        });

        assert.strictEqual(
            dashboard.el.querySelector(".o_value").textContent.trim(),
            "-",
            "should correctly display the aggregate's value"
        );
    });

    QUnit.test(
        "basic rendering of a many2one aggregate with empty result set",
        async function (assert) {
            assert.expect(3);

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_time_range",
                serverData,
                arch: `
                <dashboard>
                    <group>
                        <aggregate name="category_count" field="categ_id" help="some help" />
                    </group>
                </dashboard>
            `,
                mockRPC(route, args) {
                    if (args.method === "read_group") {
                        return [{ category_count: 0, __count: 0 }];
                    }
                },
            });

            assert.strictEqual(
                dashboard.el.querySelector(".o_value").textContent.trim(),
                "0",
                "should correctly display the aggregate's value"
            );

            const agg = dashboard.el.querySelector(".o_aggregate");
            const tooltipInfo = JSON.parse(agg.dataset.tooltipInfo);
            assert.strictEqual(serverData.models.test_time_range.fields.categ_id.type, "many2one");
            assert.strictEqual(tooltipInfo.formatter, "integer");
        }
    );

    QUnit.test(
        "click on a non empty cell in an embedded pivot view redirects to a list view",
        async function (assert) {
            assert.expect(3);

            serverData.views = {
                "test_report,some_xmlid,pivot": `
                    <pivot>
                        <field name="sold" type="measure"/>
                    </pivot>
                `,
                "test_report,false,form": `
                    <form>
                        <field name="sold"/>
                    </form>
                `,
                "test_report,false,list": `
                    <list>
                        <field name="sold"/>
                    </list>
                `,
            };

            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    function doAction(action) {
                        assert.step("do_action");
                        assert.deepEqual(action, {
                            type: "ir.actions.act_window",
                            name: "Untitled",
                            res_model: "test_report",
                            views: [
                                [false, "list"],
                                [false, "form"],
                            ],
                            view_mode: "list",
                            target: "current",
                            context: {
                                allowed_company_ids: [1],
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            domain: [],
                        });
                    }
                    return Object.assign({}, actionMain, { doAction });
                },
            };

            serviceRegistry.add("action", fakeActionService, { force: true });

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_report",
                serverData,
                arch: `
                    <dashboard>
                        <view type="pivot" ref="some_xmlid"/>
                    </dashboard>
                `,
            });

            // Click on the unique pivot cell
            await click(dashboard.el.querySelector(".o_pivot .o_pivot_cell_value"));

            // There should a unique do_action triggered.
            assert.verifySteps(["do_action"]);
        }
    );

    QUnit.test(
        "groupby selected within graph subview are not deleted when modifying search view content",
        async function (assert) {
            assert.expect(2);

            serverData.views = {
                "test_time_range,some_xmlid,graph": `
                    <graph>
                        <field name="transformation_date" type="row" interval="day"/>
                        <field name="sold" type="measure"/>
                    </graph>
                `,
            };

            const searchViewArch = `
                <search>
                    <filter string="float" name="positive" domain="[['sold', '>=', 2]]"/>
                    <filter name="categ_id" context="{'group_by' : 'categ_id'}"/>
                </search>
            `;

            const dashboard = await makeView({
                type: "dashboard",
                resModel: "test_time_range",
                serverData,
                arch: `
                    <dashboard>
                        <view type="graph" ref="some_xmlid"/>
                    </dashboard>
                `,
                searchViewArch,
            });

            await toggleGroupByMenu(dashboard);

            await toggleMenuItem(dashboard, "categ_id");
            assert.ok(isItemSelected(dashboard, "categ_id"));

            await toggleFilterMenu(dashboard);
            await toggleMenuItem(dashboard, "float");

            await toggleGroupByMenu(dashboard);
            assert.ok(isItemSelected(dashboard, "categ_id"));
        }
    );

    QUnit.test('groupbys in "Group By" menu of graph subviews', async function (assert) {
        assert.expect(16);

        serverData.models.test_time_range.fields.categ_id.store = true;
        serverData.models.test_time_range.fields.categ_id.sortable = true;

        const groupBys = [
            [],
            ["categ_id"],
            ["categ_id", "date:day"],
            ["categ_id", "date:day"], //graph view keeps only finer option when fetching data
            ["date:day"],
            ["date:quarter"],
        ];

        serverData.views = {
            "test_time_range,some_xmlid,graph": `
                <graph>
                    <field name="sold" type="measure"/>
                </graph>`,
        };

        const searchViewArch = `<search>
            <filter name="categ_id" context="{'group_by' : 'categ_id'}" />
            <filter name="date" context="{'group_by' : 'date'}" />
        </search>`;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>
            `,
            searchViewArch,
            mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    assert.deepEqual(
                        args.kwargs.groupby,
                        groupBys.shift(),
                        "should group by the correct field"
                    );
                }
            },
        });

        assert.containsOnce(
            dashboard,
            '.o_subview .o_group_by_menu:contains("Group By")',
            "graph button should have been rendered"
        );

        await toggleGroupByMenu(dashboard);

        await toggleMenuItem(dashboard, "categ_id");
        assert.ok(isItemSelected(dashboard, "categ_id"));

        await toggleMenuItem(dashboard, "Date");
        assert.notOk(isItemSelected(dashboard, "Date"));

        await toggleMenuItemOption(dashboard, "Date", "Day");
        assert.ok(isItemSelected(dashboard, "Date"));
        assert.ok(isOptionSelected(dashboard, "Date", "Day"));

        await toggleMenuItemOption(dashboard, "Date", "Quarter");
        assert.ok(isOptionSelected(dashboard, "Date", "Day"));
        assert.ok(isOptionSelected(dashboard, "Date", "Quarter"));

        await toggleMenuItem(dashboard, "categ_id");
        await toggleMenuItem(dashboard, "Date"); // re-open the 'Date' section
        assert.notOk(isItemSelected(dashboard, "categ_id"));

        await toggleMenuItemOption(dashboard, "Date", "Day");
        assert.notOk(isOptionSelected(dashboard, "Date", "Day"));
        assert.ok(isOptionSelected(dashboard, "Date", "Quarter"));
    });

    QUnit.test("empty dashboard view with sub views", async function (assert) {
        assert.expect(7);

        serverData.views = {
            "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                </graph>
            `,
            "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                </pivot>
            `,
        };

        const searchViewArch = `
            <search>
                <filter name="noId" domain="[('id', '&lt;', 0)]" />
            </search>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            searchViewArch,
            arch: `
                <dashboard>
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>
            `,
            context: { search_default_noId: 1 },
            noContentHelp: `<p class="abc">click to add a foo</p>`,
        });

        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] .o_view_nocontent");
        assert.containsNone(dashboard, ".o_subview[type=pivot] .o_view_nocontent .abc");
        assert.containsNone(dashboard, ".o_view_nocontent .abc");

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "noId");

        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] table");
        assert.containsNone(dashboard, ".o_view_nocontent .abc");
    });

    QUnit.test("empty dashboard view with sub views and sample data", async function (assert) {
        assert.expect(9);

        serverData.views = {
            "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                </graph>
            `,
            "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                </pivot>
            `,
        };

        const searchViewArch = `
            <search>
                <filter name="noId" domain="[('id', '&lt;', 0)]" />
                <filter name="noId_2" domain="[('id', '&lt;', -10)]" />
            </search>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            searchViewArch,
            arch: `
                <dashboard sample="1">
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>
            `,
            context: { search_default_noId: 1 },
            noContentHelp: `<p class="abc">click to add a foo</p>`,
        });

        assert.hasClass(dashboard.el, "o_view_sample_data");
        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] table");
        assert.containsOnce(dashboard, ".o_view_nocontent .abc");

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "noId");
        await toggleMenuItem(dashboard, "noId_2");

        assert.doesNotHaveClass(dashboard.el, "o_view_sample_data");
        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] .o_view_nocontent");
        assert.containsNone(dashboard, ".o_subview[type=pivot] .o_view_nocontent .abc");
        assert.containsNone(dashboard, ".o_view_nocontent .abc");
    });

    QUnit.test("empty dashboard view with sub views and sample data (2)", async function (assert) {
        serverData.models.test_report.records = [];
        serverData.views = {
            "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                </graph>
            `,
            "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                </pivot>
            `,
        };

        const searchViewArch = `
            <search>
                <filter name="noId" domain="[('id', '&lt;', 0)]" />
            </search>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            searchViewArch,
            arch: `
                <dashboard sample="1">
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>
            `,
            context: { search_default_noId: 1 },
        });

        assert.hasClass(dashboard.el, "o_view_sample_data");
        assert.hasClass(dashboard.el.querySelector(".o_graph_view"), "o_view_sample_data");
        assert.hasClass(dashboard.el.querySelector(".o_pivot_view"), "o_view_sample_data");
        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] table");

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "noId");

        assert.doesNotHaveClass(dashboard.el, "o_view_sample_data");
        assert.doesNotHaveClass(dashboard.el.querySelector(".o_graph_view"), "o_view_sample_data");
        assert.doesNotHaveClass(dashboard.el.querySelector(".o_pivot_view"), "o_view_sample_data");
    });

    QUnit.test("non empty dashboard view with sub views and sample data", async function (assert) {
        assert.expect(9);

        serverData.views = {
            "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                </graph>
            `,
            "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                </pivot>
            `,
        };

        const searchViewArch = `
            <search>
                <filter name="noId" domain="[('id', '&lt;', 0)]" />
            </search>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            searchViewArch,
            arch: `
                <dashboard sample="1">
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>`,
            noContentHelp: `<p class="abc">click to add a foo</p>`,
        });

        assert.doesNotHaveClass(dashboard.el, "o_view_sample_data");
        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] table");
        assert.containsNone(dashboard, ".o_view_nocontent .abc");

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "noId");

        assert.doesNotHaveClass(dashboard.el, "o_view_sample_data");
        assert.containsOnce(dashboard, ".o_subview[type=graph] canvas");
        assert.containsOnce(dashboard, ".o_subview[type=pivot] .o_view_nocontent");
        assert.containsNone(dashboard, ".o_subview[type=pivot] .o_view_nocontent .abc");
        assert.containsNone(dashboard, ".o_view_nocontent .abc");
    });

    QUnit.test(
        "non empty dashboard view with sub views and sample data -- open in fullscreen",
        async function (assert) {
            assert.expect(9);

            serverData.views = {
                "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                </graph>
            `,
                "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                </pivot>
            `,
                "test_report,false,search": `<search>
                <filter name="noId" domain="[('id', '&lt;', 0)]" />
            </search>`,
                "test_report,1,dashboard": `<dashboard sample="1">
                 <view type="graph"/>
                 <view type="pivot"/>
             </dashboard>`,
            };

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                type: "ir.actions.act_window",
                target: "current",
                res_model: "test_report",
                views: [[1, "dashboard"]],
                help: `<p class="abc">click to add a foo</p>`,
            });

            await toggleFilterMenu(webClient.el.querySelector(".o_control_panel"));
            await toggleMenuItem(webClient.el.querySelector(".o_control_panel"), "noId");

            await click(
                webClient.el.querySelector(
                    ".o_subview[type='pivot'] .o-web-dashboard-view-wrapper--switch-button"
                )
            );
            assert.containsOnce(webClient, ".o_action");
            assert.containsNone(webClient, ".o_dashboard_view");
            assert.containsOnce(webClient, ".o_pivot_view ");
            assert.containsOnce(webClient, ".o_view_nocontent_empty_folder");

            await click(webClient.el.querySelector(".breadcrumb-item.o_back_button"));
            assert.containsOnce(webClient, ".o_dashboard_view");
            assert.containsOnce(webClient, ".o_subview[type=graph] canvas");
            assert.containsOnce(webClient, ".o_subview[type=pivot] .o_view_nocontent");
            assert.containsNone(webClient, ".o_subview[type=pivot] .o_view_nocontent .abc");
            assert.containsNone(webClient, ".o_view_nocontent .abc");
        }
    );

    QUnit.test(
        "non empty dashboard view with sub views and sample data -- switch view and back",
        async function (assert) {
            assert.expect(32);

            serverData.views = {
                "test_report,false,graph": `
                <graph>
                    <field name="categ_id"/>
                </graph>
            `,
                "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                </pivot>
            `,
                "test_report,false,search": `<search>
                <filter name="noId" domain="[('id', '&lt;', 0)]" />
            </search>`,
                "test_report,1,dashboard": `<dashboard sample="1">
                 <view type="graph"/>
                 <view type="pivot"/>
             </dashboard>`,
            };

            const readGroupDomains = [
                [],
                [],
                [],
                [], // End load dashboard
                [["id", "<", 0]],
                [["id", "<", 0]], // End reload with domain
                [["id", "<", 0]], // End load graph
                [], // end load graph without domain
                [],
                [],
                [], // end load dashboard
            ];

            const mockRPC = (route, args) => {
                const method = args.method;
                if (method && method.includes("read_group")) {
                    assert.step(args.method);
                    assert.deepEqual(args.kwargs.domain, readGroupDomains.shift());
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, {
                type: "ir.actions.act_window",
                target: "current",
                res_model: "test_report",
                views: [
                    [1, "dashboard"],
                    [2, "graph"],
                ],
                help: `<p class="abc">click to add a foo</p>`,
            });

            assert.verifySteps(["read_group", "web_read_group", "read_group", "read_group"]); // dashboard, graph, pivotx2

            await toggleFilterMenu(webClient.el.querySelector(".o_control_panel"));
            await toggleMenuItem(webClient.el.querySelector(".o_control_panel"), "noId");
            assert.verifySteps(["web_read_group", "read_group"]); //  graph, pivot

            await click(webClient.el.querySelector(".o_cp_switch_buttons .o_graph"));
            assert.verifySteps(["web_read_group"]);
            await toggleFilterMenu(webClient.el.querySelector(".o_control_panel"));
            await toggleMenuItem(webClient.el.querySelector(".o_control_panel"), "noId");
            assert.verifySteps(["web_read_group"]);

            await click(webClient.el.querySelector(".o_cp_switch_buttons .o_dashboard"));
            assert.verifySteps(["web_read_group", "read_group", "read_group"]); // graph, pivotx2
            assert.containsOnce(webClient, ".o_dashboard_view");
            assert.containsOnce(webClient, ".o_subview[type=graph] canvas");
            assert.containsNone(webClient, ".o_subview[type=pivot] .o_view_nocontent");
            assert.containsNone(webClient, ".o_subview[type=pivot] .o_view_nocontent .abc");
            assert.containsNone(webClient, ".o_view_nocontent .abc");
        }
    );

    QUnit.test("dashboard statistic support wowl field", async (assert) => {
        assert.expect(5);

        class CustomField extends owl.Component {
            setup() {
                assert.ok(this.props.model instanceof DashboardModel);
                assert.ok("record" in this.props);
                assert.strictEqual(this.props.name, "sold");
                assert.strictEqual(this.props.type, "custom");
                assert.strictEqual(this.props.record.data[this.props.name], 8);
            }
        }
        CustomField.template = owl.tags.xml`<div />`;

        registry.category("fields").add("custom", CustomField);

        await makeView({
            type: "dashboard",
            resModel: "test_report",
            serverData,
            arch: `
                <dashboard>
                    <aggregate name="sold" field="sold" widget="custom"/>
                </dashboard>`,
        });
    });

    QUnit.test("dashboard statistic support wowl field with comparison", async (assert) => {
        assert.expect(31);

        const expectedFieldValues = [8, 16, 4];
        class CustomField extends owl.Component {
            setup() {
                assert.ok(this.props.model instanceof DashboardModel);
                assert.ok("record" in this.props);
                assert.strictEqual(this.props.name, "some_value");
                assert.strictEqual(this.props.type, "custom");
                assert.strictEqual(
                    this.props.record.data[this.props.name],
                    expectedFieldValues.shift()
                );
            }
        }
        CustomField.template = owl.tags
            .xml`<div>The value is <t t-esc="props.record.data[props.name]"/></div>`;

        registry.category("fields").add("custom", CustomField);

        patchDate(2017, 2, 22, 1, 0, 0);
        let nbReadGroup = 0;

        patchWithCleanup(MockServer.prototype, {
            async mockReadGroup(model, kwargs) {
                const result = await this._super(...arguments);
                nbReadGroup++;
                if (nbReadGroup === 1) {
                    assert.deepEqual(
                        kwargs.fields,
                        ["some_value:sum(sold)"],
                        "should read the correct field"
                    );
                    assert.deepEqual(kwargs.domain, [], "should send the correct domain");
                    assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
                    result[0].some_value = 8;
                }
                if (nbReadGroup === 2 || nbReadGroup === 3) {
                    assert.deepEqual(
                        kwargs.fields,
                        ["some_value:sum(sold)"],
                        "should read the correct field"
                    );
                    assert.deepEqual(
                        kwargs.domain,
                        ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
                        "should send the correct domain"
                    );
                    assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
                    result[0].some_value = 16;
                }
                if (nbReadGroup === 4) {
                    assert.deepEqual(
                        kwargs.fields,
                        ["some_value:sum(sold)"],
                        "should read the correct field"
                    );
                    assert.deepEqual(
                        kwargs.domain,
                        ["&", ["date", ">=", "2017-02-01"], ["date", "<=", "2017-02-28"]],
                        "should send the correct domain"
                    );
                    assert.deepEqual(kwargs.groupby, [], "should send the correct groupby");
                    result[0].some_value = 4;
                }
                return result;
            },
        });

        const searchViewArch = `
            <search>
                <filter name="date" date="date" string="Date"/>
            </search>
        `;

        const dashboard = await makeView({
            type: "dashboard",
            resModel: "test_time_range",
            serverData,
            searchViewArch,
            arch: `
                <dashboard>
                    <aggregate name="some_value" field="sold" string="Some Value" widget="custom"/>
                </dashboard>`,
        });

        assert.containsOnce(dashboard, ".o_aggregate .o_value");

        // Apply time range with today
        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "Date");
        await toggleMenuItemOption(dashboard, "Date", "March");
        assert.containsOnce(dashboard, ".o_aggregate .o_value");

        // Apply range with today and comparison with previous period
        await toggleComparisonMenu(dashboard);
        await toggleMenuItem(dashboard, "Date: Previous period");
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_variation").textContent,
            "300%"
        );
        assert.strictEqual(
            dashboard.el.querySelector(".o_aggregate .o_comparison").textContent,
            "The value is 16 vs The value is 4"
        );
    });

    QUnit.test("sub views do not use dashboard search_defaults", async function (assert) {
        serverData.views = {
            "test_report,false,legacy_toy": `<legacy_toy/>`,
            "test_report,false,dashboard": `
                <dashboard>
                    <view type="pivot"/>
                </dashboard>
            `,
            "test_report,false,pivot": `
                <pivot/>
            `,
            "test_report,false,search": `
                <search>
                    <filter name="noId" string="Filter" domain="[('0', '=', 1)]" />
                </search>
            `,
        };

        const LegacyToyView = AbstractView.extend({
            display_name: "Legacy toy view",
            icon: "fa fa-bars",
            multiRecord: true,
            viewType: "legacy_toy",
            searchMenuTypes: [],
        });

        legacyViewRegistry.add("legacy_toy", LegacyToyView);

        const target = getFixture();

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            name: "Dashboard",
            res_model: "test_report",
            type: "ir.actions.act_window",
            views: [[false, "legacy_toy"], [false, "dashboard"], [false, "search"]],
            context: { search_default_noId: 1 },
        });

        assert.deepEqual(getFacetTexts(target), ["Filter"]);

        await switchView(target, "dashboard");

        assert.deepEqual(getFacetTexts(target), ["Filter"]);
        assert.containsOnce(target, ".o_pivot_view .o_nocontent_help");
        assert.containsNone(target, ".o_pivot_view table");

        await removeFacet(target);

        assert.deepEqual(getFacetTexts(target), []);
        assert.containsNone(target, ".o_pivot_view .o_nocontent_help");
        assert.containsOnce(target, ".o_pivot_view table");
    });

    QUnit.test(
        "the group by menu button of a graph sub view should have the same style as other buttons",
        async function (assert) {
            serverData.views = {
                "test_report,false,graph": `
                  <graph/>
                `,
            };

            const dashboard = await makeView({
                serverData,
                type: "dashboard",
                resModel: "test_report",
                arch: `
                    <dashboard>
                        <view type="graph"/>
                    </dashboard>
                `,
            });

            const groupByMenuButton = dashboard.el.querySelector(".o_group_by_menu button");

            assert.hasClass(groupByMenuButton, "btn-outline-secondary");
            assert.doesNotHaveClass(groupByMenuButton, "btn-light");
        }
    );

    QUnit.test("keep states of sub views after update of props", async function (assert) {
        serverData.views = {
            "test_report,false,pivot": `
                <pivot>
                    <field name="categ_id" type="row"/>
                    <field name="sold" type="measure"/>
                </pivot>
            `,
        };

        const dashboard = await makeView({
            serverData,
            type: "dashboard",
            resModel: "test_report",
            arch: `
                <dashboard>
                    <view type="pivot"/>
                </dashboard>
            `,
            searchViewArch: `
                <search>
                    <filter name="noId" string="Filter" domain="[(1, '=', 1)]" />
                </search>
            `,
        });

        assert.deepEqual(
            [...dashboard.el.querySelectorAll(".o_pivot_cell_value div")].map(
                (el) => el.innerText
            ),
            ["8.00", "5.00", "3.00"]
        )

        await click(dashboard.el, ".o_pivot_flip_button");

        assert.deepEqual(
            [...dashboard.el.querySelectorAll(".o_pivot_cell_value div")].map(
                (el) => el.innerText
            ),
            ["5.00", "3.00", "8.00"]
        )

        await toggleFilterMenu(dashboard);
        await toggleMenuItem(dashboard, "Filter");

        assert.deepEqual(
            [...dashboard.el.querySelectorAll(".o_pivot_cell_value div")].map(
                (el) => el.innerText
            ),
            ["5.00", "3.00", "8.00"]
        )
    });
});
