/** @odoo-module */

import {
    getNumberOfPivotFormulas,
    getNumberOfListFormulas,
    getFirstPivotFunction,
    getFirstListFunction,
} from "../src/js/o_spreadsheet/helpers/odoo_functions_helpers";

function stringArg(value) {
    return { type: "STRING", value: `"${value}"` };
}

QUnit.module("documents_spreadsheet > pivot_helpers", {}, () => {
    QUnit.test("Basic formula extractor", async function (assert) {
        assert.expect(9);
        const formula = `=PIVOT("1", "test") + LIST("2", "hello", "bla")`;
        let functionName;
        let args;
        ({ functionName, args } = getFirstPivotFunction(formula));
        assert.strictEqual(functionName, "PIVOT");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        ({ functionName, args } = getFirstListFunction(formula));
        assert.strictEqual(functionName, "LIST");
        assert.strictEqual(args.length, 3);
        assert.deepEqual(args[0], stringArg("2"));
        assert.deepEqual(args[1], stringArg("hello"));
        assert.deepEqual(args[2], stringArg("bla"));
    });

    QUnit.test("Extraction with two PIVOT formulas", async function (assert) {
        assert.expect(5);
        const formula = `=PIVOT("1", "test") + PIVOT("2", "hello", "bla")`;
        let functionName;
        let args;
        ({ functionName, args } = getFirstPivotFunction(formula));
        assert.strictEqual(functionName, "PIVOT");
        assert.strictEqual(args.length, 2);
        assert.deepEqual(args[0], stringArg("1"));
        assert.deepEqual(args[1], stringArg("test"));
        assert.strictEqual(getFirstListFunction(formula), undefined);
    });

    QUnit.test("Number of formulas", async function (assert) {
        assert.expect(6);
        const formula = `=PIVOT("1", "test") + PIVOT("2", "hello", "bla") + LIST("1", "bla")`;
        assert.strictEqual(getNumberOfPivotFormulas(formula), 2);
        assert.strictEqual(getNumberOfListFormulas(formula), 1);
        assert.strictEqual(getNumberOfPivotFormulas("=1+1"), 0);
        assert.strictEqual(getNumberOfListFormulas("=1+1"), 0);
        assert.strictEqual(getNumberOfPivotFormulas("=bla"), 0);
        assert.strictEqual(getNumberOfListFormulas("=bla"), 0);
    });

    QUnit.test("getFirstPivotFunction does not crash when given crap", async function (assert) {
        assert.expect(8);
        assert.strictEqual(getFirstListFunction("=SUM(A1)"), undefined);
        assert.strictEqual(getFirstPivotFunction("=SUM(A1)"), undefined);
        assert.strictEqual(getFirstListFunction("=1+1"), undefined);
        assert.strictEqual(getFirstPivotFunction("=1+1"), undefined);
        assert.strictEqual(getFirstListFunction("=bla"), undefined);
        assert.strictEqual(getFirstPivotFunction("=bla"), undefined);
        assert.strictEqual(getFirstListFunction("bla"), undefined);
        assert.strictEqual(getFirstPivotFunction("bla"), undefined);
    });
});
