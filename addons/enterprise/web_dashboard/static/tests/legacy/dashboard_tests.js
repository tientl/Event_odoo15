odoo.define('web_dashboard.dashboard_tests', function (require) {
    "use strict";

var BasicFields = require('web.basic_fields');
const { createWebClient, doAction } = require("@web/../tests/webclient/helpers");
var DashboardView = require('web_dashboard.DashboardView');
var fieldRegistry = require('web.field_registry');
var GraphView = require('web.GraphView');
var PivotView = require('web.PivotView');
const legacyViewRegistry = require("web.view_registry");
const { registry } = require("@web/core/registry");
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');
const { legacyExtraNextTick, click, patchWithCleanup } = require("@web/../tests/helpers/utils");
const { browser } = require('@web/core/browser/browser');
const CohortView = require('web_cohort.CohortView');

const {
    getFacetTexts,
    toggleAddCustomFilter,
    toggleComparisonMenu,
    toggleFilterMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} = require("@web/../tests/search/helpers");

const viewRegistry = registry.category("views");

const { createView, nextTick, controlPanel: cpHelpers } = testUtils;
var patchDate = testUtils.mock.patchDate;

var FieldFloat = BasicFields.FieldFloat;

let serverData;
QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            test_report: {
                fields: {
                    categ_id: {string: "categ_id", type: 'many2one', relation: 'test_report', store: true},
                    sold: {string: "Sold", type: 'float', store: true, group_operator: 'sum'},
                    untaxed: {string: "Untaxed", type: 'float', group_operator: 'sum', store: true},
                },
                records: [{
                    display_name: "First",
                    id: 1,
                    sold: 5,
                    untaxed: 10,
                    categ_id: 1,
                }, {
                    display_name: "Second",
                    id: 2,
                    sold: 3,
                    untaxed: 20,
                    categ_id: 2,
                }],
            },
            test_time_range: {
                fields: {
                    categ_id: {string: "categ_id", type: 'many2one', relation: 'test_report'},
                    sold: {string: "Sold", type: 'float', store: true, group_operator: 'sum'},
                    untaxed: {string: "Untaxed", type: 'float', group_operator: 'sum', store: true},
                    date: {string: "Date", type: 'date', store: true, sortable: true},
                    transformation_date: {string: "Transformation Date", type: 'datetime', store: true, sortable: true},
                },
                records: [{
                    display_name: "First",
                    id: 1,
                    sold: 5,
                    untaxed: 10,
                    categ_id: 1,
                    date: '1983-07-15',
                    transformation_date: '2018-07-30 04:56:00'
                }, {
                    display_name: "Second",
                    id: 2,
                    sold: 3,
                    untaxed: 20,
                    categ_id: 2,
                    date: '1984-12-15',
                    transformation_date: '2018-12-15 14:07:03'
                }],
            },
        };
        serverData = { models: this.data };
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
    }
}, function () {

    QUnit.module('DashboardView (legacy)');

    QUnit.test('basic rendering of a dashboard with groups', async function (assert) {
        assert.expect(3);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<group></group>' +
                        '</group>' +
                    '</dashboard>',
        });
        await testUtils.nextTick();
        await testUtils.nextTick();
        assert.containsOnce(dashboard, '.o_legacy_dashboard_view',
            "root has a child with 'o_legacy_dashboard_view' class");
        assert.containsN(dashboard, '.o_group', 2,
            "should have rendered two groups");
        assert.hasClass(dashboard.$('.o_group .o_group'), 'o_group_col_2',
            "inner group should have className o_group_col_2");

        dashboard.destroy();
    });

    QUnit.test('basic rendering of a widget tag', async function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
                this._super.apply(this, arguments);
            },
            start: function () {
                this.$el.text(JSON.stringify(this.data));
            },
        });
        widgetRegistry.add('test', MyWidget);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<widget name="test"/>' +
                    '</dashboard>',
        });

        assert.containsOnce(dashboard, '.o_widget',
            "there should be a node with widget class");

        dashboard.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('basic rendering of a pie chart widget', async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        assert.expect(7);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                      '<widget name="pie_chart" title="Products sold" attrs="{\'measure\': \'sold\', \'groupby\': \'categ_id\'}"/>' +
                  '</dashboard>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/test_report/read_group') {
                    assert.deepEqual(args.args, []);
                    assert.deepEqual(args.model, "test_report");
                    assert.deepEqual(args.method, "read_group");
                    assert.deepEqual(args.kwargs, {
                      context: {fill_temporal: true},
                      domain: [],
                      fields: ["categ_id", "sold"],
                      groupby: ["categ_id"],
                      lazy: false,
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual($('.o_widget').length, 1,
            "there should be a node with o_widget class");
        var chartTitle = dashboard.$('.o_pie_chart .o_legacy_graph_renderer label').text();
        assert.strictEqual(chartTitle, "Products sold",
            "the title of the graph should be displayed");
        var chart = dashboard.renderer.widgets[0].controller.renderer.componentRef.comp.chart;
        var legendText = $(chart.generateLegend()).text().trim();
        assert.strictEqual(legendText, "FirstSecond",
            "there should be two legend items");

        dashboard.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('basic rendering of empty pie chart widget', async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        assert.expect(1);

        this.data.test_time_range.records = [];
        this.data.test_report.records = [];

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                      '<widget name="pie_chart" attrs="{\'measure\': \'sold\', \'groupby\': \'categ_id\'}"/>' +
                  '</dashboard>',
        });
        var chart = dashboard.renderer.widgets[0].controller.renderer.componentRef.comp.chart;
        var legendText = $(chart.generateLegend()).text().trim();
        assert.strictEqual(legendText, "No data",
            "the legend should contain the item 'No data'");
        dashboard.destroy();
    });

    QUnit.test('pie chart mode, groupby, and measure not altered by favorite filters', async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        assert.expect(7);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            context: {
                graph_mode: 'line',
                graph_measure: 'untaxed',
                graph_groupbys: [],
            },
            arch: '<dashboard>' +
                      '<widget name="pie_chart" title="Products sold" attrs="{\'measure\': \'sold\', \'groupby\': \'categ_id\'}"/>' +
                  '</dashboard>',
            mockRPC: function (route, args){
                if (route === '/web/dataset/call_kw/test_report/read_group') {
                    assert.deepEqual(args.args, []);
                    assert.deepEqual(args.model,"test_report");
                    assert.deepEqual(args.method,"read_group");
                    assert.deepEqual(args.kwargs, {
                      context: {fill_temporal: true},
                      domain: [],
                      fields: ["categ_id", "sold"],
                      groupby: ["categ_id"],
                      lazy: false,
                    });
                }

                return this._super.apply(this, arguments);
            }

        });
        assert.strictEqual($('.o_widget').length, 1,
            "there should be a node with o_widget class");
        assert.strictEqual($('.o_pie_chart .o_legacy_graph_renderer label').text(), "Products sold",
            "the title of the graph should be displayed");

        var chart = dashboard.renderer.widgets[0].controller.renderer.componentRef.comp.chart;
        var legendText = $(chart.generateLegend()).text().trim();
        assert.strictEqual(legendText, "FirstSecond",
            "there should be two legend items");

        dashboard.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('rendering of a pie chart widget and comparison active', async function (assert) {
        // Pie Chart is rendered asynchronously.
        // concurrency.delay is a fragile way that we use to wait until the
        // graph is rendered.
        // Roughly: 2 concurrency.delay = 2 levels of inner async calls.
        assert.expect(13);

        const unpatchDate = patchDate(2017, 2, 22, 1, 0, 0);

        const readGroupDomains = [
            [],
            ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
            ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
            ["&", ["date", ">=", "2017-02-01"], ["date", "<=", "2017-02-28"]],
        ];

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: '<dashboard>' +
                      '<widget name="pie_chart" title="Products sold" attrs="{\'measure\': \'sold\', \'groupby\': \'categ_id\'}"/>' +
                  '</dashboard>',
            archs: {
                "test_time_range,false,search": '<search><filter name="date" date="date" /></search>',
            },
            mockRPC(route, args) {
                assert.step(args.method);
                assert.deepEqual(args.kwargs.domain, readGroupDomains.shift());
                return this._super(...arguments);
            }
        });
        assert.verifySteps(["read_group"]);

        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'date');
        await toggleMenuItemOption(dashboard.el, 'date', 'March');
        assert.verifySteps(["read_group"]);

        // Apply range with today and comparison with previous period
        await toggleComparisonMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'date: Previous period');
        assert.verifySteps(["read_group","read_group"]);

        assert.strictEqual($('.o_widget').length, 1,
            "there should be a node with o_widget class");
        var chartTitle = $('.o_pie_chart .o_legacy_graph_renderer label').text();
        assert.strictEqual(chartTitle, "Products sold",
            "the title of the graph should be displayed");

        dashboard.destroy();
        unpatchDate();
        delete widgetRegistry.map.test;
    });

    QUnit.test('basic rendering of an aggregate tag inside a group', async function (assert) {
        assert.expect(8);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="sold" field="sold"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['sold:sum(sold)'],
                        "should read the correct field");
                    assert.deepEqual(args.kwargs.domain, [],
                        "should send the correct domain");
                    assert.deepEqual(args.kwargs.groupby, [],
                        "should send the correct groupby");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(dashboard, '.o_aggregate',
            "should have rendered an aggregate");
        assert.strictEqual(dashboard.$('.o_aggregate > label').text(), 'sold',
            "should have correctly rendered the aggregate's label");
        assert.strictEqual(dashboard.$('.o_aggregate > .o_value').text(), '8.00',
            "should correctly display the aggregate's value");
        assert.verifySteps(['read_group']);

        dashboard.destroy();
    });

    QUnit.test('basic rendering of a aggregate tag with widget attribute', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="sold" field="sold" widget="float_time"/>' +
                        '</group>' +
                    '</dashboard>',
        });

        assert.strictEqual(dashboard.$('.o_value').text(), '08:00',
            "should correctly display the aggregate's value");

        dashboard.destroy();
    });

    QUnit.test("Aggregates are not transmitted to the control panel", async function (assert) {
        assert.expect(2);

        this.data.test_report.fields.sold.searchable = true;
        const dashboard = await createView({
            View: DashboardView,
            arch: `
                <dashboard>
                    <group>
                        <aggregate name="sold_aggregate" field="sold"/>
                    </group>
                </dashboard>`,
            data: this.data,
            model: "test_report",
        });

        await toggleFilterMenu(dashboard.el);
        await toggleAddCustomFilter(dashboard.el);

        assert.containsOnce(dashboard, ".o_generator_menu_field > option[value=sold]");
        assert.containsNone(dashboard, ".o_generator_menu_field > option[value=sold_aggregate]");

        dashboard.destroy();
    });

    QUnit.test('basic rendering of a formula tag inside a group', async function (assert) {
        assert.expect(8);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="sold" field="sold"/>' +
                            '<aggregate name="untaxed" field="untaxed"/>' +
                            '<formula name="formula" string="Some label" value="record.sold * record.untaxed"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['sold:sum(sold)', 'untaxed:sum(untaxed)'],
                        "should read the correct fields");
                    assert.deepEqual(args.kwargs.domain, [],
                        "should send the correct domain");
                    assert.deepEqual(args.kwargs.groupby, [],
                        "should send the correct groupby");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(dashboard, '[name="formula"]',
            "should have rendered a formula");
        assert.strictEqual(dashboard.$('[name="formula"] > label').text(), 'Some label',
            "should have correctly rendered the label");
        assert.strictEqual(dashboard.$('[name="formula"] > .o_value').text(), '240.00',
            "should have correctly computed the formula value");
        assert.verifySteps(['read_group']);

        dashboard.destroy();
    });

    QUnit.test('basic rendering of a graph tag', async function (assert) {
        assert.expect(8);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="graph" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['categ_id', 'sold'],
                        "should read the correct fields");
                    assert.deepEqual(args.kwargs.groupby, ['categ_id'],
                        "should group by the correct field");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(dashboard, '.o_subview .o_graph_buttons',
            "should have rendered the graph view's buttons");
        assert.containsN(dashboard, '.o_subview .o_graph_buttons .o_button_switch', 1, "should have rendered an additional switch button");
        assert.containsOnce(dashboard, '.o_subview .o_legacy_graph_renderer');

        assert.verifySteps(['load_views', 'read_group']);

        dashboard.destroy();
    });

    QUnit.test('graph tag without aggregate and invisible field', async function (assert) {
        assert.expect(1);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,graph': `
                    <graph>
                        <field name="categ_id"/>
                        <field name="sold" invisible="1"/>
                    </graph>`,
            },
        });
        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet
        await testUtils.dom.click(dashboard.$('.o_graph_measures_list button'));
        assert.containsNone(dashboard, '.o_menu_item:contains("Sold")',
            "the sold field should be invisible in the measures");

        dashboard.destroy();
    });

    QUnit.test('graph tag with aggregate and invisible field', async function (assert) {
        assert.expect(2);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                    <group>
                        <aggregate name="categ_id_agg" field="categ_id"/>
                    </group>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,graph': `
                    <graph>
                        <field name="categ_id" invisible="1"/>
                    </graph>`,
            }
        });
        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet
        await testUtils.dom.click(dashboard.$('.o_graph_measures_list button'));
        assert.containsOnce(dashboard, '.o_menu_item:contains("Sold")',
            "the sold field should be available as a graph measure");
        assert.containsOnce(dashboard, '.o_menu_item:contains("categ_id")',
            "the categ_id field should be available as a graph measure");

        dashboard.destroy();
    });

    QUnit.test('graph tag with no aggregate and invisible field', async function (assert) {
        assert.expect(2);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,graph': `
                    <graph>
                        <field name="categ_id" invisible="1"/>
                    </graph>`,
            }
        });

        await testUtils.dom.click(dashboard.$('.o_graph_measures_list button'));
        assert.containsOnce(dashboard, '.o_menu_item:contains("Sold")',
            "the sold field should be available as a graph measure");
        assert.containsNone(dashboard, '.o_menu_item:contains("categ_id")',
            "the categ field should not be available as a graph measure");

        dashboard.destroy();
    });

    QUnit.test('graph tag and date aggregate', async function (assert) {
        assert.expect(2);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="graph" ref="some_xmlid"/>
                    <group>
                        <aggregate name="date_agg" group_operator="max" field="date"/>
                    </group>
                </dashboard>`,
            archs: {
                'test_time_range,some_xmlid,graph': `<graph/>`,
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    return Promise.resolve([{
                        __count: 1,
                        date: "1983-07-15",
                    }]);
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(dashboard.$('.o_graph_measures_list button'));
        assert.containsOnce(dashboard, '.o_menu_item:contains("Sold")',
            "the sold field should be available as a graph measure");
        assert.containsNone(dashboard, '.o_menu_item:contains("Date")',
            "the Date field should not be available as a graph measure");

        dashboard.destroy();
    });

    QUnit.test('basic rendering of a pivot tag', async function (assert) {
        assert.expect(11);

        var nbReadGroup = 0;
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="pivot" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,pivot': '<pivot>' +
                        '<field name="categ_id" type="row"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</pivot>',
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read_group') {
                    nbReadGroup++;
                    var groupBy = nbReadGroup === 1 ? [] : ['categ_id'];
                    assert.deepEqual(args.kwargs.fields, ['sold:sum'],
                        "should read the correct fields");
                    assert.deepEqual(args.kwargs.groupby, groupBy,
                        "should group by the correct field");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(dashboard, '.o_subview .o_pivot_buttons',
            "should have rendered the pivot view's buttons");
        assert.containsN(dashboard, '.o_subview .o_pivot_buttons .o_button_switch', 1, "should have rendered an additional switch button");
        assert.containsOnce(dashboard, '.o_subview .o_legacy_pivot',
            "should have rendered a graph view");

        assert.verifySteps(['load_views', 'read_group', 'read_group']);

        dashboard.destroy();
    });

    QUnit.test('pivot tag without aggregate and invisible field', async function (assert) {
        assert.expect(1);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="pivot" ref="some_xmlid"/>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,pivot': `
                    <pivot>
                        <field name="categ_id" type="row"/>
                        <field name="sold" invisible="1"/>
                    </pivot>`,
            },
        });

        await testUtils.dom.click(dashboard.$('button:contains("Measures")'));
        assert.containsNone(dashboard, '.o_pivot_measures_list a:contains("Sold")',
            "the sold field should be invisible in the measures");

        dashboard.destroy();
    });

    QUnit.test('pivot tag with aggregate and invisible field', async function (assert) {
        assert.expect(2);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="pivot" ref="some_xmlid"/>
                    <group>
                        <aggregate name="categ_id_agg" field="categ_id"/>
                    </group>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,pivot': `
                    <pivot>
                        <field name="categ_id" invisible="1" type="measure"/>
                    </pivot>`,
            },
        });

        await testUtils.dom.click(dashboard.$('button:contains("Measures")'));
        assert.containsOnce(dashboard, '.o_pivot_measures_list a:contains("Sold")',
            "the sold field should be available as a pivot measure");
        assert.containsOnce(dashboard, '.o_pivot_measures_list a:contains("categ_id")',
            "the categ_id field should be available as a pivot measure");

        dashboard.destroy();
    });

    QUnit.test('basic rendering of a cohort tag', async function (assert) {
        assert.expect(6);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';


        var readGroups = [[], ['categ_id']];
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="cohort" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>',
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read_group') {
                    var groupBy = readGroups.shift();
                    assert.deepEqual(args.kwargs.fields, ['sold'],
                        "should read the correct fields");
                    assert.deepEqual(args.kwargs.groupby, groupBy,
                        "should group by the correct field");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(dashboard, '.o_subview .o_cohort_buttons',
            "should have rendered the cohort view's buttons");
        assert.containsN(dashboard, '.o_subview .o_cohort_buttons .o_button_switch', 1, "should have rendered an additional switch button");
        assert.containsOnce(dashboard, '.o_subview .o_legacy_cohort_view',
            "should have rendered a graph view");

        assert.verifySteps(['load_views', 'get_cohort_data']);

        dashboard.destroy();
    });

    QUnit.test('cohort tag without aggregate and invisible field', async function (assert) {
        assert.expect(1);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,cohort': `
                    <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week">
                        <field name="sold" invisible="1"/>
                    </cohort>`,
            },
        });

        await testUtils.dom.click(dashboard.$('button:contains("Measures")'));
        assert.containsNone(dashboard, '.o_cohort_measures_list button[data-field="sold"]',
            "the sold field should be invisible in the measures");

        dashboard.destroy();
    });

    QUnit.test('cohort tag with aggregate and invisible field', async function (assert) {
        assert.expect(2);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="cohort" ref="some_xmlid"/>
                    <group>
                        <aggregate name="categ_id_agg" field="categ_id"/>
                    </group>
                </dashboard>`,
            archs: {
                'test_report,some_xmlid,cohort': `
                    <cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week">
                        <field name="categ_id" invisible="1"/>
                    </cohort>`,
            },
        });

        await testUtils.dom.click(dashboard.$('button:contains("Measures")'));
        assert.containsOnce(dashboard, '.o_cohort_measures_list button[data-field="sold"]',
            "the sold field should be in the measures");
        assert.containsNone(dashboard, '.o_cohort_measures_list button[data-field="categ_id"]',
            "the categ_id field should not be in the measures"); // this is wrong and should be fixed!

        dashboard.destroy();
    });

    QUnit.test('rendering of an aggregate with widget monetary', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group><aggregate name="sold" field="sold" widget="monetary"/></group>' +
                    '</dashboard>',
            session: {
                company_currency_id: 44,
                currencies: {
                    44: {
                        digits: [69, 2],
                        position: "after",
                        symbol: "€"
                    }
                }
            },
        });

        assert.strictEqual(dashboard.$('.o_value').text(), '8.00\u00a0€',
            "should format the amount with the correct currency");

        dashboard.destroy();
    });

    QUnit.test('rendering of an aggregate with widget monetary in multi-company', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group><aggregate name="sold" field="sold" widget="monetary"/></group>' +
                    '</dashboard>',
            session: {
                companies_currency_id : {
                    1: 11,
                    2: 22,
                    3: 33,
                },
                currencies: {
                    11: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "$",
                    },
                    22: {
                        digits: [69, 2],
                        position: "after",
                        symbol: "€",
                    },
                    33: {
                        digits: [69, 2],
                        position: "before",
                        symbol: "£",
                    },
                },
                user_companies: {
                    current_company: 1,
                    allowed_companies: {
                        1: {
                            id: 1,
                            name: 'Company 1',
                        },
                        2: {
                            id: 2,
                            name: 'Company 2',
                        },
                        3: {
                            id: 3,
                            name: 'Company 3',
                        },
                    },
                },
                user_context: {
                    allowed_company_ids: [3, 1],
                },
            },
        });

        assert.strictEqual(dashboard.$('.o_value').text(), '£\u00a08.00',
            "should format the amount with the correct currency");

        dashboard.destroy();
    });

    QUnit.test('rendering of an aggregate with value label', async function (assert) {
        assert.expect(2);

        var data = this.data;
        data.test_report.fields.days = {string: "Days to Confirm", type: "float"};
        data.test_report.records[0].days = 5.3;
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: data,
            arch: '<dashboard>' +
                '<group>' +
                    '<aggregate name="days" field="days" value_label="days"/>' +
                    '<aggregate name="sold" field="sold"/>' +
                '</group>' +
            '</dashboard>',
        });

        assert.strictEqual(dashboard.$('.o_value:first').text(), '5.30 days',
        "should have a value label");
        assert.strictEqual(dashboard.$('.o_value:last').text(), '8.00',
        "shouldn't have any value label");

        dashboard.destroy();
    });

    QUnit.test('rendering of field of type many2one', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="categ_id" field="categ_id"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['categ_id:count_distinct(categ_id)'],
                        "should specify 'count_distinct' group operator");
                    // mockReadGroup doesn't implement other group operators than
                    // 'sum', so we hardcode the result of the 'count_disting' here
                    return this._super.apply(this, arguments).then(function (res) {
                        res[0].categ_id = 2;
                        return res;
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(dashboard.$('.o_value').text(), '2',
            "should correctly display the value, formatted as an integer");

        dashboard.destroy();
    });

    QUnit.test('rendering of formula with widget attribute (formatter)', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<aggregate name="sold" field="sold" invisible="1"/>' +
                        '<aggregate name="untaxed" field="untaxed" invisible="1"/>' +
                        '<formula label="Some value" value="record.sold / record.untaxed" widget="percentage"/>' +
                    '</dashboard>',
        });

        assert.strictEqual(dashboard.$('.o_value:visible').text(), '26.67%',
            "should correctly display the value");

        dashboard.destroy();
    });

    QUnit.test('rendering of formula with widget attribute (widget)', async function (assert) {
        assert.expect(1);

        var MyWidget = FieldFloat.extend({
            start: function () {
                this.$el.text('The value is ' + this._formatValue(this.value));
            },
        });
        fieldRegistry.add('test', MyWidget);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<aggregate name="sold" field="sold" invisible="1"/>' +
                        '<aggregate name="untaxed" field="untaxed" invisible="1"/>' +
                        '<formula name="some_value" value="record.sold / record.untaxed" widget="test"/>' +
                    '</dashboard>',
        });
        await testUtils.nextTick();
        assert.strictEqual(dashboard.$('.o_value:visible').text(), 'The value is 0.27',
            "should have used the specified widget (as there is no 'test' formatter)");

        dashboard.destroy();
        delete fieldRegistry.map.test;
    });

    QUnit.test('invisible attribute on a field', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group><aggregate name="sold" field="sold" invisible="1"/></group>' +
                    '</dashboard>',
        });

        assert.hasClass(dashboard.$('.o_group > div'), 'o_invisible_modifier',
            "the aggregate container should be invisible");
        assert.hasClass(dashboard.$('.o_aggregate[name=sold]'), 'o_invisible_modifier',
            "the aggregate should be invisible");

        dashboard.destroy();
    });

    QUnit.test('invisible attribute on a formula', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<formula name="formula" value="2" invisible="1"/>' +
                    '</dashboard>',
        });

        assert.hasClass(dashboard.$('.o_formula'), 'o_invisible_modifier',
            "the formula should be invisible");

        dashboard.destroy();
    });

    QUnit.test('invisible modifier on an aggregate', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="untaxed" field="untaxed" />' +
                            '<aggregate name="sold" field="sold"  attrs="{\'invisible\': [(\'untaxed\',\'=\',30)]}"/>' +
                        '</group>' +
                    '</dashboard>',
        });

        assert.hasClass(dashboard.$('.o_aggregate[name=sold]'), 'o_invisible_modifier',
            "the aggregate 'sold' should be invisible");

        dashboard.destroy();
    });

    QUnit.test('invisible modifier on a formula', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="sold" field="sold"/>' +
                            '<aggregate name="untaxed" field="untaxed"/>' +
                            '<formula label="Some value" value="record.sold / record.untaxed" attrs="{\'invisible\': [(\'untaxed\',\'=\',30)]}"/>' +
                        '</group>' +
                    '</dashboard>',
        });

        assert.hasClass(dashboard.$('.o_formula'), 'o_invisible_modifier',
            "the formula should be invisible");

        dashboard.destroy();
    });

    QUnit.test('rendering of aggregates with domain attribute', async function (assert) {
        assert.expect(11);

        var nbReadGroup = 0;
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="untaxed" field="untaxed"/>' +
                            '<aggregate name="sold" field="sold" domain="[(\'categ_id\', \'=\', 1)]"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read_group') {
                    nbReadGroup++;
                    if (nbReadGroup === 1) {
                        assert.deepEqual(args.kwargs.fields, ['untaxed:sum(untaxed)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, [],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                    } else {
                        assert.deepEqual(args.kwargs.fields, ['sold:sum(sold)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, [['categ_id', '=', 1]],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(dashboard.$('.o_aggregate[name=untaxed] .o_value').text(),
            '30.00', "should correctly display the aggregate's value");
        assert.strictEqual(dashboard.$('.o_aggregate[name=sold] .o_value').text(), '5.00',
            "should correctly display the aggregate's value");

        assert.verifySteps(['read_group', 'read_group']);

        dashboard.destroy();
    });

    QUnit.test('two aggregates with the same field attribute with different domain', async function (assert) {
        assert.expect(11);

        var nbReadGroup = 0;
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="sold" field="sold"/>' +
                            '<aggregate name="sold_categ_1" field="sold" domain="[(\'categ_id\', \'=\', 1)]"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                var def = this._super.apply(this, arguments);
                if (args.method === 'read_group') {
                    nbReadGroup++;
                    if (nbReadGroup === 1) {
                        assert.deepEqual(args.kwargs.fields, ['sold:sum(sold)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, [],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                    } else {
                        assert.deepEqual(args.kwargs.fields, ['sold_categ_1:sum(sold)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, [['categ_id', '=', 1]],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                        // mockReadGroup doesn't handle this kind of requests yet, so we hardcode
                        // the result in the test
                        return def.then(function (result) {
                            result[0].sold_categ_1 = 5;
                            return result;
                        });
                    }
                }
                return def;
            },
        });

        assert.strictEqual(dashboard.$('.o_aggregate[name=sold] .o_value').text(),
            '8.00', "should correctly display the aggregate's value");
        assert.strictEqual(dashboard.$('.o_aggregate[name=sold_categ_1] .o_value').text(), '5.00',
            "should correctly display the aggregate's value");

        assert.verifySteps(['read_group', 'read_group']);

        dashboard.destroy();
    });

    QUnit.test('formula based on same field with different domains', async function (assert) {
        assert.expect(1);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="untaxed_categ_1" field="untaxed"  domain="[(\'categ_id\', \'=\', 1)]"/>' +
                            '<aggregate name="untaxed_categ_2" field="untaxed"  domain="[(\'categ_id\', \'=\', 2)]"/>' +
                            '<formula label="Ratio" value="record.untaxed_categ_1 / record.untaxed_categ_2"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                var def = this._super.apply(this, arguments);
                if (args.method === 'read_group') {
                    // mockReadGroup doesn't handle this kind of requests yet, so we hardcode
                    // the result in the test
                    return def.then(function (result) {
                        var name = args.kwargs.fields[0].split(':')[0];
                        result[0][name] = name === 'untaxed_categ_1' ? 10.0 : 20.0;
                        return result;
                    });
                }
                return def;
            },
        });

        assert.strictEqual(dashboard.$('.o_formula .o_value').text(), '0.50',
            "should have correctly computed and displayed the formula");

        dashboard.destroy();
    });

    QUnit.test('clicking on an aggregate', async function (assert) {
        assert.expect(21);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<group>' +
                        '<aggregate name="untaxed" field="untaxed"/>' +
                        '<aggregate name="sold" field="sold"/>' +
                    '</group>' +
                    '<view type="graph"/>' +
                    '<view type="pivot"/>' +
                '</dashboard>',
            archs: {
                'test_report,false,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
                'test_report,false,pivot': '<pivot>' +
                        '<field name="categ_id" type="row"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</pivot>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    for(var i in args.kwargs.fields) {
                        assert.step(args.kwargs.fields[i]);
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        assert.hasClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Sold)'), 'selected',
            "sold measure should be active in graph view");
        assert.doesNotHaveClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Untaxed)'), 'selected',
            "untaxed measure should not be active in graph view");
        assert.hasClass(dashboard.$('.o_pivot_measures_list .dropdown-item[data-field=sold]'), 'selected',
            "sold measure should be active in pivot view");
        assert.doesNotHaveClass(dashboard.$('.o_pivot_measures_list .dropdown-item[data-field=untaxed]'), 'selected',
            "untaxed measure should not be active in pivot view");

        // click on the 'untaxed' field: it should activate the 'untaxed' measure in both subviews
        await testUtils.dom.click(dashboard.$('.o_aggregate[name=untaxed]'));

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        assert.doesNotHaveClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Sold)'), 'selected',
            "sold measure should not be active in graph view");
        assert.hasClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Untaxed)'), 'selected',
            "untaxed measure should be active in graph view");
        assert.doesNotHaveClass(dashboard.$('.o_pivot_measures_list .dropdown-item[data-field=sold]'), 'selected',
            "sold measure should not be active in pivot view");
        assert.hasClass(dashboard.$('.o_pivot_measures_list .dropdown-item[data-field=untaxed]'), 'selected',
            "untaxed measure should be active in pivot view");

        assert.verifySteps([
            'untaxed:sum(untaxed)', 'sold:sum(sold)', // fields
            'categ_id', 'sold', // graph
            'sold:sum', // pivot
            'sold:sum', // pivot
            'untaxed:sum(untaxed)', 'sold:sum(sold)', // fields
            'categ_id', 'untaxed', // graph
            'untaxed:sum', // pivot
            'untaxed:sum', // pivot
        ]);

        dashboard.destroy();
    });

    QUnit.test('clicking on an aggregate interaction with cohort', async function (assert) {
        assert.expect(11);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<group>' +
                        '<aggregate name="untaxed" field="untaxed"/>' +
                        '<aggregate name="sold" field="sold"/>' +
                    '</group>' +
                    '<view type="cohort"/>' +
                '</dashboard>',
            archs: {
                'test_report,false,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week" measure="sold"/>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    for (var i in args.kwargs.fields) {
                        assert.step(args.kwargs.fields[i]);
                    }
                }
                if (args.method === 'get_cohort_data') {
                    assert.step(args.kwargs.measure);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.hasClass(dashboard.$('.o_cohort_measures_list [data-field=sold]'), 'selected',
            "sold measure should be active in cohort view");
        assert.doesNotHaveClass(dashboard.$('.o_cohort_measures_list [data-field=untaxed]'), 'selected',
            "untaxed measure should not be active in cohort view");

        // click on the 'untaxed' field: it should activate the 'untaxed' measure in cohort subview
        await testUtils.dom.click(dashboard.$('.o_aggregate[name=untaxed]'));

        assert.doesNotHaveClass(dashboard.$('.o_cohort_measures_list [data-field=sold]'), 'selected',
            "sold measure should not be active in cohort view");
        assert.hasClass(dashboard.$('.o_cohort_measures_list [data-field=untaxed]'), 'selected',
            "untaxed measure should be active in cohort view");

        assert.verifySteps([
            'untaxed:sum(untaxed)', 'sold:sum(sold)', // fields
            'sold', // cohort
            'untaxed:sum(untaxed)', 'sold:sum(sold)', // fields
            'untaxed', // cohort
        ]);

        dashboard.destroy();
    });

    QUnit.test('clicking on aggregate with domain attribute', async function (assert) {
        assert.expect(19);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<group>' +
                        '<aggregate name="untaxed" field="untaxed" domain="[(\'categ_id\', \'=\', 2)]" domain_label="Category 2"/>' +
                        '<aggregate name="sold" field="sold" domain="[(\'categ_id\', \'=\', 1)]"/>' +
                    '</group>' +
                '</dashboard>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.fields[0]);
                    for (var i in args.kwargs.domain) {
                        assert.step(args.kwargs.domain[i].join(''));
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        // click on the 'untaxed' field: it should update the domain
        await testUtils.dom.click(dashboard.$('.o_aggregate[name=untaxed]'));
        assert.strictEqual(dashboard.$('.o_control_panel .o_facet_values').text().trim(), 'Category 2',
            "should correctly display the filter in the search view");

        // click on the 'sold' field: it should update the domain
        await testUtils.dom.click(dashboard.$('.o_aggregate[name=sold]'));
        assert.strictEqual(dashboard.$('.o_control_panel .o_facet_values').text().trim(), 'sold',
            "should correctly display the filter in the search view");

        assert.verifySteps([
            // initial read_groups
            'untaxed:sum(untaxed)', 'categ_id=2',
            'sold:sum(sold)', 'categ_id=1',
            // 'untaxed' field clicked
            'untaxed:sum(untaxed)', 'categ_id=2', 'categ_id=2',
            'sold:sum(sold)', 'categ_id=2', 'categ_id=1',
            // 'sold' field clicked
            'untaxed:sum(untaxed)', 'categ_id=1', 'categ_id=2',
            'sold:sum(sold)', 'categ_id=1', 'categ_id=1',
        ]);

        dashboard.destroy();
    });

    QUnit.test('clicking on an aggregate with domain excluding all records for another an aggregate does not cause a crash with formulas', async function (assert) {
        assert.expect(14);

        this.data.test_report.fields.untaxed_2 = {string: "Untaxed_2", type: 'float', store: true};
        this.data.test_report.records.forEach(record => record.untaxed_2 = 3.1415);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<aggregate name="untaxed" field="untaxed" domain="[(\'categ_id\', \'=\', 2)]"/>' +
                    '<aggregate name="untaxed_2" field="untaxed_2" domain="[(\'categ_id\', \'=\', 1)]"/>' +
                    '<formula name="formula" value="1 / record.untaxed_2"/>' +
                    '<formula name="formula_2" value="record.untaxed_2 / record.untaxed_2"/>' +
                '</dashboard>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.fields[0]);
                    for (var i in args.kwargs.domain) {
                        assert.step(args.kwargs.domain[i].join(''));
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        // click on the 'untaxed' field: we should see zeros displayed as values
        await testUtils.dom.click(dashboard.$('.o_aggregate[name=untaxed]'));
        assert.strictEqual(dashboard.$('.o_aggregate[name="untaxed_2"] > .o_value').text(), "0.00",
            "should display zero as no record satisfies constrains");
        assert.strictEqual(dashboard.$('.o_formula[name="formula"] > .o_value').text(), "-", "Should display '-'");
        assert.strictEqual(dashboard.$('.o_formula[name="formula_2"] > .o_value').text(), "-", "Should display '-'");

        assert.verifySteps([
            'untaxed:sum(untaxed)', 'categ_id=2',
            'untaxed_2:undefined(untaxed_2)', 'categ_id=1',
            'untaxed:sum(untaxed)', 'categ_id=2', 'categ_id=2',
            'untaxed_2:undefined(untaxed_2)', 'categ_id=2', 'categ_id=1'
        ]);
        dashboard.destroy();
    });

    QUnit.test('open a graph view fullscreen', async function (assert) {
        assert.expect(3);
        const views = {
            'test_report,false,dashboard': '<dashboard>' +
                    '<view type="graph" ref="some_xmlid"/>' +
                '</dashboard>',
            'test_report,some_xmlid,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
            'test_report,false,search': '<search/>',
        };
        Object.assign(serverData, {views});

        viewRegistry.remove("dashboard");
        legacyViewRegistry.add("dashboard", DashboardView); // We want to test the legacy view that was not added to viewRegistry!
        viewRegistry.remove("graph");
        legacyViewRegistry.add("graph", GraphView); // We want to test the legacy view that was not added to viewRegistry!

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            name: 'Dashboard',
            res_model: 'test_report',
            type: 'ir.actions.act_window',
            views: [[false, 'dashboard']],
        });

        assert.strictEqual($('.o_control_panel .breadcrumb-item').text(), 'Dashboard',
            "'Dashboard' should be displayed in the breadcrumbs");

        // open graph in fullscreen
        await testUtils.dom.click($(webClient.el).find('.o_graph_buttons .o_button_switch'));
        await nextTick();

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:nth(1)').text(), 'Graph Analysis',
            "'Graph Analysis' should have been stacked in the breadcrumbs");

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await nextTick();
        await nextTick();

        assert.strictEqual($('.o_control_panel .breadcrumb-item').text(), 'Dashboard',
        "'Dashboard' should be displayed in the breadcrumbs");
    });

    QUnit.test('open a cohort view fullscreen', async function (assert) {
        assert.expect(3);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        const views = {
            'test_report,false,dashboard': '<dashboard>' +
                    '<view type="cohort" ref="some_xmlid"/>' +
                '</dashboard>',
            'test_report,some_xmlid,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>',
            'test_report,false,search': '<search/>',
        };
        Object.assign(serverData, {views});

        viewRegistry.remove("dashboard");
        legacyViewRegistry.add("dashboard", DashboardView); // We want to test the legacy view that was not added to viewRegistry!
        viewRegistry.remove("cohort");
        legacyViewRegistry.add("cohort", CohortView); // We want to test the legacy view that was not added to viewRegistry!

        const webClient = await createWebClient({
            serverData,
            legacyParams: { withLegacyMockServer: true },
        });

        await doAction(webClient, {
            name: 'Dashboard',
            res_model: 'test_report',
            type: 'ir.actions.act_window',
            views: [[false, 'dashboard']],
        });


        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').text(), 'Dashboard',
            "'Dashboard' should be displayed in the breadcrumbs");

        // open cohort in fullscreen
        await testUtils.dom.click($(webClient.el).find('.o_cohort_buttons .o_button_switch'));
        await nextTick();
        assert.strictEqual($('.o_control_panel .breadcrumb li:nth(1)').text(), 'Cohort Analysis',
            "'Cohort Analysis' should have been stacked in the breadcrumbs");

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await nextTick();

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').text(), 'Dashboard',
        "'Dashboard' should be displayed in the breadcrumbs");
    });

    QUnit.test('interact with a graph view and open it fullscreen', async function (assert) {
        assert.expect(8);

        var activeMeasure = 'sold';
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="graph"/></dashboard>',
            archs: {
                'test_report,false,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['categ_id', activeMeasure],
                        "should read the correct measure");
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                do_action: function (ev) {
                    assert.step('doAction');
                    var expectedAction = {
                        context: {
                            graph_groupbys: ['categ_id'],
                            graph_measure: 'untaxed',
                            graph_mode: 'pie',
                        },
                        domain: [],
                        name: 'Graph Analysis',
                        res_model: 'test_report',
                        type: 'ir.actions.act_window',
                        views: [[false, 'graph']],
                        useSampleModel: false,
                    };
                    assert.deepEqual(ev.data.action, expectedAction,
                        "should execute an action with correct params");
                },
            },
        });

        var chart = dashboard.renderer.subControllers.graph.renderer.componentRef.comp.chart;
        assert.strictEqual(chart.config.type, 'bar', 'should have rendered the graph in "bar" mode');
        // switch to pie mode
        await testUtils.dom.click(dashboard.$('.o_graph_buttons button[data-mode=pie]'));
        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet
        chart = dashboard.renderer.subControllers.graph.renderer.componentRef.comp.chart;
        assert.strictEqual(chart.config.type, 'pie', 'should have rendered the graph in "pie" mode');

        // select 'untaxed' as measure
        activeMeasure = 'untaxed';
        await testUtils.dom.click($('.o_graph_buttons button:contains(Measures)'));
        assert.containsOnce(dashboard, '.o_graph_buttons .dropdown-item:contains(Untaxed)',
            "should have 'untaxed' in the list of measures");

        await testUtils.dom.click(dashboard.$('.o_graph_buttons .dropdown-item:contains(Untaxed)'));

        // open graph in fullscreen
        await testUtils.dom.click(dashboard.$('.o_graph_buttons .o_button_switch'));
        assert.verifySteps(['doAction']);

        dashboard.destroy();
    });

    QUnit.test('interact with a cohort view and open it fullscreen', async function (assert) {
        assert.expect(6);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        var activeMeasure = 'sold';
        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="cohort"/></dashboard>',
            archs: {
                'test_report,false,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week" measure="sold"/>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_cohort_data') {
                    assert.deepEqual(args.kwargs.measure, activeMeasure,
                        "should read the correct measure");
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                do_action: function (ev) {
                    assert.step('doAction');
                    var expectedAction = {
                        context: {
                            cohort_measure: 'untaxed',
                            cohort_interval: 'week',
                        },
                        domain: [],
                        name: 'Cohort Analysis',
                        res_model: 'test_report',
                        type: 'ir.actions.act_window',
                        views: [[false, 'cohort']],
                        useSampleModel: false,
                    };
                    assert.deepEqual(ev.data.action, expectedAction,
                        "should execute an action with correct params");
                },
            },
        });

        // select 'untaxed' as measure
        activeMeasure = 'untaxed';
        assert.containsOnce(dashboard, '.o_cohort_buttons [data-field=untaxed]',
        "should have 'untaxed' in the list of measures");
        testUtils.dom.click($('button:contains(Measures)'));
        testUtils.dom.click(dashboard.$('.o_cohort_buttons [data-field=untaxed]'));

        // open cohort in fullscreen
        testUtils.dom.click(dashboard.$('.o_cohort_buttons .o_button_switch'));
        assert.verifySteps(['doAction']);

        dashboard.destroy();
    });

    QUnit.test('aggregates of type many2one should be measures of subviews', async function (assert) {
        assert.expect(5);

        // Define an aggregate on many2one field
        this.data.test_report.fields.product_id = {string: "Product", type: 'many2one', relation: 'product', store: true};
        this.data.product = {
            fields: {
                name: {string: "Product Name", type: "char"}
            },
            records: [{
                id: 37,
                display_name: "xphone",
            }, {
                id: 41,
                display_name: "xpad",
            }],
        };
        this.data.test_report.records[0].product_id = 37;
        this.data.test_report.records[0].product_id = 41;

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<aggregate name="product_id_something" field="product_id"/>' +
                        '<view type="graph"/>' +
                        '<view type="pivot"/>' +
                    '</dashboard>',
            archs: {
                'test_report,false,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
                'test_report,false,pivot': '<pivot>' +
                    '<field name="sold" type="measure"/>' +
                '</pivot>',
            },
            intercepts: {
                do_action: function (ev) {
                    assert.step('doAction');
                    var expectedActionFlags = {
                        additionalMeasures: ['product_id'],
                    };
                    assert.deepEqual(ev.data.action.flags, expectedActionFlags,
                        "should have passed additional measures in fullscreen");
                },
            },
        });

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click($('.o_graph_buttons button:contains(Measures)'));

        assert.containsOnce(dashboard, '.o_graph_buttons .dropdown-item:contains(Product)',
            "should have 'Product' as a measure in the graph view");
        assert.containsOnce(dashboard, '.o_pivot_measures_list .dropdown-item[data-field=product_id]',
            "should have 'Product' as measure in the pivot view");

        // open graph in fullscreen
        testUtils.dom.click(dashboard.$('.o_graph_buttons .o_button_switch'));

        assert.verifySteps(['doAction']);

        dashboard.destroy();
    });

    QUnit.test('interact with subviews, open one fullscreen and come back', async function (assert) {
        assert.expect(14);

        const views = {
            'test_report,false,dashboard': '<dashboard>' +
                    '<view type="graph"/>' +
                    '<view type="pivot"/>' +
                '</dashboard>',
            'test_report,false,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
            'test_report,false,pivot': '<pivot>' +
                    '<field name="sold" type="measure"/>' +
                '</pivot>',
            'test_report,false,search': '<search></search>',
        };
        Object.assign(serverData, {views});

        viewRegistry.remove("dashboard");
        legacyViewRegistry.add("dashboard", DashboardView); // We want to test the legacy view that was not added to viewRegistry!
        viewRegistry.remove("graph");
        legacyViewRegistry.add("graph", GraphView); // We want to test the legacy view that was not added to viewRegistry!
        viewRegistry.remove("pivot");
        legacyViewRegistry.add("pivot", PivotView); // We want to test the legacy view that was not added to viewRegistry!

        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    for (var i in args.kwargs.fields) {
                        assert.step(args.kwargs.fields[i]);
                    }
                }
            },
        });

        await doAction(webClient, {
            name: 'Dashboard',
            res_model: 'test_report',
            type: 'ir.actions.act_window',
            views: [[false, 'dashboard']],
        });

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        // select 'untaxed' as measure in graph view
        await testUtils.dom.click($(webClient.el).find('.o_graph_buttons button:contains(Measures)'));
        await testUtils.dom.click($(webClient.el).find('.o_graph_buttons .dropdown-item:contains(Untaxed)'));

        // select 'untaxed' as additional measure in pivot view
        await testUtils.dom.click($(webClient.el).find('.o_pivot_buttons button:contains(Measures)'));
        await testUtils.dom.click($(webClient.el).find('.o_pivot_measures_list .dropdown-item[data-field=untaxed]'));

        // open graph in fullscreen
        await testUtils.dom.click($(webClient.el).find('.o_pivot_buttons .o_button_switch'));
        await nextTick();

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await nextTick();

        assert.verifySteps([
            // initial read_group
            'categ_id', 'sold', // graph in dashboard
            'sold:sum', // pivot in dashboard

            // after changing the measure in graph
            'categ_id', 'untaxed', // graph in dashboard

            // after changing the measures in pivot
            'sold:sum', 'untaxed:sum', // pivot in dashboard

            // pivot opened fullscreen
            'sold:sum', 'untaxed:sum',

            // after coming back
            'categ_id', 'untaxed', // graph in dashboard
            'sold:sum', 'untaxed:sum', // pivot in dashboard
        ]);
    });

    QUnit.test('open subview fullscreen, update domain and come back', async function (assert) {
        assert.expect(8);

        const views = {
            'test_report,false,dashboard': '<dashboard>' +
                    '<view type="graph"/>' +
                '</dashboard>',
            'test_report,false,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
            'test_report,false,search': '<search>' +
                   '<filter name="sold" help="Sold" domain="[(\'sold\', \'=\', 10)]"/>' +
                   '<filter name="buy" help="Buy" domain="[(\'sold\', \'=\', -10)]"/>' +
                '</search>',
        };
        Object.assign(serverData, {views});

        viewRegistry.remove("dashboard");
        legacyViewRegistry.add("dashboard", DashboardView); // We want to test the legacy view that was not added to viewRegistry!
        viewRegistry.remove("graph");
        legacyViewRegistry.add("graph", GraphView); // We want to test the legacy view that was not added to viewRegistry!

        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.domain[0] ? args.kwargs.domain[0].join('') : ' ');
                }
            }
        });

        await doAction(webClient, {
            name: 'Dashboard',
            res_model: 'test_report',
            type: 'ir.actions.act_window',
            views: [[false, 'dashboard']],
        });


        // open graph in fullscreen
        await testUtils.dom.click($(webClient.el).find('.o_graph_buttons .o_button_switch'));
        await nextTick();

        // filter on bar
        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, 0);
        assert.deepEqual(getFacetTexts(webClient), ['Sold']);

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        await legacyExtraNextTick();

        assert.deepEqual(getFacetTexts(webClient), []);

        await toggleFilterMenu(webClient);
        await toggleMenuItem(webClient, 1);

        assert.verifySteps([
            ' ', // graph in dashboard
            ' ', // graph full screen
            'sold=10', // graph full screen with first filter applied
            ' ', // graph in dashboard after coming back
            'sold=-10', // graph in dashboard with second filter applied
        ]);
    });

    QUnit.test('action domain is kept when going back and forth to fullscreen subview', async function (assert) {
        assert.expect(4);

        const views = {
            'test_report,false,dashboard': '<dashboard>' +
                    '<view type="graph"/>' +
                '</dashboard>',
            'test_report,false,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
            'test_report,false,search': '<search></search>',
        };
        Object.assign(serverData, {views});

        viewRegistry.remove("dashboard");
        legacyViewRegistry.add("dashboard", DashboardView); // We want to test the legacy view that was not added to viewRegistry!
        viewRegistry.remove("graph");
        legacyViewRegistry.add("graph", GraphView); // We want to test the legacy view that was not added to viewRegistry!

        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.domain[0].join(''));
                }
            },
        });

        await doAction(webClient, {
            name: 'Dashboard',
            domain: [['categ_id', '=', 1]],
            res_model: 'test_report',
            type: 'ir.actions.act_window',
            views: [[false, 'dashboard']],
        });

        // open graph in fullscreen
        await testUtils.dom.click($(webClient.el).find('.o_graph_buttons .o_button_switch'));
        await nextTick();

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await nextTick();

        assert.verifySteps([
            'categ_id=1', // First rendering of dashboard view
            'categ_id=1', // Rendering of graph view in full screen
            'categ_id=1', // Second rendering of dashboard view
        ]);
    });

    QUnit.test('getOwnedQueryParams correctly returns graph subview context', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="graph" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                    '</graph>',
            },
        });

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        assert.deepEqual(dashboard.getOwnedQueryParams().context.graph, {
            graph_mode: 'bar',
            graph_measure: '__count__',
            graph_groupbys: ['categ_id'],
        }, "context should be correct");

        await testUtils.dom.click(dashboard.$('button:contains(Measures)'));
        await testUtils.dom.click(dashboard.$('.dropdown-item:contains(Sold)'));
        await testUtils.dom.click(dashboard.$('button[data-mode="line"]'));

        assert.deepEqual(dashboard.getOwnedQueryParams().context.graph, {
            graph_mode: 'line',
            graph_measure: 'sold',
            graph_groupbys: ['categ_id'],
        }, "context should be correct");

        dashboard.destroy();
    });

    QUnit.test('getOwnedQueryParams correctly returns pivot subview context', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="pivot" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,pivot': '<pivot>' +
                        '<field name="categ_id" type="row"/>' +
                    '</pivot>',
            },
        });

        assert.deepEqual(dashboard.getOwnedQueryParams().context.pivot, {
            pivot_column_groupby: [],
            pivot_measures: ['__count'],
            pivot_row_groupby: ['categ_id'],
        }, "context should be correct");

        await testUtils.dom.click(dashboard.$('.dropdown-toggle:contains(Measures)'));
        await testUtils.dom.click(dashboard.$('.dropdown-item[data-field="sold"]'));
        await testUtils.dom.click(dashboard.$('.o_pivot_flip_button'));

        assert.deepEqual(dashboard.getOwnedQueryParams().context.pivot, {
            pivot_column_groupby: ['categ_id'],
            pivot_measures: ['__count', 'sold'],
            pivot_row_groupby: [],
        }, "context should be correct");

        dashboard.destroy();
    });

    QUnit.test('getOwnedQueryParams correctly returns cohort subview context', async function (assert) {
        assert.expect(2);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="cohort" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>',
            },
        });

        assert.deepEqual(dashboard.getOwnedQueryParams().context.cohort, {
            cohort_measure: '__count',
            cohort_interval: 'week',
        }, "context should be correct");

        await testUtils.dom.click(dashboard.$('.dropdown-toggle:contains(Measures)'));
        await testUtils.dom.click(dashboard.$('[data-field="sold"]'));

        assert.deepEqual(dashboard.getOwnedQueryParams().context.cohort, {
            cohort_measure: 'sold',
            cohort_interval: 'week',
        }, "context should be correct");

        dashboard.destroy();
    });

    QUnit.test('correctly uses graph_ keys from the context', async function (assert) {
        assert.expect(4);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="graph" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['categ_id', 'untaxed'],
                        "should fetch data for untaxed");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                context: {
                    graph: {
                        graph_measure: 'untaxed',
                        graph_mode: 'line',
                        graph_groupbys: ['categ_id'],
                    }
                },
            },
        });

        // check mode
        assert.strictEqual(dashboard.renderer.subControllers.graph.renderer.componentRef.comp.props.mode,
            "line", "should be in line chart mode");
        assert.doesNotHaveClass(dashboard.$('button[data-mode="bar"]'), 'active',
            'bar chart button should not be active');
        assert.hasClass(dashboard.$('button[data-mode="line"]'), 'active',
            'line chart button should be active');

        dashboard.destroy();
    });

    QUnit.test('correctly uses pivot_ keys from the context', async function (assert) {
        assert.expect(7);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="pivot" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,pivot': '<pivot>' +
                        '<field name="categ_id" type="col"/>' +
                        '<field name="untaxed" type="measure"/>' +
                '</pivot>',
            },
            viewOptions: {
                context: {
                    pivot: {
                        pivot_measures: ['sold'],
                        pivot_column_groupby: ['categ_id'],
                        pivot_row_groupby: ['categ_id'],
                    }
                },
            },
        });

        assert.containsOnce(dashboard, 'thead .o_pivot_header_cell_opened',
            "column: should have one opened header");
        assert.strictEqual(dashboard.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            "column: should display one closed header with 'First'");
        assert.strictEqual(dashboard.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            "column: should display one closed header with 'Second'");

        assert.containsOnce(dashboard, 'tbody .o_pivot_header_cell_opened',
            "row: should have one opened header");
        assert.strictEqual(dashboard.$('tbody .o_pivot_header_cell_closed:contains(First)').length, 1,
            "row: should display one closed header with 'xphone'");
        assert.strictEqual(dashboard.$('tbody .o_pivot_header_cell_closed:contains(First)').length, 1,
            "row: should display one closed header with 'xpad'");

        assert.strictEqual(dashboard.$('tbody tr:first td:nth(2)').text(), '8.00',
            "selected measure should be foo, with total 32");

        dashboard.destroy();
    });

    QUnit.test('correctly uses cohort_ keys from the context', async function (assert) {
        assert.expect(4);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="cohort" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_cohort_data') {
                    assert.deepEqual(args.kwargs.measure, 'untaxed',
                        "should fetch data for untaxed");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                context: {
                    cohort: {
                        cohort_measure: 'untaxed',
                        cohort_interval: 'year',
                    }
                },
            },
        });

        // check interval
        assert.strictEqual(dashboard.renderer.subControllers.cohort.renderer.props.interval,
            "year", "should use year interval");
        assert.doesNotHaveClass(dashboard.$('button[data-interval="day"]'), 'active',
                'day interval button should not be active');
        assert.hasClass(dashboard.$('button[data-interval="year"]'), 'active',
            'year interval button should be active');

        dashboard.destroy();
    });

    QUnit.test('correctly uses graph_ keys from the context (at reload)', async function (assert) {
        assert.expect(5);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="graph" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,graph': '<graph>' +
                        '<field name="categ_id"/>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    for (var i in args.kwargs.fields) {
                        assert.step(args.kwargs.fields[i]);
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        await dashboard.reload({
            context: {
                graph: {
                    graph_measure: 'untaxed',
                    graph_mode: 'line',
                    graph_groupbys: ['categ_id'],
                },
            },
        });

        assert.verifySteps([
            'categ_id', 'sold', // first load
            'categ_id', 'untaxed', // reload
        ]);

        dashboard.destroy();
    });

    QUnit.test('correctly uses cohort_ keys from the context (at reload)', async function (assert) {
        assert.expect(3);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard><view type="cohort" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_report,some_xmlid,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_cohort_data') {
                    assert.step(args.kwargs.measure);
                }
                return this._super.apply(this, arguments);
            },
        });

        await dashboard.reload({
            context: {
                cohort: {
                    cohort_measure: 'untaxed',
                    cohort_interval: 'year',
                },
            },
        });

        assert.verifySteps([
            '__count', // first load
            'untaxed', // reload
        ]);

        dashboard.destroy();
    });

    QUnit.test('changes in search view do not affect measure selection in graph subview', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<view type="graph" ref="some_xmlid"/>' +
                '</dashboard>',
            archs: {
                'test_report,some_xmlid,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
                'test_report,false,search': '<search>' +
                    '<field name="categ_id" string="Label"/>' +
                    '<filter string="categ" name="positive" domain="[(\'categ_id\', \'>=\', 0)]"/>' +
                '</search>',
            },
        });

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));
        await testUtils.dom.click(dashboard.$('.o_graph_buttons .o_graph_measures_list .dropdown-item').eq(1));

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        assert.hasClass(dashboard.$('.o_graph_buttons .o_graph_measures_list .dropdown-item').eq(1), 'selected',
            'groupby should be unselected');

        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 0);

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));

        assert.hasClass(dashboard.$('.o_graph_buttons .o_graph_measures_list .dropdown-item').eq(1), 'selected',
            'groupby should be unselected');

        dashboard.destroy();
    });

    QUnit.test('When there is a measure attribute we use it to filter the graph and pivot', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<view type="graph"/>' +
                    '<group>' +
                        '<aggregate name="number" field="id" group_operator="count" measure="__count__"/>' +
                        '<aggregate name="untaxed" field="untaxed"/>' +
                    '</group>' +
                    '<view type="pivot"/>' +
                '</dashboard>',
            archs: {
                'test_report,false,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
                'test_report,false,pivot': '<pivot>' +
                    '<field name="categ_id" type="row"/>' +
                    '<field name="sold" type="measure"/>' +
                '</pivot>',
            },
        });

        // click on aggregate to activate count measure
        await testUtils.dom.click(dashboard.$('.o_aggregate:first .o_value'));

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));
        assert.hasClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Count)'), 'selected',
            'count measure should be selected in graph view');
        assert.hasClass(dashboard.$('.o_pivot_measures_list [data-field=\'__count\']'), 'selected',
            'count measure should be selected in pivot view');

        dashboard.destroy();
    });

    QUnit.test('When no measure is given in the aggregate we use the field as measure', async function (assert) {
        assert.expect(2);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<view type="graph"/>' +
                    '<group>' +
                        '<aggregate name="number" field="id" group_operator="count" measure="__count__"/>' +
                        '<aggregate name="untaxed" field="untaxed"/>' +
                    '</group>' +
                    '<view type="pivot"/>' +
                '</dashboard>',
            archs: {
                'test_report,false,graph': '<graph>' +
                    '<field name="categ_id"/>' +
                    '<field name="sold" type="measure"/>' +
                '</graph>',
                'test_report,false,pivot': '<pivot>' +
                    '<field name="categ_id" type="row"/>' +
                    '<field name="sold" type="measure"/>' +
                '</pivot>',
            },
        });

        // click on aggregate to activate untaxed measure
        await testUtils.dom.click(dashboard.$('.o_aggregate:nth(1) .o_value'));

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));
        assert.hasClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Untaxed)'), 'selected',
            'untaxed measure should be selected in graph view');
        assert.hasClass(dashboard.$('.o_pivot_measures_list [data-field=\'untaxed\']'), 'selected',
            'untaxed measure should be selected in pivot view');

        dashboard.destroy();
    });

    QUnit.test('changes in search view do not affect measure selection in cohort subview', async function (assert) {
        assert.expect(2);

        this.data.test_report.fields.create_date = {type: 'date', string: 'Creation Date'};
        this.data.test_report.fields.transformation_date = {type: 'date', string: 'Transormation Date'};

        this.data.test_report.records[0].create_date = '2018-05-01';
        this.data.test_report.records[1].create_date = '2018-05-01';
        this.data.test_report.records[0].transformation_date = '2018-07-03';
        this.data.test_report.records[1].transformation_date = '2018-06-23';

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<view type="cohort" ref="some_xmlid"/>' +
                '</dashboard>',
            archs: {
                'test_report,some_xmlid,cohort': '<cohort string="Cohort" date_start="create_date" date_stop="transformation_date" interval="week"/>',
                'test_report,false,search': '<search>' +
                    '<field name="categ_id" string="Label"/>' +
                    '<filter string="categ" name="positive" domain="[(\'categ_id\', \'>=\', 0)]"/>' +
                '</search>',
            },
        });


        await testUtils.dom.click(dashboard.$('.o_cohort_buttons button:first'));
        await testUtils.dom.click(dashboard.$('.o_cohort_buttons .o_cohort_measures_list .dropdown-item').eq(1));
        assert.hasClass(dashboard.$('.o_cohort_buttons .o_cohort_measures_list .dropdown-item').eq(1), 'selected',
            'groupby should be unselected');

        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 0);
        assert.hasClass(dashboard.$('.o_cohort_buttons .o_cohort_measures_list .dropdown-item').eq(1), 'selected',
            'groupby should be unselected');

        dashboard.destroy();
    });

    QUnit.test('render aggregate node using clickable attribute', async function (assert) {
        assert.expect(4);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                    '<view type="graph" ref="xml_id"/>' +
                    '<group>' +
                        '<aggregate name="a" field="categ_id"/>' +
                        '<aggregate name="b" field="sold" clickable="true"/>' +
                        '<aggregate name="c" field="untaxed" clickable="false"/>' +
                    '</group>' +
                  '</dashboard>',
            archs: {
                'test_report,xml_id,graph': '<graph>' +
                            '<field name="categ_id"/>' +
                            '<field name="sold" type="measure"/>' +
                        '</graph>'
            },
        });

        assert.hasClass(dashboard.$('div[name="a"]'), 'o_clickable',
                    "By default aggregate should be clickable");
        assert.hasClass(dashboard.$('div[name="b"]'), 'o_clickable',
                    "Clickable = true aggregate should be clickable");
        assert.doesNotHaveClass(dashboard.$('div[name="c"]'), 'o_clickable',
                    "Clickable = false aggregate should not be clickable");

        await testUtils.dom.click(dashboard.$('div[name="c"]'));
        await testUtils.dom.click(dashboard.$('.o_graph_buttons button:first'));
        assert.hasClass(dashboard.$('.o_graph_measures_list .dropdown-item:contains(Sold)'), 'selected',
                    "Measure on graph should not have changed");

        dashboard.destroy();

    });

    QUnit.test('rendering of aggregate with widget attribute (widget)', async function (assert) {
        assert.expect(1);

        var MyWidget = FieldFloat.extend({
            start: function () {
                this.$el.text('The value is ' + this._formatValue(this.value));
            },
        });
        fieldRegistry.add('test', MyWidget);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<aggregate name="some_value" field="sold" widget="test"/>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    return Promise.resolve([{some_value: 8}]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(dashboard.$('.o_value:visible').text(), 'The value is 8.00',
            "should have used the specified widget (as there is no 'test' formatter)");

        dashboard.destroy();
        delete fieldRegistry.map.test;
    });

    QUnit.test('rendering of aggregate with widget attribute (widget) and comparison active', async function (assert) {
        assert.expect(16);

        var MyWidget = FieldFloat.extend({
            start: function () {
                this.$el.text('The value is ' + this._formatValue(this.value));
            },
        });
        fieldRegistry.add('test', MyWidget);

        var nbReadGroup = 0;

        const unpatchDate = patchDate(2017, 2, 22, 1, 0, 0);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: '<dashboard>' +
                    '<aggregate name="some_value" field="sold" string="Some Value" widget="test"/>' +
                '</dashboard>',
            archs: {
                'test_time_range,false,search': `
                    <search>
                        <filter name="date" date="date" string="Date"/>
                    </search>
                `,
            },
            mockRPC: function (route, args) {
                var def = this._super.apply(this, arguments);
                if (args.method === 'read_group') {
                    nbReadGroup++;
                    if (nbReadGroup === 1) {
                        assert.deepEqual(args.kwargs.fields, ['some_value:sum(sold)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, [],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                        return def.then(function (result) {
                            result[0].some_value = 8;
                            return result;
                        });
                    }
                    if (nbReadGroup === 2 || nbReadGroup === 3) {
                        assert.deepEqual(args.kwargs.fields, ['some_value:sum(sold)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, ["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                        return def.then(function (result) {
                            // this is not the real value computed from data
                            result[0].some_value = 16;
                            return result;
                        });
                    }
                    if (nbReadGroup === 4) {
                        assert.deepEqual(args.kwargs.fields, ['some_value:sum(sold)'],
                            "should read the correct field");
                        assert.deepEqual(args.kwargs.domain, ["&", ["date", ">=", "2017-02-01"], ["date", "<=", "2017-02-28"]],
                            "should send the correct domain");
                        assert.deepEqual(args.kwargs.groupby, [],
                            "should send the correct groupby");
                        return def.then(function (result) {
                            // this is not the real value computed from data
                            result[0].some_value = 4;
                            return result;
                        });
                    }
                }
                return def;
            },
        });


        assert.containsOnce(dashboard, '.o_aggregate .o_value');

        // Apply time range with today
        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'Date');
        await toggleMenuItemOption(dashboard.el, 'Date', 'March');
        assert.containsOnce(dashboard, '.o_aggregate .o_value');

        // Apply range with today and comparison with previous period
        await toggleComparisonMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'Date: Previous period');
        assert.strictEqual(dashboard.$('.o_aggregate .o_variation').text(), "300%");
        assert.strictEqual(dashboard.$('.o_aggregate .o_comparison').text(), "The value is 16.00 vs The value is 4.00");

        dashboard.destroy();
        delete fieldRegistry.map.test;
        unpatchDate();
    });

    QUnit.test('rendering of a cohort tag with comparison active', async function (assert) {
        assert.expect(1);

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: '<dashboard>' +
                    '<view type="cohort" ref="some_xmlid"/>' +
                '</dashboard>',
            archs: {
                'test_time_range,some_xmlid,cohort': '<cohort string="Cohort" date_start="date" date_stop="transformation_date" interval="week"/>',
                'test_time_range,false,search': `
                    <search>
                        <filter name="date" date="date" string="Date"/>
                    </search>
                `,
            },
        });

        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'Date');
        await toggleMenuItemOption(dashboard.el, 'Date', 'October');

        await toggleComparisonMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'Date: Previous period');

        // The test should be modified and extended.
        assert.strictEqual(dashboard.$('.o_legacy_cohort_view div.o_view_nocontent').length, 1);

        unpatchDate();
        dashboard.destroy();
    });

    QUnit.test('rendering of an aggregate with comparison active', async function (assert) {
        assert.expect(27);

        var nbReadGroup = 0;

        const unpatchDate = patchDate(2017, 2, 22, 1, 0, 0);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: '<dashboard>' +
                    '<group>' +
                        '<aggregate name="some_value" field="sold" string="Some Value"/>' +
                    '</group>' +
                '</dashboard>',
                archs: {
                    'test_time_range,false,search': `
                        <search>
                            <filter name="date" date="date" string="Date"/>
                        </search>
                    `,
                },
            mockRPC: function (route, args) {
                var def = this._super.apply(this, arguments);

                function _readGroup(expectedDomain, readGroupResult) {
                    assert.deepEqual(args.kwargs.fields, ['some_value:sum(sold)'], "should read the correct field");
                    assert.deepEqual(args.kwargs.domain, expectedDomain,
                        "should send the correct domain");
                    assert.deepEqual(args.kwargs.groupby, [],
                        "should send the correct groupby");
                    return def.then(function (result) {
                        // this is not the real value computed from data
                        result[0].some_value = readGroupResult;
                        return result;
                    });
                }

                if (args.method === 'read_group') {
                    nbReadGroup++;
                    if (nbReadGroup === 1) {
                        _readGroup([], 8);
                    }
                    if (nbReadGroup === 2 || nbReadGroup === 3) {
                        _readGroup(["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]], 16);
                    }
                    if (nbReadGroup === 4) {
                        _readGroup(["&", ["date", ">=", "2017-02-01"], ["date", "<=", "2017-02-28"]], 4);
                    }
                    if (nbReadGroup === 5) {
                        _readGroup(["&", ["date", ">=", "2017-03-01"], ["date", "<=", "2017-03-31"]], 4);
                    }
                    if (nbReadGroup === 6) {
                        _readGroup(["&", ["date", ">=", "2016-03-01"], ["date", "<=", "2016-03-31"]], 16);
                    }
                }
                return def;
            },
        });

        assert.strictEqual(dashboard.$('.o_aggregate .o_value').text().trim(), "8.00");

        // Apply time range with today
        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'Date');
        await toggleMenuItemOption(dashboard.el, 'Date', 'March');

        assert.strictEqual(dashboard.$('.o_aggregate .o_value').text().trim(), "16.00");
        assert.containsOnce(dashboard, '.o_aggregate .o_value');

        // Apply range with this month and comparison with previous period
        await toggleComparisonMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 'Date: Previous period');

        assert.strictEqual(dashboard.$('.o_aggregate .o_variation').text(), "300%");
        assert.hasClass(dashboard.$('.o_aggregate'), 'border-success');
        assert.strictEqual(dashboard.$('.o_aggregate .o_comparison').text(), "16.00 vs 4.00");

        // Apply range with this month and comparison with last year
        await toggleMenuItem(dashboard.el, 'Date: Previous year');
        assert.strictEqual(dashboard.$('.o_aggregate .o_variation').text(), "-75%");
        assert.hasClass(dashboard.$('.o_aggregate'), 'border-danger');
        assert.strictEqual(dashboard.$('.o_aggregate .o_comparison').text(), "4.00 vs 16.00");

        dashboard.destroy();
        unpatchDate();
    });

    QUnit.test('basic rendering of aggregates with big values', async function (assert) {
        assert.expect(12);

        var readGroupNo = -3;
        var results = [
            "0.02", "0.15", "1.52", "15.23", "152.35",
            "1.52k", "15.24k", "152.35k", "1.52M", "15.23M",
            "152.35M", "1.52G"];

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<group>' +
                            '<aggregate name="sold" field="sold" widget="monetary"/>' +
                        '</group>' +
                    '</dashboard>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    readGroupNo++;
                    return Promise.resolve([{sold: Math.pow(10, readGroupNo) * 1.52346}]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(dashboard.$('.o_value').text(), results.shift(),
            "should correctly display the aggregate's value");

        for (var i = 0; i < 11; i++) {
            await dashboard.update({});
            assert.strictEqual(dashboard.$('.o_value').text(), results.shift(),
                "should correctly display the aggregate's value");
        }

        dashboard.destroy();
    });

    QUnit.test('click on a non empty cell in an embedded pivot view redirects to a list view', async function (assert) {
        assert.expect(3);

        var dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<view type="pivot" ref="some_xmlid"/>' +
                    '</dashboard>',
            archs: {
                'test_report,some_xmlid,pivot': '<pivot>' +
                        '<field name="sold" type="measure"/>' +
                    '</pivot>',
                'test_report,false,form': '<form>' +
                        '<field name="sold"/>' +
                    '</form>',
                'test_report,false,list': '<list>' +
                        '<field name="sold"/>' +
                    '</list>',
                'test_report,false,search': '<search></search>',
            },
            intercepts: {
                do_action: function (ev) {
                    assert.step('do_action');
                    assert.deepEqual(ev.data.action, {
                        type: 'ir.actions.act_window',
                        name: "Untitled",
                        res_model: 'test_report',
                        views: [[false, "list"], [false, "form"]],
                        view_mode: 'list',
                        target: 'current',
                        context: {},
                        domain: [],
                    });
                },
            },
        });

        // Click on the unique pivot cell
        await testUtils.dom.click(dashboard.$('.o_legacy_pivot .o_pivot_cell_value'));

        // There should a unique do_action triggered.
        assert.verifySteps(['do_action']);

        dashboard.destroy();
    });

    QUnit.test('groupby selected within graph subview are not deleted when modifying search view content', async function (assert) {
        assert.expect(2);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: '<dashboard>' +
                        '<view type="graph" ref="some_xmlid"/>' +
                    '</dashboard>',
            archs: {
                'test_time_range,some_xmlid,graph': `<graph>
                        <field name="transformation_date" type="row" interval="day"/>
                        <field name="sold" type="measure"/>
                    </graph>`,
                'test_time_range,false,search': `
                    <search>
                        <filter string="float" name="positive" domain="[['sold', '>=', 2]]"/>
                    </search>`,
            },
        });
        const el = dashboard.el;

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(el.querySelectorAll('.o_graph_buttons button')[1]);
        await testUtils.dom.click(el.querySelectorAll('.o_graph_buttons .o_menu_item > a')[1]);
        await testUtils.dom.click(el.querySelectorAll('.o_graph_buttons .o_menu_item .o_item_option > a')[4]);
        assert.doesNotHaveClass(el.querySelectorAll('.o_graph_buttons .o_menu_item > a')[1], 'selected',
            'groupby should be unselected');
        await toggleFilterMenu(dashboard.el);
        await toggleMenuItem(dashboard.el, 0);

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        await testUtils.dom.click(el.querySelectorAll('.o_graph_buttons button')[1]);
        assert.doesNotHaveClass(el.querySelectorAll('.o_graph_buttons .o_menu_item > a')[1], 'selected',
            'groupby should be still unselected');
        dashboard.destroy();
    });

    QUnit.test('groupbys in "Group By" menu of graph subviews', async function (assert) {
        assert.expect(17);

        this.data.test_time_range.fields.categ_id.store = true;
        this.data.test_time_range.fields.categ_id.sortable = true;

        const groupBys = [
            [],
            ['categ_id'],
            ['categ_id', 'date:day'],
            ['categ_id', 'date:day'], //graph view keeps only finer option when fetching data
            ['date:day'],
            ['date:quarter'],
        ];

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_time_range',
            data: this.data,
            arch: '<dashboard><view type="graph" ref="some_xmlid"/></dashboard>',
            archs: {
                'test_time_range,some_xmlid,graph': '<graph>' +
                        '<field name="sold" type="measure"/>' +
                    '</graph>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.groupby, groupBys.shift(),
                        "should group by the correct field");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(dashboard, '.o_subview .o_graph_buttons',
            "should contain the buttons container");

        await testUtils.owlCompatibilityExtraNextTick(); // buttons (measure and group by menu) are not ready yet

        assert.containsOnce(dashboard, '.o_subview .o_graph_buttons .o_group_by_menu:contains("Group By")',
            "graph button should have been rendered");

        await cpHelpers.toggleGroupByMenu(dashboard.$el);

        await cpHelpers.toggleMenuItem(dashboard, 'categ_id');
        assert.ok(cpHelpers.isItemSelected(dashboard, 'categ_id'));

        await cpHelpers.toggleMenuItem(dashboard, 'Date');
        assert.notOk(cpHelpers.isItemSelected(dashboard, 'Date'));

        await cpHelpers.toggleMenuItemOption(dashboard, 'Date', 'Day');
        assert.ok(cpHelpers.isItemSelected(dashboard, 'Date'));
        assert.ok(cpHelpers.isOptionSelected(dashboard, 'Date', 'Day'));

        await cpHelpers.toggleMenuItemOption(dashboard, 'Date', 'Quarter');
        assert.ok(cpHelpers.isOptionSelected(dashboard, 'Date', 'Day'));
        assert.ok(cpHelpers.isOptionSelected(dashboard, 'Date', 'Quarter'));

        await cpHelpers.toggleMenuItem(dashboard, 'categ_id');
        await cpHelpers.toggleMenuItem(dashboard, 'Date'); // re-open the 'Date' section
        assert.notOk(cpHelpers.isItemSelected(dashboard, 'categ_id'));

        await cpHelpers.toggleMenuItemOption(dashboard, 'Date', 'Day');
        assert.notOk(cpHelpers.isOptionSelected(dashboard, 'Date', 'Day'));
        assert.ok(cpHelpers.isOptionSelected(dashboard, 'Date', 'Quarter'));

        dashboard.destroy();
    });

    QUnit.test('empty dashboard view with sub views', async function (assert) {
        assert.expect(7);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard>
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>`,
            archs: {
                'test_report,false,graph': '<graph><field name="categ_id"/></graph>',
                'test_report,false,pivot': '<pivot><field name="categ_id" type="row"/></pivot>',
            },
            domain: [['id', '<', 0]],
            viewOptions: {
                action: {
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.containsOnce(dashboard, '.o_subview[type=graph] canvas');
        assert.containsOnce(dashboard, '.o_subview[type=pivot] .o_view_nocontent');
        assert.containsNone(dashboard, '.o_subview[type=pivot] .o_view_nocontent .abc');
        assert.containsNone(dashboard, '.o_view_nocontent .abc');

        await dashboard.reload({ domain: [] });

        assert.containsOnce(dashboard, '.o_subview[type=graph] canvas');
        assert.containsOnce(dashboard, '.o_subview[type=pivot] table');
        assert.containsNone(dashboard, '.o_view_nocontent .abc');

        dashboard.destroy();
    });

    QUnit.test('empty dashboard view with sub views and sample data', async function (assert) {
        assert.expect(9);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard sample="1">
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>`,
            archs: {
                'test_report,false,graph': '<graph><field name="categ_id"/></graph>',
                'test_report,false,pivot': '<pivot><field name="categ_id" type="row"/></pivot>',
            },
            domain: [['id', '<', 0]],
            viewOptions: {
                action: {
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.hasClass(dashboard.el, 'o_view_sample_data');
        assert.containsOnce(dashboard, '.o_subview[type=graph] canvas');
        assert.containsOnce(dashboard, '.o_subview[type=pivot] table');
        assert.containsOnce(dashboard, '.o_view_nocontent .abc');

        await dashboard.reload({ domain: [['id', '<', -10]] }); // new domain, still matching nothing

        assert.doesNotHaveClass(dashboard.el, 'o_view_sample_data');
        assert.containsOnce(dashboard, '.o_subview[type=graph] canvas');
        assert.containsOnce(dashboard, '.o_subview[type=pivot] .o_view_nocontent');
        assert.containsNone(dashboard, '.o_subview[type=pivot] .o_view_nocontent .abc');
        assert.containsNone(dashboard, '.o_view_nocontent .abc');

        dashboard.destroy();
    });

    QUnit.test('non empty dashboard view with sub views and sample data', async function (assert) {
        assert.expect(9);

        const dashboard = await createView({
            View: DashboardView,
            model: 'test_report',
            data: this.data,
            arch: `
                <dashboard sample="1">
                    <view type="graph"/>
                    <view type="pivot"/>
                </dashboard>`,
            archs: {
                'test_report,false,graph': '<graph><field name="categ_id"/></graph>',
                'test_report,false,pivot': '<pivot><field name="categ_id" type="row"/></pivot>',
            },
            viewOptions: {
                action: {
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.doesNotHaveClass(dashboard.el, 'o_view_sample_data');
        assert.containsOnce(dashboard, '.o_subview[type=graph] canvas');
        assert.containsOnce(dashboard, '.o_subview[type=pivot] table');
        assert.containsNone(dashboard, '.o_view_nocontent .abc');

        await dashboard.reload({ domain: [['id', '<', 0]] });

        assert.doesNotHaveClass(dashboard.el, 'o_view_sample_data');
        assert.containsOnce(dashboard, '.o_subview[type=graph] canvas');
        assert.containsOnce(dashboard, '.o_subview[type=pivot] .o_view_nocontent');
        assert.containsNone(dashboard, '.o_subview[type=pivot] .o_view_nocontent .abc');
        assert.containsNone(dashboard, '.o_view_nocontent .abc');

        dashboard.destroy();
    });

    QUnit.test("correctly transition from legacy to a wowl view -- emulates a legacy dashboard within a board.board", async (assert) => {
        assert.expect(4);

        const DashboardLegacy = DashboardView.extend({
            withControlPanel: false,
            withSearchPanel: false,
        });

        viewRegistry.remove("dashboard");
        legacyViewRegistry.add("dashboard", DashboardLegacy);

        serverData.actions = {};
        serverData.views = {};

        serverData.actions[213] = {
            type: "ir.actions.act_window",
            res_model: "test_report",
            views: [[999, "dashboard"]],
            search_view_id: 1000,
            context: { search_default_my_filter: true },
        };

        serverData.views["test_report,999,dashboard"] = `<dashboard><view type="graph"/></dashboard>`;
        serverData.views["test_report,1000,search"] = `<search><filter name="my_filter" domain="[('name', '=', 'Jackie Brown')]"/></search>`;

        serverData.views["test_report,false,graph"] = `<graph/>`;

        let testActive = false;
        const mockRPC = (route, args) => {
            if (testActive && args.method === "web_read_group") {
                assert.deepEqual(args.kwargs.domain, [["name", "=", "Jackie Brown"]]);
            }
        }

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 213);

        assert.containsOnce(webClient, ".o_legacy_dashboard_view");

        testActive = true;
        await click(webClient.el.querySelector(".o_button_switch"));
        assert.containsNone(webClient, ".o_legacy_dashboard_view");
        assert.containsOnce(webClient, ".o_graph_view");
    });
});
});
