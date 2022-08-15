/** @odoo-module */

import {
    getListAutofillValue,
    getCellFormula,
    createSpreadsheetFromList,
    autofill,
    getCellValue,
    waitForEvaluation,
} from "./spreadsheet_test_utils";
import { nextTick } from "web.test_utils";

QUnit.module("documents_spreadsheet > list_autofill", {}, () => {
    QUnit.test("Autofill list values", async function (assert) {
        assert.expect(25);

        const { model } = await createSpreadsheetFromList();
        // From value to value
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "C4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "C5")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 3 }),
            `=LIST("1","5","date")`
        );
        assert.strictEqual(getListAutofillValue(model, "C3", { direction: "right", steps: 4 }), "");
        // From value to header
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "left", steps: 1 }),
            getCellFormula(model, "A4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 2 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 3 }),
            getCellFormula(model, "B1")
        );
        // From header to header
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            getCellFormula(model, "C3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "right", steps: 2 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "left", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "top", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A5")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "top", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "bottom", steps: 2 }),
            `=LIST("1","5","foo")`
        );
        assert.strictEqual(getListAutofillValue(model, "A4", { direction: "top", steps: 4 }), "");
        // From header to value
        assert.strictEqual(
            getListAutofillValue(model, "B2", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B2", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "B4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A3", { direction: "right", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A3", { direction: "right", steps: 5 }),
            getCellFormula(model, "F3")
        );
        assert.strictEqual(getListAutofillValue(model, "A3", { direction: "right", steps: 6 }), "");
    });

    QUnit.test("Autofill list correctly update the cache", async function (assert) {
        assert.expect(2);
        const { model } = await createSpreadsheetFromList({ linesNumber: 1 });
        autofill(model, "A2", "A3");
        assert.strictEqual(getCellValue(model, "A3"), undefined);
        await nextTick(); // Wait for the RPC to be launched
        await waitForEvaluation(model);
        assert.strictEqual(getCellValue(model, "A3"), 1);
    });

    QUnit.test("Tooltip of list formulas", async function (assert) {
        assert.expect(4);

        const { model } = await createSpreadsheetFromList();

        function getTooltip(xc, isColumn) {
            return model.getters.getTooltipListFormula(getCellFormula(model, xc), isColumn);
        }

        assert.strictEqual(getTooltip("A3", false), "Record #2");
        assert.strictEqual(getTooltip("A3", true), "Foo");
        assert.strictEqual(getTooltip("A1", false), "Foo");
        assert.strictEqual(getTooltip("A1", true), "Foo");
    });
});
