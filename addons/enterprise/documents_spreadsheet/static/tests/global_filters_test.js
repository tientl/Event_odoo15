/** @odoo-module alias=documents_spreadsheet.PivotGlobalFilterTests */
/* global $ moment */

import testUtils from "web.test_utils";
import CommandResult from "../src/js/o_spreadsheet/plugins/cancelled_reason";
import spreadsheet from "documents_spreadsheet.spreadsheet";
import {
    createSpreadsheetFromPivot,
    setCellContent,
    getCellFormula,
    getCellValue,
    createSpreadsheetWithPivotAndList,
    addGlobalFilter,
    removeGlobalFilter,
    editGlobalFilter,
    setGlobalFilterValue,
    waitForEvaluation,
} from "./spreadsheet_test_utils";

import { getBasicPivotArch, getBasicData } from "./spreadsheet_test_data";

const { Model, DispatchResult } = spreadsheet;
const { cellMenuRegistry } = spreadsheet.registries;
const { module, test } = QUnit;

const LAST_YEAR_FILTER = {
    filter: {
        id: "42",
        type: "date",
        label: "Last Year",
        defaultValue: { year: "last_year" },
        pivotFields: { 1: { field: "date", type: "date" } },
        listFields: { 1: { field: "date", type: "date" } },
    },
};

const THIS_YEAR_FILTER = {
    filter: {
        type: "date",
        label: "This Year",
        defaultValue: { year: "this_year" },
        pivotFields: { 1: { field: "date", type: "date" } },
        listFields: { 1: { field: "date", type: "date" } },
    },
};

