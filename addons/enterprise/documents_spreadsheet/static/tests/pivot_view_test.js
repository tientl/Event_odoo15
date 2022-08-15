/** @odoo-module alias=documents_spreadsheet.PivotViewTests */

import { getBasicData } from "./spreadsheet_test_data";
import {
    createSpreadsheet,
    createSpreadsheetFromPivot,
    getCell,
    getCellContent,
    getCellFormula,
    getCells,
    getCellValue,
    getMerges,
    setCellContent,
    waitForEvaluation,
} from "./spreadsheet_test_utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { click, nextTick, legacyExtraNextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { modal } from "web.test_utils"

import { makeView } from "@web/../tests/views/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import {
    toggleMenu,
    toggleMenuItem,
    setupControlPanelServiceRegistry,
} from "@web/../tests/search/helpers";
import * as BusService from "bus.BusService";
import * as legacyRegistry from "web.Registry";
import * as RamStorage from "web.RamStorage";
import * as AbstractStorageService from "web.AbstractStorageService";
import { spreadsheetService } from "../src/actions/spreadsheet/spreadsheet_service";
import spreadsheet from "../src/js/o_spreadsheet/o_spreadsheet_extended";
const { cellMenuRegistry } = spreadsheet.registries;

const { module, test } = QUnit;

module("documents_spreadsheet > pivot_view");

test("simple pivot export", async (assert) => {
    assert.expect(8);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                </pivot>`,
        },
    });
    assert.strictEqual(Object.values(getCells(model)).length, 6);
    assert.strictEqual(getCellFormula(model, "A1"), "");
    assert.strictEqual(getCellFormula(model, "A2"), "");
    assert.strictEqual(getCellFormula(model, "A3"), '=PIVOT.HEADER("1")');
    assert.strictEqual(getCellFormula(model, "B1"), '=PIVOT.HEADER("1")');
    assert.strictEqual(getCellFormula(model, "B2"), '=PIVOT.HEADER("1","measure","foo")');
    assert.strictEqual(getCellFormula(model, "B3"), '=PIVOT("1","foo")');
    assert.strictEqual(getCell(model, "B3").format, "#,##0.00");
});

test("simple pivot export with two measures", async (assert) => {
    assert.expect(10);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="measure"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        },
    });
    assert.strictEqual(Object.values(getCells(model)).length, 9);
    assert.strictEqual(getCellFormula(model, "B1"), '=PIVOT.HEADER("1")');
    assert.strictEqual(getCellFormula(model, "B2"), '=PIVOT.HEADER("1","measure","foo")');
    assert.strictEqual(getCell(model, "B2").style.bold, undefined);
    assert.strictEqual(getCellFormula(model, "C2"), '=PIVOT.HEADER("1","measure","probability")');
    assert.strictEqual(getCellFormula(model, "B3"), '=PIVOT("1","foo")');
    assert.strictEqual(getCell(model, "B3").format, "#,##0.00");
    assert.strictEqual(getCellFormula(model, "C3"), '=PIVOT("1","probability")');
    assert.strictEqual(getCell(model, "C3").format, "#,##0.00");
    assert.deepEqual(getMerges(model), ["B1:C1"]);
});

test("pivot with two measures: total cells above measures totals are merged in one", async (assert) => {
    assert.expect(2);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
                <pivot string="Partners">
                    <field name="foo" type="col"/>
                    <field name="date" interval="week" type="row"/>
                    <field name="foo" type="measure"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        },
    });
    const merges = getMerges(model);
    assert.strictEqual(merges.length, 5);
    assert.strictEqual(merges[4], "J1:K1");
});

test("pivot with one level of group bys", async (assert) => {
    assert.expect(7);
    const { model } = await createSpreadsheetFromPivot();
    assert.strictEqual(Object.values(getCells(model)).length, 30);
    assert.strictEqual(getCellFormula(model, "A3"), '=PIVOT.HEADER("1","bar","false")');
    assert.strictEqual(getCellFormula(model, "A4"), '=PIVOT.HEADER("1","bar","true")');
    assert.strictEqual(getCellFormula(model, "A5"), '=PIVOT.HEADER("1")');
    assert.strictEqual(
        getCellFormula(model, "B2"),
        '=PIVOT.HEADER("1","foo","1","measure","probability")'
    );
    assert.strictEqual(
        getCellFormula(model, "C3"),
        '=PIVOT("1","probability","bar","false","foo","2")'
    );
    assert.strictEqual(getCellFormula(model, "F5"), '=PIVOT("1","probability")');
});

test("pivot with two levels of group bys in rows", async (assert) => {
    assert.expect(9);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="bar" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
        actions: async (pivot) => {
            await click(pivot.el.querySelector("tbody .o_pivot_header_cell_closed"));
            await click(pivot.el.querySelectorAll(".dropdown-item")[1]);
        },
    });
    assert.strictEqual(Object.values(getCells(model)).length, 16);
    assert.strictEqual(getCellFormula(model, "A3"), '=PIVOT.HEADER("1","bar","false")');
    assert.deepEqual(getCell(model, "A3").style, { fillColor: "#f2f2f2", bold: true });
    assert.strictEqual(
        getCellFormula(model, "A4"),
        '=PIVOT.HEADER("1","bar","false","product_id","41")'
    );
    assert.deepEqual(getCell(model, "A4").style, { fillColor: "#f2f2f2" });
    assert.strictEqual(getCellFormula(model, "A5"), '=PIVOT.HEADER("1","bar","true")');
    assert.strictEqual(
        getCellFormula(model, "A6"),
        '=PIVOT.HEADER("1","bar","true","product_id","37")'
    );
    assert.strictEqual(
        getCellFormula(model, "A7"),
        '=PIVOT.HEADER("1","bar","true","product_id","41")'
    );
    assert.strictEqual(getCellFormula(model, "A8"), '=PIVOT.HEADER("1")');
});

test("Add pivot: date grouping", async (assert) => {
    assert.expect(6);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="date" interval="month" type="row"/>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "A7"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "A8"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41")`);
});

