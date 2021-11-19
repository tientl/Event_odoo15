/** @odoo-module **/

import { _t } from "web.core";
import spreadsheet from "../o_spreadsheet_loader";
const { args, toString } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

functionRegistry
    .add("FILTER_VALUE", {
        description: _t("Return the current value of a spreadsheet filter."),
        compute: function (filterName) {
            return this.getters.getFilterDisplayValue(filterName);
        },
        args: args(`
            filter_name (string) ${_t("The label of the filter whose value to return.")}
        `),
        returns: ["STRING"],
    })
    .add("PIVOT", {
        description: _t("Get the value from a pivot."),
        compute: function (pivotId, measureName, ...domain) {
            pivotId = toString(pivotId);
            const measure = toString(measureName);
            const args = domain.map(toString);
            this.getters.validatePivotArguments(pivotId, measure, args);
            return this.getters.getPivotValue(pivotId, measure, args, this);
        },
        args: args(`
        pivot_id (string) ${_t("ID of the pivot.")}
        measure_name (string) ${_t("Name of the measure.")}
        domain_field_name (string,optional,repeating) ${_t("Field name.")}
        domain_value (string,optional,repeating) ${_t("Value.")}
    `),
        returns: ["NUMBER", "STRING"],
    })
    .add("PIVOT_HEADER", {
        description: _t("Get the header of a pivot."),
        compute: function (pivotId, ...domain) {
            pivotId = toString(pivotId);
            const args = domain.map(toString);
            this.getters.validatePivotHeaderArguments(pivotId, args);
            return this.getters.getPivotHeaderValue(pivotId, args);
        },
        args: args(`
        pivot_id (string) ${_t("ID of the pivot.")}
        domain_field_name (string,optional,repeating) ${_t("Field name.")}
        domain_value (string,optional,repeating) ${_t("Value.")}
    `),
        returns: ["NUMBER", "STRING"],
    })
    .add("PIVOT.POSITION", {
        description: _t("Get the absolute ID of an element in the pivot"),
        compute: function () {
            throw new Error(_t(`[[FUNCTION_NAME]] cannot be called from the spreadsheet.`));
        },
        args: args(`
            pivot_id (string) ${_t("ID of the pivot.")}
            field_name (string) ${_t("Name of the field.")}
            position (number) ${_t("Position in the pivot")}
        `),
        returns: ["STRING"],
    });
