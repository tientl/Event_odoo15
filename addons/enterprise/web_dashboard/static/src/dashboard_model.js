/** @odoo-module */

import BasicModel from "web.BasicModel";
import { computeVariation } from "@web/core/utils/numbers";
import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/views/helpers/model";

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 */

function getPseudoRecords(meta, data) {
    const records = [];
    for (let i = 0; i < meta.domains.length; i++) {
        const record = {};
        for (const [statName, statInfo] of Object.entries(data)) {
            const { values } = statInfo;
            record[statName] = values[i];
        }
        records.push(record);
    }
    return records;
}

function getVariationAsRecords(data) {
    const periods = [];

    Object.entries(data).forEach(([fName, { variations }]) => {
        for (const varIndex in variations) {
            periods[varIndex] = periods[varIndex] || {};
            periods[varIndex][fName] = variations[varIndex];
        }
    });
    return periods;
}

function setupBasicModel(resModel, { getFieldsInfo, postProcessRecord }) {
    const basicModel = new BasicModel();
    const mkDatapoint = basicModel._makeDataPoint;

    const { viewFieldsInfo, fieldsInfo } = getFieldsInfo();

    let legacyModelParams;
    basicModel._makeDataPoint = (params) => {
        params = Object.assign({}, params, legacyModelParams);
        return mkDatapoint.call(basicModel, params);
    };

    return {
        makeRecord: async (params, data) => {
            legacyModelParams = params;
            const recId = await basicModel.makeRecord(resModel, viewFieldsInfo, fieldsInfo);
            const record = basicModel.get(recId);
            postProcessRecord(record, data);
            return record;
        },
        set isSample(bool) {
            basicModel.isSample = bool;
        },
    };
}

export class DashboardModel extends Model {
    setup(params) {
        super.setup(...arguments);

        this.keepLast = new KeepLast();

        const { aggregates, fields, formulae, resModel } = params;
        this.metaData = { fields, formulae, resModel };

        this.metaData.aggregates = [];
        for (const agg of aggregates) {
            const enrichedCopy = Object.assign({}, agg);

            const groupOperator = agg.groupOperator || "sum";
            enrichedCopy.measureSpec = `${agg.name}:${groupOperator}(${agg.field})`;

            const field = fields[agg.field];
            enrichedCopy.fieldType = field.type;

            this.metaData.aggregates.push(enrichedCopy);
        }

        this.metaData.statistics = this._statisticsAsFields();

        this.basicModel = setupBasicModel(this.metaData.resModel, {
            getFieldsInfo: () => {
                const legFieldsInfo = {
                    dashboard: {},
                };

                this.metaData.aggregates.forEach((agg) => {
                    legFieldsInfo.dashboard[agg.name] = Object.assign({}, agg, {
                        type: agg.fieldType,
                    });
                });

                Object.entries(this.metaData.fields).forEach(([fName, f]) => {
                    legFieldsInfo.dashboard[fName] = Object.assign({}, f);
                });

                let formulaId = 1;
                this.metaData.formulae.forEach((formula) => {
                    const formulaName = formula.name || `formula_${formulaId++}`;
                    const fakeField = Object.assign({}, formula, {
                        type: "float",
                        name: formulaName,
                    });
                    legFieldsInfo.dashboard[formulaName] = fakeField;
                    legFieldsInfo.formulas = Object.assign(legFieldsInfo.formulas || {}, {
                        [formulaName]: fakeField,
                    });
                });
                legFieldsInfo.default = legFieldsInfo.dashboard;
                return { viewFieldsInfo: legFieldsInfo.dashboard, fieldsInfo: legFieldsInfo };
            },
            postProcessRecord: (record, data) => {
                record.context = this.env.searchModel.context;
                record.viewType = "dashboard";

                const pseudoRecords = getPseudoRecords(this.metaData, data);
                record.data = pseudoRecords[0];

                if (this.metaData.domains.length > 1) {
                    const comparison = this.env.searchModel.getFullComparison();

                    record.comparisonData = pseudoRecords[1];
                    record.comparisonTimeRange = comparison.comparisonRange;
                    record.timeRange = comparison.range;
                    record.timeRanges = comparison;
                    record.variationData = getVariationAsRecords(data)[0];
                }
            },
        });
    }