test("Add pivot: no date groupings", async (assert) => {
    assert.expect(8);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="row"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
            mockRPC: function (route, args) {
                if(args.method === "search_read" && args.model === "product"){
                    assert.deepEqual(
                        args.kwargs,
                        {
                            context: {
                                active_test: false,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            domain: [["id", "in", [37, 41]]],
                            fields: ["id"],
                        },
                        "RPC arguments should be correct"
                    );
                }
            }
        }
    });
    assert.equal(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","product_id","37")`);
    assert.equal(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","product_id","41")`);
    assert.equal(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "A7"), `=PIVOT.HEADER("1","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "A8"), `=PIVOT.HEADER("1","product_id","41","foo","17")`);
});

test("Add pivot: foo has a parent date grouping: only foo should be joined across months", async (assert) => {
    assert.expect(12);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="row"/>
                <field name="date" interval="month" type="row"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","product_id","37")`);
    assert.equal(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","product_id","37","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","product_id","37","date:month","04/2016","foo","12")`);
    assert.equal(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","product_id","41")`);
    assert.equal(getCellFormula(model, "A7"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "A8"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","1")`);
    assert.equal(getCellFormula(model, "A9"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","2")`);
    assert.equal(getCellFormula(model, "A10"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","17")`);
    assert.equal(getCellFormula(model, "A11"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "A12"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","1")`);
    assert.equal(getCellFormula(model, "A13"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","2")`);
    assert.equal(getCellFormula(model, "A14"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","17")`);
});

test("Add pivot: Both groupings have a parent date grouping: both sets must be joined across months", async (assert) => {
    assert.expect(33);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="date" interval="month" type="row"/>
                <field name="product_id" type="row"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","1")`);
    assert.equal(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","2")`);
    assert.equal(getCellFormula(model, "A7"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "A8"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","17")`);
    assert.equal(getCellFormula(model, "A9"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "A10"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "A11"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "A12"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","12")`);
    assert.equal(getCellFormula(model, "A13"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","17")`);
    assert.equal(getCellFormula(model, "A14"), `=PIVOT.HEADER("1","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "A15"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "A16"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","1")`);
    assert.equal(getCellFormula(model, "A17"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","2")`);
    assert.equal(getCellFormula(model, "A18"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "A19"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","17")`);
    assert.equal(getCellFormula(model, "A20"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "A21"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "A22"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "A23"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","12")`);
    assert.equal(getCellFormula(model, "A24"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","17")`);
    assert.equal(getCellFormula(model, "A25"), `=PIVOT.HEADER("1","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "A26"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "A27"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","1")`);
    assert.equal(getCellFormula(model, "A28"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","2")`);
    assert.equal(getCellFormula(model, "A29"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "A30"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","17")`);
    assert.equal(getCellFormula(model, "A31"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "A32"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "A33"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "A34"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","12")`);
    assert.equal(getCellFormula(model, "A35"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","17")`);
});

test("Add pivot: Never join the values of a date field if there is a parent group based on the same date field", async (assert) => {
    assert.expect(8);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="date" interval="month" type="row"/>
                <field name="date" interval="week" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","date:month","04/2016","date:week","15/2016")`);
    assert.equal(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","date:month","10/2016","date:week","43/2016")`);
    assert.equal(getCellFormula(model, "A7"), `=PIVOT.HEADER("1","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "A8"), `=PIVOT.HEADER("1","date:month","12/2016","date:week","49/2016")`);
    assert.equal(getCellFormula(model, "A9"), `=PIVOT.HEADER("1","date:month","12/2016","date:week","50/2016")`);
    assert.equal(getCellFormula(model, "A10"), `=PIVOT.HEADER("1")`);
});

test("Add pivot: date grouping", async (assert) => {
    assert.expect(17);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="date" interval="month" type="col"/>
                <field name="product_id" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "B1"), `=PIVOT.HEADER("1","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "B2"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "B3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","measure","probability")`);
    assert.equal(getCellFormula(model, "C2"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "C3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","measure","probability")`);
    assert.equal(getCellFormula(model, "D1"), `=PIVOT.HEADER("1","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "D2"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "D3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","measure","probability")`);
    assert.equal(getCellFormula(model, "E2"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "E3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","measure","probability")`);
    assert.equal(getCellFormula(model, "F1"), `=PIVOT.HEADER("1","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "F2"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "F3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","measure","probability")`);
    assert.equal(getCellFormula(model, "G2"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "G3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","measure","probability")`);
    assert.equal(getCellFormula(model, "H2"), `=PIVOT.HEADER("1")`);
    assert.equal(getCellFormula(model, "H3"), `=PIVOT.HEADER("1","measure","probability")`);
});

test("Add pivot: no date groupings", async (assert) => {
    assert.expect(12);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "B1"), `=PIVOT.HEADER("1","product_id","37")`);
    assert.equal(getCellFormula(model, "B2"), `=PIVOT.HEADER("1","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "B3"), `=PIVOT.HEADER("1","product_id","37","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "C1"), `=PIVOT.HEADER("1","product_id","41")`);
    assert.equal(getCellFormula(model, "C2"), `=PIVOT.HEADER("1","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "C3"), `=PIVOT.HEADER("1","product_id","41","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "D2"), `=PIVOT.HEADER("1","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "D3"), `=PIVOT.HEADER("1","product_id","41","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "E2"), `=PIVOT.HEADER("1","product_id","41","foo","17")`);
    assert.equal(getCellFormula(model, "E3"), `=PIVOT.HEADER("1","product_id","41","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "F2"), `=PIVOT.HEADER("1")`);
    assert.equal(getCellFormula(model, "F3"), `=PIVOT.HEADER("1","measure","probability")`);
});

test("Add pivot: foo has a parent date grouping: only foo should be joined across months", async (assert) => {
    assert.expect(21);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="date" interval="month" type="col"/>
                <field name="foo" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "B1"), `=PIVOT.HEADER("1","product_id","37")`);
    assert.equal(getCellFormula(model, "B2"), `=PIVOT.HEADER("1","product_id","37","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "B3"), `=PIVOT.HEADER("1","product_id","37","date:month","04/2016","foo","12")`);
    assert.equal(getCellFormula(model, "B4"), `=PIVOT.HEADER("1","product_id","37","date:month","04/2016","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "C1"), `=PIVOT.HEADER("1","product_id","41")`);
    assert.equal(getCellFormula(model, "C2"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "C3"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","1")`);
    assert.equal(getCellFormula(model, "C4"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "D3"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","2")`);
    assert.equal(getCellFormula(model, "D4"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "E3"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","17")`);
    assert.equal(getCellFormula(model, "E4"), `=PIVOT.HEADER("1","product_id","41","date:month","10/2016","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "F2"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "F3"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","1")`);
    assert.equal(getCellFormula(model, "F4"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "G3"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","2")`);
    assert.equal(getCellFormula(model, "G4"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "H3"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","17")`);
    assert.equal(getCellFormula(model, "H4"), `=PIVOT.HEADER("1","product_id","41","date:month","12/2016","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "I3"), `=PIVOT.HEADER("1")`);
    assert.equal(getCellFormula(model, "I4"), `=PIVOT.HEADER("1","measure","probability")`);
});

test("Add pivot: Both groupings have a parent date grouping: both sets must be joined across months", async (assert) => {
    assert.expect(59);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="date" interval="month" type="col"/>
                <field name="product_id" type="col"/>
                <field name="foo" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "B1"), `=PIVOT.HEADER("1","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "B2"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "B3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","1")`);
    assert.equal(getCellFormula(model, "B4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "C3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","2")`);
    assert.equal(getCellFormula(model, "C4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "D3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "D4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "E3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","17")`);
    assert.equal(getCellFormula(model, "E4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","37","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "F2"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "F3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "F4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "G3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "G4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "H3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","12")`);
    assert.equal(getCellFormula(model, "H4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "I3"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","17")`);
    assert.equal(getCellFormula(model, "I4"), `=PIVOT.HEADER("1","date:month","04/2016","product_id","41","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "J1"), `=PIVOT.HEADER("1","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "J2"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "J3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","1")`);
    assert.equal(getCellFormula(model, "J4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "K3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","2")`);
    assert.equal(getCellFormula(model, "K4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "L3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "L4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "M3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","17")`);
    assert.equal(getCellFormula(model, "M4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","37","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "N2"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "N3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "N4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "O3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "O4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "P3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","12")`);
    assert.equal(getCellFormula(model, "P4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "Q3"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","17")`);
    assert.equal(getCellFormula(model, "Q4"), `=PIVOT.HEADER("1","date:month","10/2016","product_id","41","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "R1"), `=PIVOT.HEADER("1","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "R2"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37")`);
    assert.equal(getCellFormula(model, "R3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","1")`);
    assert.equal(getCellFormula(model, "R4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "S3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","2")`);
    assert.equal(getCellFormula(model, "S4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "T3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","12")`);
    assert.equal(getCellFormula(model, "T4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "U3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","17")`);
    assert.equal(getCellFormula(model, "U4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","37","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "V2"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41")`);
    assert.equal(getCellFormula(model, "V3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","1")`);
    assert.equal(getCellFormula(model, "V4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","1","measure","probability")`);
    assert.equal(getCellFormula(model, "W3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","2")`);
    assert.equal(getCellFormula(model, "W4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","2","measure","probability")`);
    assert.equal(getCellFormula(model, "X3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","12")`);
    assert.equal(getCellFormula(model, "X4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","12","measure","probability")`);
    assert.equal(getCellFormula(model, "Y3"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","17")`);
    assert.equal(getCellFormula(model, "Y4"), `=PIVOT.HEADER("1","date:month","12/2016","product_id","41","foo","17","measure","probability")`);
    assert.equal(getCellFormula(model, "Z3"), `=PIVOT.HEADER("1")`);
    assert.equal(getCellFormula(model, "Z4"), `=PIVOT.HEADER("1","measure","probability")`);
});

test("Add pivot: Never join the values of a date field if there is a parent group based on the same date field", async (assert) => {
    assert.expect(14);
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="date" interval="month" type="col"/>
                <field name="date" interval="week" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        }
    });
    assert.equal(getCellFormula(model, "B1"), `=PIVOT.HEADER("1","date:month","04/2016")`);
    assert.equal(getCellFormula(model, "B2"), `=PIVOT.HEADER("1","date:month","04/2016","date:week","15/2016")`);
    assert.equal(getCellFormula(model, "B3"), `=PIVOT.HEADER("1","date:month","04/2016","date:week","15/2016","measure","probability")`);
    assert.equal(getCellFormula(model, "C1"), `=PIVOT.HEADER("1","date:month","10/2016")`);
    assert.equal(getCellFormula(model, "C2"), `=PIVOT.HEADER("1","date:month","10/2016","date:week","43/2016")`);
    assert.equal(getCellFormula(model, "C3"), `=PIVOT.HEADER("1","date:month","10/2016","date:week","43/2016","measure","probability")`);
    assert.equal(getCellFormula(model, "D1"), `=PIVOT.HEADER("1","date:month","12/2016")`);
    assert.equal(getCellFormula(model, "D2"), `=PIVOT.HEADER("1","date:month","12/2016","date:week","49/2016")`);
    assert.equal(getCellFormula(model, "D3"), `=PIVOT.HEADER("1","date:month","12/2016","date:week","49/2016","measure","probability")`);
    assert.equal(getCellFormula(model, "E1"), ``);
    assert.equal(getCellFormula(model, "E2"), `=PIVOT.HEADER("1","date:month","12/2016","date:week","50/2016")`);
    assert.equal(getCellFormula(model, "E3"), `=PIVOT.HEADER("1","date:month","12/2016","date:week","50/2016","measure","probability")`);
    assert.equal(getCellFormula(model, "F2"), `=PIVOT.HEADER("1")`);
    assert.equal(getCellFormula(model, "F3"), `=PIVOT.HEADER("1","measure","probability")`);
});

test("verify that there is a record for an undefined header", async (assert) => {
    assert.expect(1);

    const data = getBasicData();

    data.partner.records = [
        {
            id: 1,
            foo: 12,
            bar: true,
            date: "2016-04-14",
            product_id: false,
            probability: 10,
        },
    ];

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    assert.strictEqual(getCellFormula(model, "A3"), '=PIVOT.HEADER("1","product_id","false")');
});

test("undefined date is inserted in pivot", async (assert) => {
    assert.expect(1);

    const data = getBasicData();
    data.partner.records = [
        {
            id: 1,
            foo: 12,
            bar: true,
            date: false,
            product_id: 37,
            probability: 10,
        },
    ];

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="date" interval="day" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    assert.strictEqual(getCellFormula(model, "A3"), '=PIVOT.HEADER("1","date:day","false")');
});

test("pivot with two levels of group bys in cols", async (assert) => {
    assert.expect(12);

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="bar" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
        actions: async (pivot) => {
            await click(pivot.el.querySelector("thead .o_pivot_header_cell_closed"));
            await click(pivot.el.querySelectorAll(".dropdown-item")[1]);
        },
    });
    assert.strictEqual(Object.values(getCells(model)).length, 20);
    assert.strictEqual(getCellContent(model, "A1"), "");
    assert.deepEqual(getCell(model, "A4").style, { fillColor: "#f2f2f2", bold: true });
    assert.strictEqual(getCellFormula(model, "B1"), '=PIVOT.HEADER("1","bar","false")');
    assert.strictEqual(getCellFormula(model, "B2"), '=PIVOT.HEADER("1","bar","false","product_id","41")');
    assert.strictEqual(getCellFormula(model, "B3"), '=PIVOT.HEADER("1","bar","false","product_id","41","measure","probability")');
    assert.deepEqual(getCell(model, "C2").style, { fillColor: "#f2f2f2", bold: true });
    assert.strictEqual(getCellFormula(model, "C1"), '=PIVOT.HEADER("1","bar","true")');
    assert.strictEqual(getCellFormula(model, "C2"), '=PIVOT.HEADER("1","bar","true","product_id","37")');
    assert.strictEqual(getCellFormula(model, "C3"), '=PIVOT.HEADER("1","bar","true","product_id","37","measure","probability")');
    assert.strictEqual(getCellFormula(model, "D2"), '=PIVOT.HEADER("1","bar","true","product_id","41")');
    assert.strictEqual(getCellFormula(model, "D3"), '=PIVOT.HEADER("1","bar","true","product_id","41","measure","probability")');
});

test("pivot with count as measure", async (assert) => {
    assert.expect(3);

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="probability" type="measure"/>
            </pivot>`,
        },
        actions: async (pivot) => {
            await toggleMenu(pivot, "Measures");
            await toggleMenuItem(pivot, "Count");
        },
    });
    assert.strictEqual(Object.keys(getCells(model)).length, 9);
    assert.strictEqual(getCellFormula(model, "C2"), '=PIVOT.HEADER("1","measure","__count")');
    assert.strictEqual(getCellFormula(model, "C3"), '=PIVOT("1","__count")');
});

test("pivot with two levels of group bys in cols with not enough cols", async (assert) => {
    assert.expect(1);

    const data = getBasicData();
    // add many values in a subgroup
    for (let i = 0; i < 70; i++) {
        data.product.records.push({
            id: i + 9999,
            display_name: i.toString(),
        });
        data.partner.records.push({
            id: i + 9999,
            bar: i % 2 === 0,
            product_id: i + 9999,
            probability: i,
        });
    }

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="bar" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
        actions: async (pivot) => {
            await click(pivot.el.querySelector("thead .o_pivot_header_cell_closed"));
            await click(pivot.el.querySelectorAll(".dropdown-item")[1]);
        },
    });
    // 72 products * 1 groups + 1 row header + 1 total col + 1 extra empty col at the end
    assert.strictEqual(model.getters.getActiveSheet().cols.length, 76);
});

test("groupby week is sorted", async (assert) => {
    assert.expect(4);

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            arch: `
            <pivot string="Partners">
                <field name="foo" type="col"/>
                <field name="date" interval="week" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    assert.strictEqual(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","date:week","15/2016")`);
    assert.strictEqual(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","date:week","43/2016")`);
    assert.strictEqual(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","date:week","49/2016")`);
    assert.strictEqual(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","date:week","50/2016")`);
});

test("groupby quarter is sorted", async (assert) => {
    assert.expect(4);

    let data = getBasicData();
    data.partner.records[0].date = "2016-01-02";
    data.partner.records[1].date = "2016-05-02";
    data.partner.records[2].date = "2016-09-02";
    data.partner.records[3].date = "2017-01-02";
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="foo" type="col"/>
                <field name="date" interval="quarter" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    assert.strictEqual(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","date:quarter","1/2016")`);
    assert.strictEqual(getCellFormula(model, "A4"), `=PIVOT.HEADER("1","date:quarter","2/2016")`);
    assert.strictEqual(getCellFormula(model, "A5"), `=PIVOT.HEADER("1","date:quarter","3/2016")`);
    assert.strictEqual(getCellFormula(model, "A6"), `=PIVOT.HEADER("1","date:quarter","1/2017")`);
});

test("Can save a pivot in a new spreadsheet", async (assert) => {
    assert.expect(2);

    const legacyServicesRegistry = new legacyRegistry();
    const LocalStorageService = AbstractStorageService.extend({
        storage: new RamStorage(),
    });
    legacyServicesRegistry.add(
        "bus_service",
        BusService.extend({
            _poll() {},
        })
    );
    legacyServicesRegistry.add("local_storage", LocalStorageService);

    const serverData = {
        models: getBasicData(),
        views: {
            "partner,false,pivot": `
                 <pivot string="Partners">
                     <field name="probability" type="measure"/>
                 </pivot>`,
            "partner,false,search": `<search/>`,
        },
    };
    registry.category("services").add("spreadsheet", spreadsheetService);
    const webClient = await createWebClient({
        serverData,
        legacyParams: {
            withLegacyMockServer: true,
            serviceRegistry: legacyServicesRegistry,
        },
        mockRPC: function (route, args) {
            if (args.method === "has_group") {
                return Promise.resolve(true);
            }
            if (route.includes("get_spreadsheets_to_display")) {
                return [{ id: 1, name: "My Spreadsheet" }];
            }
            if (args.method === "create" && args.model === "documents.document") {
                assert.step("create");
                return 1;
            }
        },
    });

    await doAction(webClient, {
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });
    await click(webClient.el.querySelector(".o_pivot_add_spreadsheet"));
    await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
    assert.verifySteps(["create"]);
});

test("Can save a pivot in existing spreadsheet", async (assert) => {
    assert.expect(3);

    const legacyServicesRegistry = new legacyRegistry();
    const LocalStorageService = AbstractStorageService.extend({
        storage: new RamStorage(),
    });
    legacyServicesRegistry.add("local_storage", LocalStorageService);
    legacyServicesRegistry.add(
        "bus_service",
        BusService.extend({
            _poll() {},
        })
    );

    const serverData = {
        models: getBasicData(),
        views: {
            "partner,false,pivot": `
                 <pivot string="Partners">
                     <field name="probability" type="measure"/>
                 </pivot>`,
            "partner,false,search": `<search/>`,
        },
    };
    registry.category("services").add("spreadsheet", spreadsheetService);
    const webClient = await createWebClient({
        serverData,
        legacyParams: {
            withLegacyMockServer: true,
            serviceRegistry: legacyServicesRegistry,
        },
        mockRPC: function (route, args) {
            if (args.method === "has_group") {
                return Promise.resolve(true);
            }
            if (route === "/web/action/load") {
                assert.step("write");
                return { id: args.action_id, type: "ir.actions.act_window_close" };
            }
            if (route.includes("join_spreadsheet_session")) {
                assert.step("join_spreadsheet_session");
            }
            if (args.model === "documents.document") {
                switch (args.method) {
                    case "get_spreadsheets_to_display":
                        return [{ id: 1, name: "My Spreadsheet" }];
                }
            }
        },
    });

    await doAction(webClient, {
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    await click(webClient.el.querySelector(".o_pivot_add_spreadsheet"));
    await click(document.querySelector(".modal-content select"));
    document.body
        .querySelector(".modal-content option[value='1']")
        .setAttribute("selected", "selected");
    await nextTick();
    await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
    await doAction(webClient, 1); // leave the spreadsheet action
    assert.verifySteps(["join_spreadsheet_session", "write"]);
});

test("Add pivot sheet at the end of existing spreadsheet", async (assert) => {
    assert.expect(4);

    let callback;
    const { model } = await createSpreadsheetFromPivot({
        async actions(pivot) {
            callback = await pivot.getCallbackBuildPivot(false);
        },
    });
    model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1 });
    const activeSheetId = model.getters.getActiveSheetId();
    assert.deepEqual(model.getters.getVisibleSheets(), [activeSheetId, "42"]);
    callback(model);
    assert.strictEqual(model.getters.getSheets().length, 3);
    assert.deepEqual(model.getters.getVisibleSheets()[0], activeSheetId);
    assert.deepEqual(model.getters.getVisibleSheets()[1], "42");
});

test("pivot with a domain", async (assert) => {
    assert.expect(3);

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            domain: [["bar", "=", true]],
        },
    });
    const domain = model.getters.getPivotDomain("1");
    assert.deepEqual(domain, [["bar", "=", true]], "It should have the correct domain");
    assert.strictEqual(getCellFormula(model, "A3"), `=PIVOT.HEADER("1","bar","true")`);
    assert.strictEqual(getCellFormula(model, "A4"), `=PIVOT.HEADER("1")`);
});

test("Insert in spreadsheet is disabled when no measure is specified", async (assert) => {
    assert.expect(1);

    setupControlPanelServiceRegistry();
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("dialog", dialogService);
    const serverData = {
        models: getBasicData(),
    };
    const pivot = await makeView({
        type: "pivot",
        resModel: "partner",
        serverData,
        arch: `
        <pivot string="Partners">
            <field name="foo" type="measure"/>
        </pivot>`,
        mockRPC: function (route, args) {
            if (args.method === "has_group") {
                return Promise.resolve(true);
            }
        },
    });

    await toggleMenu(pivot, "Measures");
    await toggleMenuItem(pivot, "Foo");
    assert.ok(pivot.el.querySelector("button.o_pivot_add_spreadsheet").disabled);
});

test("Insert in spreadsheet is disabled when data is empty", async (assert) => {
    assert.expect(1);

    const serviceRegistry = registry.category("services");
    setupControlPanelServiceRegistry();
    serviceRegistry.add("dialog", dialogService);

    const data = getBasicData();
    data.partner.records = [];
    data.product.records = [];
    const serverData = {
        models: data,
    };

    await makeView({
        type: "pivot",
        resModel: "partner",
        serverData,
        arch: `
        <pivot string="Partners">
            <field name="foo" type="measure"/>
        </pivot>`,
        mockRPC: function (route, args) {
            if (args.method === "has_group") {
                return Promise.resolve(true);
            }
        },
    });
    assert.ok(document.body.querySelector("button.o_pivot_add_spreadsheet").disabled);
});

test("pivot with a quote in name", async function (assert) {
    assert.expect(1);

    const data = getBasicData();
    data.product.records.push({
        id: 42,
        display_name: `name with "`,
    });
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            model: "product",
            data,
            arch: `
            <pivot string="Products">
                <field name="display_name" type="col"/>
                <field name="id" type="row"/>
            </pivot>`,
        },
    });
    assert.equal(getCellContent(model, "B1"), `=PIVOT.HEADER("1","display_name","name with \\"")`);
});

test("group by regular field defined with not supported aggregate", async function (assert) {
    assert.expect(2);

    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            model: "partner",
            data: getBasicData(),
            arch: `
            <pivot string="Partners">
                <field name="foo" type="row"/>
                <field name="field_with_array_agg" type="measure"/>
            </pivot>`,
        },
    });
    const B7 = getCell(model, "B7");
    assert.equal(B7.evaluated.error, `Not implemented: array_agg`);
    assert.equal(B7.evaluated.value, `#ERROR`);
});

test("group by related field with archived record", async function (assert) {
    assert.expect(3);

    const data = getBasicData();
    // data.product.records[0].active = false;
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="name" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    assert.equal(getCellContent(model, "B1"), `=PIVOT.HEADER("1","product_id","37")`);
    assert.equal(getCellContent(model, "C1"), `=PIVOT.HEADER("1","product_id","41")`);
    assert.equal(getCellContent(model, "D1"), `=PIVOT.HEADER("1")`);
});

test("group by regular field with archived record", async function (assert) {
    assert.expect(4);

    const data = getBasicData();
    data.partner.records[0].active = false;
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    assert.equal(getCellContent(model, "A3"), `=PIVOT.HEADER("1","foo","1")`);
    assert.equal(getCellContent(model, "A4"), `=PIVOT.HEADER("1","foo","2")`);
    assert.equal(getCellContent(model, "A5"), `=PIVOT.HEADER("1","foo","17")`);
    assert.equal(getCellContent(model, "A6"), `=PIVOT.HEADER("1")`);
});

test("can select a Pivot from cell formula", async function (assert) {
    assert.expect(1);
    const data = getBasicData();
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition(sheetId, 2, 2);
    model.dispatch("SELECT_PIVOT", { pivotId });
    const selectedPivotId = model.getters.getSelectedPivotId();
    assert.strictEqual(selectedPivotId, "1");
});

test("can select a Pivot from cell formula with '-' before the formula", async function (assert) {
    assert.expect(1);

    const data = getBasicData();
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=-PIVOT("1","probability","bar","false","foo","2")`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition(sheetId, 2, 2);
    model.dispatch("SELECT_PIVOT", { pivotId });
    const selectedPivotId = model.getters.getSelectedPivotId();
    assert.strictEqual(selectedPivotId, "1");
});

test("can select a Pivot from cell formula with other numerical values", async function (assert) {
    assert.expect(1);

    const data = getBasicData();
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=3*PIVOT("1","probability","bar","false","foo","2")+2`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition(sheetId, 2, 2);
    model.dispatch("SELECT_PIVOT", { pivotId });
    const selectedPivotId = model.getters.getSelectedPivotId();
    assert.strictEqual(selectedPivotId, "1");
});

test("can select a Pivot from cell formula where pivot is in a function call", async function (assert) {
    assert.expect(1);

    const data = getBasicData();
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=SUM(PIVOT("1","probability","bar","false","foo","2"),PIVOT("1","probability","bar","false","foo","2"))`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition(sheetId, 2, 2);
    model.dispatch("SELECT_PIVOT", { pivotId });
    const selectedPivotId = model.getters.getSelectedPivotId();
    assert.strictEqual(selectedPivotId, "1");
});

test("can select a Pivot from cell formula where the id is a reference", async function (assert) {
    assert.expect(1);
    const { model } = await createSpreadsheetFromPivot();
    setCellContent(model, "C3", `=PIVOT(G10,"probability","bar","false","foo","2")+2`);
    setCellContent(model, "G10", "1");
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition(sheetId, 2, 2);
    model.dispatch("SELECT_PIVOT", { pivotId });
    const selectedPivotId = model.getters.getSelectedPivotId();
    assert.strictEqual(selectedPivotId, "1");
});

test("Columns of newly inserted pivot are auto-resized", async function (assert) {
    assert.expect(1);

    const data = getBasicData();
    data.partner.fields.probability.string = "Probability with a super long name";
    const { model } = await createSpreadsheetFromPivot({ pivotView: { data } });
    const sheetId = model.getters.getActiveSheetId();
    const defaultColSize = 96;
    assert.ok(model.getters.getCol(sheetId, 1).size > defaultColSize, "Column should be resized");
});

test("can select a Pivot from cell formula (Mix of test scenarios above)", async function (assert) {
    assert.expect(1);

    const data = getBasicData();
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        },
    });
    model.dispatch("SET_VALUE", {
        xc: "C3",
        text: `=3*SUM(PIVOT("1","probability","bar","false","foo","2"),PIVOT("1","probability","bar","false","foo","2"))+2*PIVOT("1","probability","bar","false","foo","2")`,
    });
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIdFromPosition(sheetId, 2, 2);
    model.dispatch("SELECT_PIVOT", { pivotId });
    const selectedPivotId = model.getters.getSelectedPivotId();
    assert.strictEqual(selectedPivotId, "1");
});

test("Can remove a pivot with undo after editing a cell", async function (assert) {
    assert.expect(4);
    const { model } = await createSpreadsheetFromPivot();
    assert.ok(getCellContent(model, "B1").startsWith("=PIVOT.HEADER"));
    setCellContent(model, "G10", "should be undoable");
    model.dispatch("REQUEST_UNDO");
    assert.equal(getCellContent(model, "G10"), "");
    // 2 REQUEST_UNDO because of the AUTORESIZE feature
    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    assert.equal(getCellContent(model, "B1"), "");
    assert.equal(model.getters.getPivotIds().length, 0);
});

test("Get value from pivot with a non-loaded cache", async function (assert) {
    assert.expect(3);
    const { model } = await createSpreadsheetFromPivot();
    await waitForEvaluation(model);
    assert.equal(getCellValue(model, "C3"), 15);
    model.getters.waitForPivotDataReady("1", { force: true });
    model.dispatch("EVALUATE_CELLS", { sheetId: model.getters.getActiveSheetId() });
    assert.equal(getCellValue(model, "C3"), "Loading...");
    await waitForEvaluation(model);
    assert.equal(getCellValue(model, "C3"), 15);
});

test("Format header correctly works with non-existing field", async function (assert) {
    assert.expect(2);
    const { model } = await createSpreadsheetFromPivot();
    setCellContent(model, "G10", `=PIVOT.HEADER("1", "measure", "non-existing")`);
    setCellContent(model, "G11", `=PIVOT.HEADER("1", "non-existing", "bla")`);
    await nextTick();
    assert.equal(getCellValue(model, "G10"), "non-existing");
    assert.equal(getCellValue(model, "G11"), "(Undefined)");
});

test("user related context is not saved in the spreadsheet", async function (assert) {
    const context = {
        allowed_company_ids: [15],
        default_stage_id: 5,
        search_default_stage_id: 5,
        tz: "bx",
        lang: "FR",
        uid: 4,
    };
    const testSession = {
        uid: 4,
        user_companies: {
            allowed_companies: { 15: { id: 15, name: "Hermit" } },
            current_company: 15,
        },
        user_context: context,
    };
    patchWithCleanup(session, testSession);
    const { model, env } = await createSpreadsheetFromPivot();
    assert.deepEqual(env.services.user.context, context, "context is used for spreadsheet action");
    assert.deepEqual(
        model.exportData().pivots[1].context,
        {
            default_stage_id: 5,
            search_default_stage_id: 5,
        },
        "user related context is not stored in context"
    );
});

test("user context is combined with pivot context to fetch data", async function (assert) {
    const context = {
        allowed_company_ids: [15],
        default_stage_id: 5,
        search_default_stage_id: 5,
        tz: "bx",
        lang: "FR",
        uid: 4,
    };
    const testSession = {
        uid: 4,
        user_companies: {
            allowed_companies: {
                15: { id: 15, name: "Hermit" },
                16: { id: 16, name: "Craft" },
            },
            current_company: 15,
        },
        user_context: context,
    };
    const spreadsheetData = {
        pivots: {
            1: {
                id: 1,
                colGroupBys: ["foo"],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: ["bar"],
                context: {
                    allowed_company_ids: [16],
                    default_stage_id: 9,
                    search_default_stage_id: 90,
                    tz: "nz",
                    lang: "EN",
                    uid: 40,
                },
            },
        },
    };
    const data = getBasicData();
    data["documents.document"].records.push({
        id: 45,
        raw: JSON.stringify(spreadsheetData),
        name: "Spreadsheet",
        handler: "spreadsheet",
    });
    const expectedFetchContext = {
        allowed_company_ids: [15],
        default_stage_id: 9,
        search_default_stage_id: 90,
        tz: "bx",
        lang: "FR",
        uid: 4,
    };
    patchWithCleanup(session, testSession);
    await createSpreadsheet({
        data,
        spreadsheetId: 45,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model !== "partner") {
                return;
            }
            switch (method) {
                case "search_read":
                    assert.step("search_read");
                    assert.deepEqual(
                        kwargs.context,
                        {
                            ...expectedFetchContext,
                            active_test: false,
                        },
                        "search_read"
                    );
                    break;
                case "read_group":
                    assert.step("read_group");
                    assert.deepEqual(kwargs.context, expectedFetchContext, "read_group");
                    break;
            }
        },
    });
    assert.verifySteps(["read_group", "search_read", "search_read"]);
});

test("Add pivot with grouping on a many2many", async function (assert) {
    assert.expect(9);

    const data = getBasicData();
    let spreadsheetLoaded = false;
    const { model } = await createSpreadsheetFromPivot({
        pivotView: {
            data,
            arch: `
            <pivot string="Partners">
                <field name="product_id" type="col"/>
                <field name="tag_ids" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
            mockRPC: function (route, args) {
                if (args.method === "join_spreadsheet_session") {
                    spreadsheetLoaded = true;
                }
                if (
                    ['product', 'tag'].includes(args.model)
                    && args.method === "search_read"
                    && spreadsheetLoaded
                    ) {
                    // check that every argument of the domain is json parsed.
                    // Since the values refer to record ids (since we group by
                    // relational field) in this case, we should only have
                    // integers or boolean (false) values
                    const domain = args.kwargs.domain[0];
                    assert.ok(
                        domain[2].every(id => Number.isInteger(id) || id === false),
                        "Every value in the domain should either be an integer or a boolean (false)"
                    )
                }
            }
        },
    });
    assert.equal(getCellContent(model, "A3"), `=PIVOT.HEADER("1","tag_ids","42")`);
    assert.equal(getCellContent(model, "A4"), `=PIVOT.HEADER("1","tag_ids","67")`);
    assert.equal(getCellContent(model, "A5"), `=PIVOT.HEADER("1","tag_ids","false")`);
    assert.equal(getCellContent(model, "A6"), `=PIVOT.HEADER("1")`);
    assert.equal(getCellContent(model, "B1"), `=PIVOT.HEADER("1","product_id","37")`);
    assert.equal(getCellContent(model, "C1"), `=PIVOT.HEADER("1","product_id","41")`);
    assert.equal(getCellContent(model, "D1"), `=PIVOT.HEADER("1")`);
});

test("Can reopen a sheet after see records", async function (assert) {
    assert.expect(1);

    // Create a first spreadsheet with a pivot
    const { webClient, model } = await createSpreadsheetFromPivot({
        pivotView: {
            archs: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,false,list": `<List/>`,
                "partner,false,search": `<Search/>`,
            },
            mockRPC: function(route, args) {
                if (route === "/web/action/load") {
                    return { id: args.action_id, type: "ir.actions.act_window_close" };
                }
                if (args.model === "documents.document") {
                    switch (args.method) {
                        case "get_spreadsheets_to_display":
                            return [{ id: 3, name: "My Spreadsheet" }];
                    }
                }
            },
        },
    });
    await waitForEvaluation(model);
    // Insert a second pivot in the newly created spreadsheet
    await click(document.body.querySelector(".o_back_button"));
    await click(document.body.querySelector(".o_pivot_add_spreadsheet"));
    await click(document.body.querySelector(".modal-content select"));
    document.body
        .querySelector(".modal-content option[value='3']")
        .setAttribute("selected", "selected");
    await modal.clickButton("Confirm");
    await waitForEvaluation(window.o_spreadsheet.__DEBUG__.model);
    // Go the the list view and go back, a third pivot should not be opened
    model.dispatch("SELECT_CELL", { col: 1, row: 2 });
    const root = cellMenuRegistry.getAll().find((item) => item.id === "see records");
    const env = {
        ...webClient.env,
        getters: model.getters,
        dispatch: model.dispatch,
        services: model.config.evalContext.env.services,
    };
    await root.action(env);
    await nextTick();
    await click(document.body.querySelector(".o_back_button"));
    await nextTick();
    await legacyExtraNextTick();
    assert.strictEqual(window.o_spreadsheet.__DEBUG__.model.getters.getPivotIds().length, 2);
});
