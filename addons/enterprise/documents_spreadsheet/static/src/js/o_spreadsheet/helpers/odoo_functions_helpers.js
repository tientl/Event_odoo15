/** @odoo-module **/

import spreadsheet from "../o_spreadsheet_loader";

const { parse } = spreadsheet;

/**
 * @typedef {Object} OdooFunctionDescription
 * @property {string} functionName Name of the function
 * @property {Array<string>} args Arguments of the function
 * @property {boolean} isPivot True if the function is relative to a Pivot
 * @property {boolean} isList True if the function is relative to a List
 */

/**
 * Get the first Pivot function description of the given formula.
 *
 * @param {string} formula
 *
 * @returns {OdooFunctionDescription|undefined}
 */
export function getFirstPivotFunction(formula) {
    return _getOdooFunctions(formula).find((fn) => fn.isPivot);
}

/**
 * Get the first List function description of the given formula.
 *
 * @param {string} formula
 *
 * @returns {OdooFunctionDescription|undefined}
 */
export function getFirstListFunction(formula) {
    return _getOdooFunctions(formula).find((fn) => fn.isList);
}

/**
 * Parse a spreadsheet formula and detect the number of PIVOT functions that are
 * present in the given formula.
 *
 * @param {string} formula
 *
 * @returns {number}
 */
export function getNumberOfPivotFormulas(formula) {
    return _getOdooFunctions(formula).filter((fn) => fn.isPivot).length;
}

/**
 * Parse a spreadsheet formula and detect the number of LIST functions that are
 * present in the given formula.
 *
 * @param {string} formula
 *
 * @returns {number}
 */
export function getNumberOfListFormulas(formula) {
    return _getOdooFunctions(formula).filter((fn) => fn.isList).length;
}

/**
 * This function is used to extract the Odoo functions (PIVOT, LIST) from a
 * spreadsheet formula.
 *
 * @param {string} formula
 *
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
function _getOdooFunctions(formula) {
    let ast;
    try {
        ast = parse(formula);
    } catch (_) {
        return [];
    }
    return _getOdooFunctionsFromAST(ast);
}

/**
 * This function is used to extract the Odoo functions (PIVOT, LIST) from an AST.
 *
 * @param {Object} AST (see o-spreadsheet)
 *
 * @private
 * @returns {Array<OdooFunctionDescription>}
 */
function _getOdooFunctionsFromAST(ast) {
    switch (ast.type) {
        case "UNARY_OPERATION":
            return _getOdooFunctionsFromAST(ast.right);
        case "BIN_OPERATION": {
            return _getOdooFunctionsFromAST(ast.left).concat(_getOdooFunctionsFromAST(ast.right));
        }
        case "FUNCALL": {
            const functionName = ast.value.toUpperCase();
            if (["PIVOT", "PIVOT.HEADER", "PIVOT.POSITION"].includes(functionName)) {
                return [{ functionName, args: ast.args, isPivot: true }];
            } else if (["LIST", "LIST.HEADER"].includes(functionName)) {
                return [{ functionName, args: ast.args, isList: true }];
            } else {
                return ast.args.map((arg) => _getOdooFunctionsFromAST(arg)).flat();
            }
        }
        default:
            return [];
    }
}