module(
    "documents_spreadsheet > global_filters",
    {
        beforeEach() {
            this.data = getBasicData();
            this.arch = getBasicPivotArch();
        },
    },
    () => {
        test("Can add a global filter", async function (assert) {
            assert.expect(4);

            const { model } = await createSpreadsheetWithPivotAndList();
            assert.equal(model.getters.getGlobalFilters().length, 0);
            await addGlobalFilter(model, LAST_YEAR_FILTER);
            assert.equal(model.getters.getGlobalFilters().length, 1);
            const computedDomain = model.getters.getPivotComputedDomain("1");
            assert.equal(computedDomain.length, 3);
            assert.equal(computedDomain[0], "&");
        });

        test("Can delete a global filter", async function (assert) {
            assert.expect(4);

            const { model } = await createSpreadsheetWithPivotAndList();
            let result = await removeGlobalFilter(model, 1);
            assert.deepEqual(result.reasons, [
                CommandResult.FilterNotFound,
            ]);
            await addGlobalFilter(model, LAST_YEAR_FILTER);
            const gf = model.getters.getGlobalFilters()[0];
            result = await removeGlobalFilter(model, gf.id);
            assert.deepEqual(result, DispatchResult.Success);
            assert.equal(model.getters.getGlobalFilters().length, 0);
            const computedDomain = model.getters.getPivotComputedDomain("1");
            assert.equal(computedDomain.length, 0);
        });

        test("Can edit a global filter", async function (assert) {
            assert.expect(4);

            const { model } = await createSpreadsheetWithPivotAndList();
            const gfDef = { ...THIS_YEAR_FILTER, id: 1 };
            let result = await editGlobalFilter(model, gfDef);
            assert.deepEqual(result.reasons, [
                CommandResult.FilterNotFound,
            ]);
            await addGlobalFilter(model, LAST_YEAR_FILTER);
            const gf = model.getters.getGlobalFilters()[0];
            gfDef.id = gf.id;
            result = await editGlobalFilter(model, gfDef);
            assert.deepEqual(result, DispatchResult.Success);
            assert.equal(model.getters.getGlobalFilters().length, 1);
            assert.deepEqual(model.getters.getGlobalFilters()[0].defaultValue.year, "this_year");
        });

        test("Create a new date filter", async function (assert) {
            assert.expect(14);

            const { webClient, model } = await createSpreadsheetFromPivot({
                pivotView: {
                    arch: `
                    <pivot string="Partners">
                        <field name="date" interval="month" type="row"/>
                        <field name="id" type="col"/>
                        <field name="probability" type="measure"/>
                    </pivot>
                `,
                },
            });
            await testUtils.nextTick();
            const searchIcon = $(webClient.el).find(".o_topbar_filter_icon")[0];
            await testUtils.dom.click(searchIcon);
            const newDate = $(webClient.el).find(".o_global_filter_new_time")[0];
            await testUtils.dom.click(newDate);
            assert.equal($(webClient.el).find(".o-sidePanel").length, 1);

            const label = $(webClient.el).find(".o_global_filter_label")[0];
            await testUtils.fields.editInput(label, "My Label");

            const range = $(webClient.el).find(".o_input:nth-child(2)")[0];
            await testUtils.fields.editAndTrigger(range, "month", ["change"]);

            const filterValues = $(webClient.el).find(".date_filter_values .o_input")[0];
            await testUtils.dom.click(filterValues);

            assert.equal($(webClient.el).find(".date_filter_values .o_input").length, 2);
            const month = $(webClient.el).find(".date_filter_values .o_input:nth-child(1)")[0];
            assert.equal(month.length, 13);
            const year = $(webClient.el).find(".date_filter_values .o_input:nth-child(2)")[0];
            assert.equal(year.length, 4);

            await testUtils.fields.editAndTrigger(month, "october", ["change"]);
            assert.equal(year.length, 3);

            await testUtils.fields.editAndTrigger(year, "this_year", ["change"]);

            $($(webClient.el).find(".o_field_selector_value")[0]).focusin();
            await testUtils.dom.click($(webClient.el).find(".o_field_selector_select_button")[0]);

            const save = $(webClient.el).find(
                ".o_spreadsheet_filter_editor_side_panel .o_global_filter_save"
            )[0];
            await testUtils.dom.click(save);

            assert.equal(
                $(webClient.el).find(".o_spreadsheet_global_filters_side_panel").length,
                1
            );
            const globalFilter = model.getters.getGlobalFilters()[0];
            assert.equal(globalFilter.label, "My Label");
            assert.equal(globalFilter.defaultValue.year, "this_year");
            assert.equal(globalFilter.defaultValue.period, "october");
            assert.equal(globalFilter.rangeType, "month");
            assert.equal(globalFilter.type, "date");
            const currentYear = new Date().getFullYear();
            const computedDomain = model.getters.getPivotComputedDomain("1");
            assert.deepEqual(computedDomain[0], "&");
            assert.deepEqual(computedDomain[1], ["date", ">=", currentYear + "-10-01"]);
            assert.deepEqual(computedDomain[2], ["date", "<=", currentYear + "-10-31"]);
        });

        test("Create a new date filter without specifying the year", async function (assert) {
            assert.expect(9);
            const { webClient, model } = await createSpreadsheetFromPivot({
                pivotView: {
                    arch: `
                        <pivot string="Partners">
                            <field name="date" interval="month" type="row"/>
                            <field name="id" type="col"/>
                            <field name="probability" type="measure"/>
                        </pivot>
                        `,
                }
            });
            await testUtils.nextTick();
            const searchIcon = $(webClient.el).find(".o_topbar_filter_icon")[0];
            await testUtils.dom.click(searchIcon);
            const newDate = $(webClient.el).find(".o_global_filter_new_time")[0];
            await testUtils.dom.click(newDate);
            assert.equal($(webClient.el).find(".o-sidePanel").length, 1);

            const label = $(webClient.el).find(".o_global_filter_label")[0];
            await testUtils.fields.editInput(label, "My Label");

            const range = $(webClient.el).find(".o_input:nth-child(2)")[0];
            await testUtils.fields.editAndTrigger(range, "month", ["change"]);

            const filterValues = $(webClient.el).find(".date_filter_values .o_input")[0];
            await testUtils.dom.click(filterValues);

            assert.equal($(webClient.el).find(".date_filter_values .o_input").length, 2);
            const month = $(webClient.el).find(".date_filter_values .o_input:nth-child(1)")[0];
            assert.equal(month.length, 13);
            const year = $(webClient.el).find(".date_filter_values .o_input:nth-child(2)")[0];
            assert.equal(year.length, 4);

            await testUtils.fields.editAndTrigger(month, "november", ["change"]);
            // intentionally skip the year input

            $($(webClient.el).find(".o_field_selector_value")[0]).focusin();
            await testUtils.dom.click($(webClient.el).find(".o_field_selector_select_button")[0]);

            const save = $(webClient.el).find(
                ".o_spreadsheet_filter_editor_side_panel .o_global_filter_save"
            )[0];
            await testUtils.dom.click(save);

            const globalFilter = model.getters.getGlobalFilters()[0];
            assert.equal(globalFilter.label, "My Label");
            assert.equal(globalFilter.defaultValue.year, "this_year");
            assert.equal(globalFilter.defaultValue.period, "november");
            assert.equal(globalFilter.rangeType, "month");
            assert.equal(globalFilter.type, "date");
        });

        test("Readonly user can update text filter values",  async function (assert) {
            assert.expect(5);
            const { webClient, model } = await createSpreadsheetFromPivot({
                pivotView: {
                    arch: `
                        <pivot string="Partners">
                            <field name="name" type="col"/>
                            <field name="date" interval="month" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>
                    `,
                }
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Text Filter",
                    defaultValue: "abc",
                    pivotFields: {},
                    listFields: {}
                },
            });
            model.updateReadOnly(true);
            await testUtils.nextTick();

            const searchIcon = webClient.el.querySelector(".o_topbar_filter_icon");
            await testUtils.dom.click(searchIcon);

            const pivots = webClient.el.querySelectorAll(".pivot_filter_section");
            assert.containsOnce(webClient, ".pivot_filter_section");
            assert.containsNone(webClient, "i.o_side_panel_filter_icon");
            assert.equal(pivots[0].querySelector(".o_side_panel_filter_label").textContent, "Text Filter");

            const input = pivots[0].querySelector(".pivot_filter_input input");
            assert.equal(input.value, "abc");

            await testUtils.fields.editAndTrigger(input, "something", ["change"]);

            assert.equal(model.getters.getGlobalFilterValue("42"), "something");
        })

        test("Readonly user can update date filter values",  async function (assert) {
            assert.expect(9);
            const { webClient, model } = await createSpreadsheetFromPivot({
                arch: `
                    <pivot string="Partners">
                        <field name="name" type="col"/>
                        <field name="date" interval="month" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>
                `,
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "43",
                    type: "date",
                    label: "Date Filter",
                    rangeType: "quarter",
                    defaultValue: {year: "this_year", period: "fourth_quarter"},
                    pivotFields: {1: {field: "date", type: "date"}},
                    listFields: {}
                },
            });
            model.updateReadOnly(true);
            await testUtils.nextTick();

            const searchIcon = webClient.el.querySelector(".o_topbar_filter_icon");
            await testUtils.dom.click(searchIcon);
            await testUtils.nextTick();

            const pivots = webClient.el.querySelectorAll(".pivot_filter_section");
            assert.containsOnce(webClient, ".pivot_filter_section");
            assert.containsNone(webClient, "i.o_side_panel_filter_icon");
            assert.equal(pivots[0].querySelector(".o_side_panel_filter_label").textContent, "Date Filter");

            const selections = pivots[0].querySelectorAll(".pivot_filter_input div.date_filter_values select");
            assert.containsN(pivots[0], ".pivot_filter_input div.date_filter_values select", 2);

            const [quarter, year] = selections;
            assert.equal(quarter.value, "fourth_quarter");
            assert.equal(year.value, "this_year");

            await testUtils.fields.editSelect(quarter, "second_quarter");
            await testUtils.fields.editSelect(year, "last_year");

            assert.equal(quarter.value, "second_quarter");
            assert.equal(year.value, "last_year");

            assert.deepEqual(model.getters.getGlobalFilterValue("43"), {year: "last_year", period: "second_quarter"});
        })

        test("Readonly user can update relation filter values",  async function (assert) {
            assert.expect(8);
            const tagSelector = ".o_field_many2manytags .badge";
            const { webClient, model } = await createSpreadsheetFromPivot({
                arch: `
                    <pivot string="Partners">
                        <field name="name" type="col"/>
                        <field name="date" interval="month" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>
                `,
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                    modelName: "product",
                    defaultValue: [41],
                    pivotFields: {1: {field: "product_id", type: "many2one"}},
                    listFields: {}
                },
            });
            assert.equal(model.getters.getGlobalFilters().length, 1);
            model.updateReadOnly(true);
            await testUtils.nextTick();

            const searchIcon = webClient.el.querySelector(".o_topbar_filter_icon");
            await testUtils.dom.click(searchIcon);

            const pivot = webClient.el.querySelector(".pivot_filter_section");
            assert.containsOnce(webClient, ".pivot_filter_section");
            assert.containsNone(webClient, "i.o_side_panel_filter_icon");
            assert.equal(pivot.querySelector(".o_side_panel_filter_label").textContent, "Relation Filter");
            assert.containsOnce(pivot, tagSelector);
            assert.deepEqual([...pivot.querySelectorAll(tagSelector)].map(el => el.textContent.trim()), ['xpad']);

            await testUtils.dom.click(pivot.querySelector('.pivot_filter_input input.ui-autocomplete-input'));
            await testUtils.dom.click(document.querySelector('ul.ui-autocomplete li:first-child'));

            assert.containsN(pivot, tagSelector, 2);
            assert.deepEqual([...pivot.querySelectorAll(tagSelector)].map(el => el.textContent.trim()), ['xpad', 'xphone']);
        })

        test("Cannot have duplicated names", async function (assert) {
            assert.expect(6);

            const { model } = await createSpreadsheetWithPivotAndList();
            const filter = { ...THIS_YEAR_FILTER.filter, label: "Hello" };
            await addGlobalFilter(model, { filter });
            assert.equal(model.getters.getGlobalFilters().length, 1);

            // Add filter with same name
            let result = await addGlobalFilter(model , { filter: { ...filter, id: "456" } });
            assert.deepEqual(result.reasons, [CommandResult.DuplicatedFilterLabel]);
            assert.equal(model.getters.getGlobalFilters().length, 1);
            await waitForEvaluation(model);

            // Edit to set same name as other filter
            await addGlobalFilter(model, {
                filter: { ...filter, id: "789", label: "Other name" },
            });
            assert.equal(model.getters.getGlobalFilters().length, 2);
            result = await editGlobalFilter(model, {
                id: "789",
                filter: { ...filter, label: "Hello" },
            });
            assert.deepEqual(result.reasons, [CommandResult.DuplicatedFilterLabel]);

            // Edit to set same name
            result = await editGlobalFilter(model, {
                id: "789",
                filter: { ...filter, label: "Other name" },
            });
            assert.deepEqual(result, DispatchResult.Success);
        });

        test("Can name/rename filters with special characters", async function (assert) {
            assert.expect(5);
            const { model } = await createSpreadsheetFromPivot({
                arch: `
                    <pivot string="Partners">
                        <field name="name" type="col"/>
                        <field name="date" interval="month" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>
                `,
            });
            const filter = Object.assign({}, THIS_YEAR_FILTER.filter, { label: "{my} We)ird. |*ab(el []" });
            let result = model.dispatch("ADD_GLOBAL_FILTER", { filter });
            assert.deepEqual(result, DispatchResult.Success);
            assert.equal(model.getters.getGlobalFilters().length, 1);

            const filterId = model.getters.getGlobalFilters()[0].id;

            // Edit to set another name with special characters
            result = model.dispatch("EDIT_PIVOT_FILTER", {id: filterId, filter: Object.assign({}, filter, { label: "+Othe^ we?rd name+$" }) });
            assert.deepEqual(result, DispatchResult.Success);

            result = model.dispatch("EDIT_PIVOT_FILTER", {id: filterId, filter: Object.assign({}, filter, { label: "normal name" }) });
            assert.deepEqual(result, DispatchResult.Success);

            result = model.dispatch("EDIT_PIVOT_FILTER", {id: filterId, filter: Object.assign({}, filter, { label: "?ack +.* to {my} We)ird. |*ab(el []" }) });
            assert.deepEqual(result, DispatchResult.Success);
        });

        test("Can save a value to an existing global filter", async function (assert) {
            assert.expect(8);

            const { model } = await createSpreadsheetWithPivotAndList();
            await addGlobalFilter(model, LAST_YEAR_FILTER);
            const gf = model.getters.getGlobalFilters()[0];
            let result = await setGlobalFilterValue(model, {
                id: gf.id,
                value: { period: "last_month" },
            });
            assert.deepEqual(result, DispatchResult.Success);
            assert.equal(model.getters.getGlobalFilters().length, 1);
            assert.deepEqual(model.getters.getGlobalFilterDefaultValue(gf.id).year, "last_year");
            assert.deepEqual(model.getters.getGlobalFilterValue(gf.id).period, "last_month");
            result = await setGlobalFilterValue(model, {
                id: gf.id,
                value: { period: "this_month" },
            });
            assert.deepEqual(result, DispatchResult.Success);
            assert.deepEqual(model.getters.getGlobalFilterValue(gf.id).period, "this_month");
            const computedDomain = model.getters.getPivotComputedDomain("1");
            assert.equal(computedDomain.length, 3);
            const listDomain = model.getters.getListComputedDomain("1");
            assert.equal(listDomain.length, 3);
        });

        test("Can export/import filters", async function (assert) {
            assert.expect(5);

            const { model, env } = await createSpreadsheetWithPivotAndList();
            await addGlobalFilter(model, LAST_YEAR_FILTER);
            const newModel = new Model(model.exportData(), {
                evalContext: { env },
            });
            assert.equal(newModel.getters.getGlobalFilters().length, 1);
            const [filter] = newModel.getters.getGlobalFilters();
            assert.deepEqual(filter.defaultValue.year, "last_year");
            assert.deepEqual(
                newModel.getters.getGlobalFilterValue(filter.id).year,
                "last_year",
                "it should have applied the default value"
            );

            const computedDomain = newModel.getters.getPivotComputedDomain("1");
            assert.equal(computedDomain.length, 3, "it should have updated the pivot domain");
            const listDomain = newModel.getters.getListComputedDomain("1");
            assert.equal(listDomain.length, 3, "it should have updated the list domain");
        });

        test("Relational filter with undefined value", async function (assert) {
            assert.expect(1);

            const { model } = await createSpreadsheetFromPivot();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                    pivotFields: {
                        1: {
                            field: "foo",
                            type: "char",
                        },
                    },
                },
            });
            const [filter] = model.getters.getGlobalFilters();
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: undefined,
            });
            const computedDomain = model.getters.getPivotComputedDomain("1");
            assert.equal(computedDomain.length, 0, "it should not have updated the pivot domain");
        });

        test("Get active filters with multiple filters", async function (assert) {
            assert.expect(2);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Text Filter",
                },
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "43",
                    type: "date",
                    label: "Date Filter",
                    rangeType: "quarter",
                },
            });
            await addGlobalFilter(model, {
                filter: {
                    id: "44",
                    type: "relation",
                    label: "Relation Filter",
                },
            });
            const [text] = model.getters.getGlobalFilters();
            assert.equal(model.getters.getActiveFilterCount(), false);
            await setGlobalFilterValue(model, {
                id: text.id,
                value: "Hello",
            });
            assert.equal(model.getters.getActiveFilterCount(), true);
        });

        test("Get active filters with text filter enabled", async function (assert) {
            assert.expect(2);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Text Filter",
                },
            });
            const [filter] = model.getters.getGlobalFilters();
            assert.equal(model.getters.getActiveFilterCount(), false);
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: "Hello",
            });
            assert.equal(model.getters.getActiveFilterCount(), true);
        });

        test("Get active filters with relation filter enabled", async function (assert) {
            assert.expect(2);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                },
            });
            const [filter] = model.getters.getGlobalFilters();
            assert.equal(model.getters.getActiveFilterCount(), false);
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: [1],
            });
            assert.equal(model.getters.getActiveFilterCount(), true);
        });

        test("Get active filters with date filter enabled", async function (assert) {
            assert.expect(4);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "date",
                    label: "Date Filter",
                    rangeType: "quarter",
                },
            });
            const [filter] = model.getters.getGlobalFilters();
            assert.equal(model.getters.getActiveFilterCount(), false);
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: {
                    year: "this_year",
                    period: undefined,
                },
            });
            assert.equal(model.getters.getActiveFilterCount(), true);
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: {
                    year: undefined,
                    period: "first_quarter",
                },
            });
            assert.equal(model.getters.getActiveFilterCount(), true);
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: {
                    year: "this_year",
                    period: "first_quarter",
                },
            });
            assert.equal(model.getters.getActiveFilterCount(), true);
        });

        test("FILTER.VALUE text filter", async function (assert) {
            assert.expect(3);

            const model = new Model();
            setCellContent(model, "A10", `=FILTER.VALUE("Text Filter")`);
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), "#ERROR");
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Text Filter",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), "");
            const [filter] = model.getters.getGlobalFilters();
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: "Hello",
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), "Hello");
        });

        test("FILTER.VALUE date filter", async function (assert) {
            assert.expect(4);

            const model = new Model();
            setCellContent(model, "A10", `=FILTER.VALUE("Date Filter")`);
            await testUtils.nextTick();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "date",
                    label: "Date Filter",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            await testUtils.nextTick();
            const [filter] = model.getters.getGlobalFilters();
            await setGlobalFilterValue(model, {
                id: filter.id,
                rangeType: "quarter",
                value: {
                    year: "this_year",
                    period: "first_quarter",
                },
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), `Q1 ${moment().year()}`);
            await setGlobalFilterValue(model, {
                id: filter.id,
                rangeType: "year",
                value: {
                    year: "this_year",
                },
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), `${moment().year()}`);
            await setGlobalFilterValue(model, {
                id: filter.id,
                rangeType: "year",
                value: {
                    period: "january",
                    year: "this_year",
                },
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), `01/${moment().year()}`);
            await setGlobalFilterValue(model, {
                id: filter.id,
                rangeType: "year",
                value: {},
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), ``);
        });

        test("FILTER.VALUE relation filter", async function (assert) {
            assert.expect(6);

            const model = new Model(
                {},
                {
                    evalContext: {
                        env: {
                            services: {
                                orm: {
                                    call: async (model, method, args) => {
                                        const resId = args[0][0];
                                        assert.step(`name_get_${resId}`);
                                        return resId === 1
                                            ? [[1, "Jean-Jacques"]]
                                            : [[2, "Raoul Grosbedon"]];
                                    },
                                },
                            },
                        },
                    },
                }
            );
            setCellContent(model, "A10", `=FILTER.VALUE("Relation Filter")`);
            await testUtils.nextTick();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                    modelName: "partner",
                },
            });
            await testUtils.nextTick();
            const [filter] = model.getters.getGlobalFilters();

            // One record; displayNames not defined => rpc
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: [1],
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), "Jean-Jacques");

            // Two records; displayNames defined => no rpc
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: [1, 2],
                displayNames: ["Jean-Jacques", "Raoul Grosbedon"],
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), "Jean-Jacques, Raoul Grosbedon");

            // another record; displayNames not defined => rpc
            await setGlobalFilterValue(model, {
                id: filter.id,
                value: [2],
            });
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A10"), "Raoul Grosbedon");
            assert.verifySteps(["name_get_1", "name_get_2"]);
        });

        test("FILTER.VALUE formulas are updated when filter label is changed", async function (assert) {
            assert.expect(1);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "date",
                    label: "Cuillère",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            setCellContent(model, "A10", `=FILTER.VALUE("Cuillère") & FILTER.VALUE( "Cuillère" )`);
            const [filter] = model.getters.getGlobalFilters();
            const newFilter = {
                type: "date",
                label: "Interprete",
                pivotFields: {
                    1: {
                        field: "name",
                        type: "char",
                    },
                },
            };
            await editGlobalFilter(model, { id: filter.id, filter: newFilter });
            assert.equal(
                getCellFormula(model, "A10"),
                `=FILTER.VALUE("Interprete") & FILTER.VALUE("Interprete")`
            );
        });

        test("Exporting data does not remove value from model", async function (assert) {
            assert.expect(2);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Cuillère",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            await setGlobalFilterValue(model, {
                id: "42",
                value: "Hello export bug",
            });
            const [filter] = model.getters.getGlobalFilters();
            assert.equal(model.getters.getGlobalFilterValue(filter.id), "Hello export bug");
            model.exportData();
            assert.equal(model.getters.getGlobalFilterValue(filter.id), "Hello export bug");
        });

        test("Re-insert a pivot with a global filter should re-insert the full pivot", async function (assert) {
            assert.expect(1);

            const { model, env } = await createSpreadsheetFromPivot({
                pivotView: {
                    model: "partner",
                    data: this.data,
                    arch: `
                <pivot string="Partners">
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
                },
            });
            await waitForEvaluation(model);
            await addGlobalFilter(model, {
                filter: {
                    id: "41",
                    type: "relation",
                    label: "41",
                    defaultValue: [41],
                    pivotFields: { 1: { field: "product_id", type: "many2one" } },
                },
            });
            await waitForEvaluation(model);
            model.dispatch("SELECT_CELL", { col: 0, row: 5 });
            const root = cellMenuRegistry.getAll().find((item) => item.id === "reinsert_pivot");
            const reinsertPivot = cellMenuRegistry.getChildren(root, env)[0];
            await reinsertPivot.action(env);
            await testUtils.nextTick();
            assert.equal(getCellFormula(model, "B6"), getCellFormula(model, "B1"));
        });

        test("Can undo-redo a ADD_GLOBAL_FILTER", async function (assert) {
            assert.expect(3);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Cuillère",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            assert.equal(model.getters.getGlobalFilters().length, 1);
            model.dispatch("REQUEST_UNDO");
            assert.equal(model.getters.getGlobalFilters().length, 0);
            model.dispatch("REQUEST_REDO");
            assert.equal(model.getters.getGlobalFilters().length, 1);
        });

        test("Can undo-redo a REMOVE_GLOBAL_FILTER", async function (assert) {
            assert.expect(3);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Cuillère",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            await removeGlobalFilter(model, "42");
            assert.equal(model.getters.getGlobalFilters().length, 0);
            model.dispatch("REQUEST_UNDO");
            assert.equal(model.getters.getGlobalFilters().length, 1);
            model.dispatch("REQUEST_REDO");
            assert.equal(model.getters.getGlobalFilters().length, 0);
        });

        test("Can undo-redo a EDIT_GLOBAL_FILTER", async function (assert) {
            assert.expect(3);

            const model = new Model();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "text",
                    label: "Cuillère",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            await editGlobalFilter(model, {
                id: "42",
                filter: {
                    id: "42",
                    type: "text",
                    label: "Arthouuuuuur",
                    pivotFields: {
                        1: {
                            field: "name",
                            type: "char",
                        },
                    },
                },
            });
            assert.equal(model.getters.getGlobalFilters()[0].label, "Arthouuuuuur");
            model.dispatch("REQUEST_UNDO");
            assert.equal(model.getters.getGlobalFilters()[0].label, "Cuillère");
            model.dispatch("REQUEST_REDO");
            assert.equal(model.getters.getGlobalFilters()[0].label, "Arthouuuuuur");
        });

        test("Changing the range of a date global filter reset the default value", async function (assert) {
            assert.expect(1);

            const { webClient, model } = await createSpreadsheetFromPivot();
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "date",
                    rangeType: "month",
                    label: "This month",
                    pivotFields: {
                        1: { field: "create_date", type: "datetime" },
                    },
                    defaultValue: {
                        period: "january",
                    },
                },
            });
            const searchIcon = $(webClient.el).find(".o_topbar_filter_icon")[0];
            await testUtils.dom.click(searchIcon);
            const editFilter = $(webClient.el).find(".o_side_panel_filter_icon");
            await testUtils.dom.click(editFilter);
            const options = $(webClient.el).find(
                ".o_spreadsheet_filter_editor_side_panel .o_side_panel_section"
            )[1];
            options
                .querySelector("select option[value='year']")
                .setAttribute("selected", "selected");
            await testUtils.dom.triggerEvent(options.querySelector("select"), "change");
            await testUtils.nextTick();
            await testUtils.dom.click($(webClient.el).find(".o_global_filter_save")[0]);
            await testUtils.nextTick();
            assert.deepEqual(model.getters.getGlobalFilters()[0].defaultValue, {});
        });

        test("Changing the range of a date global filter reset the current value", async function (assert) {
          const { webClient, model } = await createSpreadsheetFromPivot();
          await addGlobalFilter(model, {
            filter: {
              id: "42",
              type: "date",
              rangeType: "month",
              label: "This month",
              pivotFields: {
                1: { field: "create_date", type: "datetime" },
              },
              defaultValue: {
                period: "january",
              },
            },
          });
          const searchIcon = webClient.el.querySelector(
            ".o_topbar_filter_icon"
          );
          await testUtils.dom.click(searchIcon);

          // Edit filter value in filters list
          const optionInFilterList = webClient.el.querySelector(
            ".pivot_filter select"
          );
          optionInFilterList
            .querySelector("select option[selected='1']")
            .setAttribute("selected", "0");
          optionInFilterList
            .querySelector("select option[value='february']")
            .setAttribute("selected", "1");
          await testUtils.dom.triggerEvent(optionInFilterList, "change");
          await testUtils.nextTick();
          const editFilter = webClient.el.querySelector(
            ".o_side_panel_filter_icon"
          );

           // Edit filter range and save
          await testUtils.dom.click(editFilter);
          const timeRangeOption = webClient.el.querySelectorAll(
            ".o_spreadsheet_filter_editor_side_panel .o_side_panel_section"
          )[1];
          timeRangeOption
            .querySelector("select option[value='quarter']")
            .setAttribute("selected", "selected");
          await testUtils.dom.triggerEvent(
            timeRangeOption.querySelector("select"),
            "change"
          );
          await testUtils.nextTick();
          const quarterOption = webClient.el.querySelectorAll(
            ".o_spreadsheet_filter_editor_side_panel .o_side_panel_section"
          )[2];
          quarterOption
            .querySelector("select option[value='first_quarter']")
            .setAttribute("selected", "selected");
          await testUtils.dom.triggerEvent(
            quarterOption.querySelector("select"),
            "change"
          );
          await testUtils.nextTick();

          await testUtils.dom.click(
            webClient.el.querySelector(".o_global_filter_save")
          );
          await testUtils.nextTick();

          assert.deepEqual(model.getters.getGlobalFilter(42).defaultValue, {
            period: "first_quarter",
            year: "this_year",
          });
          assert.deepEqual(model.getters.getGlobalFilterValue(42), model.getters.getGlobalFilter(42).defaultValue);

        });

        test("pivot headers won't change when adding a filter ", async function (assert) {
            assert.expect(6);
            const { model } = await createSpreadsheetFromPivot({
                pivotView: {
                    arch: `
                    <pivot string="Partners">
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>
                    `,
                },
            });
            await waitForEvaluation(model);
            assert.equal(getCellValue(model, "A3"), "xphone");
            assert.equal(getCellValue(model, "A4"), "xpad");
            await addGlobalFilter(model, {
                filter: {
                    id: "42",
                    type: "relation",
                    label: "Relation Filter",
                    modelName: "product",
                    defaultValue: [41],
                    pivotFields: {1: {field: "product_id", type: "many2one"}},
                },
            });
            await waitForEvaluation(model);
            await testUtils.nextTick();
            assert.equal(getCellValue(model, "A3"), "xphone");
            assert.equal(getCellValue(model, "B3"), "");
            assert.equal(getCellValue(model, "A4"), "xpad");
            assert.equal(getCellValue(model, "B4"), "121");
        });
    }
);
