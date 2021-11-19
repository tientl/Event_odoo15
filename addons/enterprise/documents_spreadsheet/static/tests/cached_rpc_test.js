/** @odoo-module */

import { nextTick } from "web.test_utils";
import CachedRPC from "../src/js/o_spreadsheet/helpers/cached_rpc";

const { module, test } = QUnit;

module("documents_spreadsheet > cached_rpc", {}, () => {
    test("Fields_get and search_read are only loaded once", async function (assert) {
        assert.expect(4);

        const rpc = async (params) => {
            assert.step(`rpc-${params.method}-${params.model}`);
            return {};
        };

        const cache = new CachedRPC(rpc);
        await cache.delayedRPC({
            model: "A",
            method: "fields_get",
        });
        await cache.delayedRPC({
            model: "A",
            method: "fields_get",
        });
        await cache.delayedRPC({
            model: "A",
            method: "search_read",
        });
        await cache.delayedRPC({
            model: "B",
            method: "fields_get",
        });
        assert.verifySteps(["rpc-fields_get-A", "rpc-search_read-A", "rpc-fields_get-B"]);
    });

    test("Name_get are collected before executing", async function (assert) {
        assert.expect(7);

        const rpc = async (params) => {
            assert.step(`rpc-${params.model}-${params.args[0].join("-")}`);
            const result = [];
            for (const arg of params.args[0]) {
                result.push([arg, arg]);
            }
            return result;
        };

        const cache = new CachedRPC(rpc);
        cache
            .delayedRPC({
                model: "A",
                method: "name_get",
                args: [1],
            })
            .then((result) => {
                assert.strictEqual(result, 1);
            });
        cache
            .delayedRPC({
                model: "A",
                method: "name_get",
                args: [2],
            })
            .then((result) => {
                assert.strictEqual(result, 2);
            });
        cache
            .delayedRPC({
                model: "A",
                method: "name_get",
                args: [3],
            })
            .then((result) => {
                assert.strictEqual(result, 3);
            });
        cache
            .delayedRPC({
                model: "B",
                method: "name_get",
                args: [4],
            })
            .then((result) => {
                assert.strictEqual(result, 4);
            });
        await nextTick();
        assert.verifySteps(["rpc-A-1-2-3", "rpc-B-4"]);
    });
});
