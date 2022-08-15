/** @odoo-module */
/* global moment _ */

/**
 * @typedef {import("../../helpers/basic_data_source").Field} Field
 * @typedef {import("../core/filters_plugin").GlobalFilter} GlobalFilter
 */

import { _t } from "web.core";
import spreadsheet from "documents_spreadsheet.spreadsheet";
import Domain from "web.Domain";
import { constructDateDomain, constructDateRange, yearSelected } from "web.searchUtils";
import pyUtils from "web.py_utils";
import { getPeriodOptions } from "web.searchUtils";
import CommandResult from "../cancelled_reason";
import { checkFiltersTypeValueCombination } from "../../helpers/helpers";

const MONTHS = {
    january: { value: 0, granularity: "month" },
    february: { value: 1, granularity: "month" },
    march: { value: 2, granularity: "month" },
    april: { value: 3, granularity: "month" },
    may: { value: 4, granularity: "month" },
    june: { value: 5, granularity: "month" },
    july: { value: 6, granularity: "month" },
    august: { value: 7, granularity: "month" },
    september: { value: 8, granularity: "month" },
    october: { value: 9, granularity: "month" },
    november: { value: 10, granularity: "month" },
    december: { value: 11, granularity: "month" },
};
const THIS_YEAR = moment().year();
const YEARS = {
    this_year: { value: THIS_YEAR, granularity: "year" },
    last_year: { value: THIS_YEAR - 1, granularity: "year" },
    antepenultimate_year: { value: THIS_YEAR - 2, granularity: "year" },
};
const PERIOD_OPTIONS = Object.assign({}, MONTHS, YEARS);

