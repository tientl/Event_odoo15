/** @odoo-module */

import { _t } from "web.core";
import spreadsheet from "documents_spreadsheet.spreadsheet";
import {
    getFirstListFunction,
    getNumberOfListFormulas,
} from "../../helpers/odoo_functions_helpers";

const { astToFormula } = spreadsheet;

export default class ListAutofillPlugin extends spreadsheet.UIPlugin {
    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill of a list function
     *
     * @param {string} formula List formula
     * @param {boolean} isColumn True if autofill is LEFT/RIGHT, false otherwise
     * @param {number} increment number of steps
     *
     * @returns Autofilled value
     */
    getNextListValue(formula, isColumn, increment) {
        if (getNumberOfListFormulas(formula) !== 1) {
            return formula;
        }
        const { functionName, args } = getFirstListFunction(formula);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        const listId = evaluatedArgs[0];
        const columns = this.getters.getListColumns(listId);
        if (functionName === "LIST") {
            const position = parseInt(evaluatedArgs[1], 10);
            const field = evaluatedArgs[2];
            if (isColumn) {
                /** Change the field */
                const index = columns.findIndex((col) => col === field) + increment;
                if (index < 0 || index >= columns.length) {
                    return "";
                }
                return this._getListFunction(listId, position, columns[index]);
            } else {
                /** Change the position */
                const nextPosition = position + increment;
                if (nextPosition === 0) {
                    return this._getListHeaderFunction(listId, field);
                }
                if (nextPosition < 0) {
                    return "";
                }
                return this._getListFunction(listId, nextPosition, field);
            }
        }
        if (functionName === "LIST.HEADER") {
            const field = evaluatedArgs[1];
            if (isColumn) {
                /** Change the field */
                const index = columns.findIndex((col) => col === field) + increment;
                if (index < 0 || index >= columns.length) {
                    return "";
                }
                return this._getListHeaderFunction(listId, columns[index]);
            } else {
                /** If down, set position */
                if (increment > 0) {
                    return this._getListFunction(listId, increment, field);
                }
                return "";
            }
        }
        return formula;
    }

    /**
     * Compute the tooltip to display from a Pivot formula
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     */
    getTooltipListFormula(formula, isColumn) {
        if (!formula) {
            return [];
        }
        const { functionName, args } = getFirstListFunction(formula);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        if (isColumn || functionName === "LIST.HEADER") {
            const fieldName = functionName === "LIST" ? evaluatedArgs[2] : evaluatedArgs[1];
            return this.getters.getListFieldName(evaluatedArgs[0], fieldName);
        }
        return _t("Record #") + evaluatedArgs[1];
    }

    _getListFunction(listId, position, field) {
        return `=LIST("${listId}","${position}","${field}")`;
    }

    _getListHeaderFunction(listId, field) {
        return `=LIST.HEADER("${listId}","${field}")`;
    }
}

ListAutofillPlugin.modes = ["normal", "headless"];
ListAutofillPlugin.getters = ["getNextListValue", "getTooltipListFormula"];