    /**
     * @param {SearchParams} searchParams
     */
    async load(searchParams) {
        const { comparison, domain, context } = searchParams;
        const metaData = Object.assign({}, this.metaData, { context, domain });
        if (comparison) {
            metaData.domains = comparison.domains;
        } else {
            metaData.domains = [{ arrayRepr: domain, description: null }];
        }
        await this.keepLast.add(this._load(metaData));
        this.basicModel.isSample = metaData.useSampleModel;
        this.metaData = metaData;

        const legacyParams = {
            domain: metaData.domain,
            compare: metaData.domains.length > 1,
        };
        this._legacyRecord_ = await this.keepLast.add(
            this.basicModel.makeRecord(legacyParams, this.data)
        );
    }

    /**
     * @override
     */
    hasData() {
        return this.count > 0;
    }

    evalDomain(record, expr) {
        if (!Array.isArray(expr)) {
            return !!expr;
        }
        const domain = new Domain(expr);
        return domain.contains(getPseudoRecords(this.metaData, this.data)[0]);
    }

    /**
     * @param {strnig} statName
     * @returns {Object}
     */
    getStatisticDescription(statName) {
        return this.metaData.statistics[statName];
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * @protected
     * @param {Object} meta
     * @param {Object} data
     */
    _computeVariations(meta, data) {
        const n = meta.domains.length - 1;
        for (const statInfo of Object.values(data)) {
            const { values } = statInfo;
            statInfo.variations = new Array(n);
            for (let i = 0; i < n; i++) {
                statInfo.variations[i] = computeVariation(values[i], values[i + 1]);
            }
        }
    }

    /**
     * @protected
     * @param {Object} meta
     * @param {Object} data
     */
    _evalFormulae(meta, data) {
        const records = getPseudoRecords(meta, data);
        for (const formula of meta.formulae) {
            const { name, operation } = formula;
            data[name] = {
                values: new Array(meta.domains.length).fill(NaN),
            };
            for (let i = 0; i < meta.domains.length; i++) {
                try {
                    const value = evaluateExpr(operation, { record: records[i] });
                    if (isFinite(value)) {
                        data[name].values[i] = value;
                    }
                } catch (e) {
                    // pass
                }
            }
        }
    }

    /**
     * @protected
     * @param {Object} meta
     */
    async _load(meta) {
        const domainMapping = {};
        if (this.useSampleModel) {
            // force a read_group RPC without domain to determine if there is data to display
            domainMapping["[]"] = [];
        }
        for (const agg of meta.aggregates) {
            const domain = agg.domain || "[]";
            if (domain in domainMapping) {
                domainMapping[domain].push(agg);
            } else {
                domainMapping[domain] = [agg];
            }
        }

        const proms = [];
        const data = {};
        let count = 0;
        for (const [domain, aggregates] of Object.entries(domainMapping)) {
            for (let i = 0; i < meta.domains.length; i++) {
                const { arrayRepr } = meta.domains[i];
                proms.push(
                    this.orm
                        .readGroup(
                            meta.resModel,
                            Domain.and([domain, arrayRepr]).toList(),
                            aggregates.map((agg) => agg.measureSpec),
                            [],
                            { lazy: true },
                            meta.context
                        )
                        .then((groups) => {
                            const group = groups[0];
                            if (domain === "[]") {
                                count += group.__count;
                            }
                            for (const agg of aggregates) {
                                if (!data[agg.name]) {
                                    data[agg.name] = {
                                        values: new Array(meta.domains.length),
                                    };
                                }
                                const { type: fieldType } = meta.fields[agg.field];
                                data[agg.name].values[i] = group[agg.name] || (["date", "datetime"].includes(fieldType) ? NaN : 0);
                            }
                        })
                );
            }
        }
        await Promise.all(proms);

        this._evalFormulae(meta, data);
        this._computeVariations(meta, data);

        this.data = data;
        this.count = count;
    }

    /**
     * @protected
     */
    _statisticsAsFields() {
        const fakeFields = {};
        for (const agg of this.metaData.aggregates) {
            fakeFields[agg.name] = agg;
        }
        for (const formula of this.metaData.formulae) {
            fakeFields[formula.name] = Object.assign({}, formula, { fieldType: "float" });
        }
        return fakeFields;
    }
}

// TODO:
// comparisons beware of legacy record
// check fakeFields in legacyrecord