export default class FiltersEvaluationPlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        this.orm = config.evalContext.env ? config.evalContext.env.services.orm : undefined;
        /**
         * Cache record display names for relation filters.
         * For each filter, contains a promise resolving to
         * the list of display names.
         */
        this.recordsDisplayName = {};
        /** @type {Object.<string, string|Array<string>|Object>} */
        this.values = {};
    }

    /**
     * Check if the given command can be dispatched
     *
     * @param {Object} cmd Command
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "SET_GLOBAL_FILTER_VALUE": {
                const filter = this.getters.getGlobalFilter(cmd.id);
                if (!filter) {
                    return CommandResult.FilterNotFound;
                }
                return checkFiltersTypeValueCombination(filter.type, cmd.value);
            }
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_GLOBAL_FILTER":
                this.recordsDisplayName[cmd.filter.id] = cmd.filter.defaultValueDisplayNames;
                break;
            case "EDIT_GLOBAL_FILTER":
                if(this.values[cmd.id] && this.values[cmd.id].rangeType !== cmd.filter.rangeType){
                    delete this.values[cmd.id];
                }
                this.recordsDisplayName[cmd.filter.id] = cmd.filter.defaultValueDisplayNames;
                break;
            case "SET_GLOBAL_FILTER_VALUE":
                this.recordsDisplayName[cmd.id] = cmd.displayNames;
                this._setGlobalFilterValue(cmd.id, cmd.value);
                break;
            case "REMOVE_GLOBAL_FILTER":
                delete this.recordsDisplayName[cmd.id];
                delete this.values[cmd.id];
                break;
        }
        switch (cmd.type) {
            case "START":
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
            case "REMOVE_GLOBAL_FILTER":
                this._updateAllDomains();
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get the current value of a global filter
     *
     * @param {string} id Id of the filter
     *
     * @returns {string|Array<string>|Object} value Current value to set
     */
    getGlobalFilterValue(id) {
        return id in this.values ? this.values[id].value : this.getters.getGlobalFilterDefaultValue(id);
    }

    /**
     * Get the number of active global filters
     *
     * @returns {number}
     */
    getActiveFilterCount() {
        return this.getters.getGlobalFilters().filter((filter) => {
            const value = this.getGlobalFilterValue(filter.id);
            switch (filter.type) {
                case "text":
                    return value;
                case "date":
                    return value && (value.year || value.period);
                case "relation":
                    return value && value.length;
            }
        }).length;
    }

    getFilterDisplayValue(filterName) {
        const filter = this.getters.getGlobalFilterLabel(filterName);
        if (!filter) {
            throw new Error(_.str.sprintf(_t(`Filter "%s" not found`), filterName));
        }
        const value = this.getGlobalFilterValue(filter.id);
        switch (filter.type) {
            case "text":
                return value || "";
            case "date":
                if(!value || !value.year) return ""
                const periodOptions = getPeriodOptions(moment());
                const year = periodOptions.find(({ id }) => value.year === id).description;
                const period = periodOptions.find(({ id }) => value.period === id);
                let periodStr = period && period.description;
                // Named months aren't in getPeriodOptions
                if(!period){
                    periodStr = MONTHS[value.period] && String(MONTHS[value.period].value + 1).padStart(2, "0");
                }
                // Use format "Q4 2022" instead of "Q2/2022" to not introduce possibly breaking changes in this version
                const separator = period && period.id.endsWith("quarter") ? " " : "/";
                return periodStr ? periodStr + separator + year : year;
            case "relation":
                if (!value || !this.orm) return "";
                if (!this.recordsDisplayName[filter.id]) {
                    this.orm.call(filter.modelName, "name_get", [value]).then((result) => {
                        const names = result.map(([, name]) => name);
                        this.recordsDisplayName[filter.id] = names;
                        this.dispatch("EVALUATE_CELLS", {
                            sheetId: this.getters.getActiveSheetId(),
                        });
                    });
                    return "";
                }
                return this.recordsDisplayName[filter.id].join(", ");
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Set the current value of a global filter
     *
     * @param {string} id Id of the filter
     * @param {string|Array<string>|Object} value Current value to set
     */
    _setGlobalFilterValue(id, value) {
        this.values[id] = {value: value, rangeType: this.getters.getGlobalFilter(id).rangeType};
    }

    /**
     * Update the domain of all pivots and all lists
     *
     * @private
     */
    _updateAllDomains() {
        for (const pivotId of this.getters.getPivotIds()) {
            const domain = this._getComputedDomain((filterId) =>
                this.getters.getGlobalFilterFieldPivot(filterId, pivotId)
            );
            this.dispatch("ADD_PIVOT_DOMAIN", { id: pivotId, domain, refresh: true });
        }
        for (const listId of this.getters.getListIds()) {
            const domain = this._getComputedDomain((filterId) =>
                this.getters.getGlobalFilterFieldList(filterId, listId)
            );
            this.dispatch("ADD_LIST_DOMAIN", { id: listId, domain, refresh: true });
        }
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Get the domain relative to a date field
     *
     * @private
     *
     * @param {GlobalFilter} filter
     * @param {Field} fieldDesc
     *
     * @returns {string|undefined}
     */
    _getDateDomain(filter, fieldDesc) {
        const value = this.getGlobalFilterValue(filter.id);
        const values = value && Object.values(value).filter(Boolean);
        if (!values || values.length === 0) {
            return undefined;
        }
        if (!yearSelected(values)) {
            values.push("this_year");
        }
        const field = fieldDesc.field;
        const type = fieldDesc.type;
        const dateFilterRange =
            filter.rangeType === "month"
                ? constructDateRange({
                      referenceMoment: moment(),
                      fieldName: field,
                      fieldType: type,
                      granularity: "month",
                      setParam: this._getSelectedOptions(values),
                  })
                : constructDateDomain(moment(), field, type, values);
        return Domain.prototype.arrayToString(pyUtils.eval("domain", dateFilterRange.domain, {}));
    }

    /**
     * Get the domain relative to a text field
     *
     * @private
     *
     * @param {GlobalFilter} filter
     * @param {Field} fieldDesc
     *
     * @returns {string|undefined}
     */
    _getTextDomain(filter, fieldDesc) {
        const value = this.getGlobalFilterValue(filter.id);
        if (!value) {
            return undefined;
        }
        const field = fieldDesc.field;
        return Domain.prototype.arrayToString([[field, "ilike", value]]);
    }

    /**
     * Get the domain relative to a relation field
     *
     * @private
     *
     * @param {GlobalFilter} filter
     * @param {Field} fieldDesc
     *
     * @returns {string|undefined}
     */
    _getRelationDomain(filter, fieldDesc) {
        const values = this.getGlobalFilterValue(filter.id);
        if (!values || values.length === 0) {
            return undefined;
        }
        const field = fieldDesc.field;
        return Domain.prototype.arrayToString([[field, "in", values]]);
    }

    /**
     * Get the computed domain of a global filters applied to the field given
     * by the callback
     *
     * @private
     *
     * @param {Function<Field>} getFieldDesc Callback to get the field description
     * on which the global filters is applied
     *
     * @returns {string}
     */
    _getComputedDomain(getFieldDesc) {
        let domain = "[]";
        for (let filter of this.getters.getGlobalFilters()) {
            const fieldDesc = getFieldDesc(filter.id);
            if (!fieldDesc) {
                continue;
            }
            let domainToAdd = undefined;
            switch (filter.type) {
                case "date":
                    domainToAdd = this._getDateDomain(filter, fieldDesc);
                    break;
                case "text":
                    domainToAdd = this._getTextDomain(filter, fieldDesc);
                    break;
                case "relation":
                    domainToAdd = this._getRelationDomain(filter, fieldDesc);
                    break;
            }
            if (domainToAdd) {
                domain = pyUtils.assembleDomains([domain, domainToAdd], "AND");
            }
        }
        return domain;
    }

    _getSelectedOptions(selectedOptionIds) {
        const selectedOptions = { year: [] };
        for (const optionId of selectedOptionIds) {
            const option = PERIOD_OPTIONS[optionId];
            const granularity = option.granularity;
            selectedOptions[granularity] = option.value;
        }
        return selectedOptions;
    }
}

FiltersEvaluationPlugin.modes = ["normal"];
FiltersEvaluationPlugin.getters = [
    "getFilterDisplayValue",
    "getGlobalFilterValue",
    "getActiveFilterCount",
];
