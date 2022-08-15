/** @odoo-module */

/**
 * This class is used to collect and regroup all the RPCs requests that are
 * executed in Spreadsheet. It contributes to reduce the number of requests.
 *
 * LUL TODO convert to use the `orm` service. I already have a working implementation
 * but it currently doesn't fit well with some other non-converted elements (views, helpers).
 */
export default class CachedRPC {
    /**
     *
     * @param {Function} rpc RPC Function
     */
    constructor(rpc) {
        this.rpc = rpc;
        /** Cache of the requests 'fields_get' and 'search_read' */
        this.cache = {};
        /** Cache of the requests 'name_get' */
        this.nameGets = {};
        /** Promise defined the first time a 'name_get' request is started */
        this.setTimeoutPromise = undefined;
    }

    /**
     * Collect and regroup the RPC.
     * - 'field_get' and 'search_read':
     *      If the value is already in cache, return it. Else, trigger a rpc and
     *      set it in cache
     * - 'name_get':
     *      Collect all the ids to collect and trigger a rpc
     *
     * @param {Object} params Params of the RPC
     * @param {Object} options Options of the RPC
     */
    async delayedRPC(params, options) {
        if (params.method === "fields_get") {
            const key = JSON.stringify(params);
            if (!(key in this.cache)) {
                this.cache[key] = this.rpc(params, options);
            }
            return this.cache[key];
        }
        if (params.method === "name_get") {
            const id = params.args[0];
            const model = params.model;
            if (!(model in this.nameGets)) {
                this.nameGets[model] = {
                    toFetch: [],
                };
            }
            if (this.nameGets[model][id]) {
                return this.nameGets[model][id];
            }
            this.nameGets[model].toFetch.push(id);
            await this._executeNameGetRPCAfterTimeout();
            return this.nameGets[model][id];
        }
        return this.rpc(params, options);
    }

    /**
     * Execute the "name_get" request after a setTimeout, in order to collect
     * all the required ids.
     *
     * The first time this function is called, a promise is created in order to
     * execute the RPC in the setTimeout. If this promise is already created,
     * this promise is returned.
     */
    async _executeNameGetRPCAfterTimeout() {
        if (this.setTimeoutPromise) {
            return this.setTimeoutPromise;
        }
        this.setTimeoutPromise = new Promise((resolve, reject) => {
            setTimeout(async () => {
                try {
                    const promises = {};
                    for (const [model, params] of Object.entries(this.nameGets)) {
                        if (params.toFetch.length) {
                            promises[model] = this.rpc({
                                model,
                                args: [Array.from(new Set(params.toFetch))],
                                method: "name_get",
                            }).then((result) => {
                                for (const r of result) {
                                    this.nameGets[model][r[0]] = r[1];
                                }
                            });
                        }
                        this.nameGets[model].toFetch = [];
                    }
                    await Promise.all(Object.values(promises));
                    resolve();
                } catch (e) {
                    reject(e);
                } finally {
                    this.setTimeoutPromise = undefined;
                }
            });
        });
        return this.setTimeoutPromise;
    }
}
