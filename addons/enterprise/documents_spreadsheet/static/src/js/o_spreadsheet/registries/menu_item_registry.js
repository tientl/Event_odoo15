/** @odoo-module alias=documents_spreadsheet.MenuItemRegistry */

import { _t, _lt } from "web.core";
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "../helpers/odoo_functions_helpers";
import { pivotFormulaRegex } from "../helpers/pivot_helpers";
import spreadsheet from "../o_spreadsheet_loader";
import { REINSERT_LIST_CHILDREN } from "./list_actions";
import { INSERT_PIVOT_CELL_CHILDREN, REINSERT_PIVOT_CHILDREN } from "./pivot_actions";
const { cellMenuRegistry, topbarMenuRegistry } = spreadsheet.registries;
const { createFullMenuItem } = spreadsheet.helpers;
const { astToFormula } = spreadsheet;

//--------------------------------------------------------------------------
// Spreadsheet context menu items
//--------------------------------------------------------------------------

topbarMenuRegistry.add("file", { name: _t("File"), sequence: 10 });
topbarMenuRegistry.addChild("new_sheet", ["file"], {
    name: _lt("New"),
    sequence: 10,
    action: (env) => env.newSpreadsheet(),
});
topbarMenuRegistry.addChild("make_copy", ["file"], {
    name: _lt("Make a copy"),
    sequence: 20,
    action: (env) => env.makeCopy(),
});
topbarMenuRegistry.addChild("save_as_template", ["file"], {
    name: _lt("Save as Template"),
    sequence: 40,
    action: (env) => env.saveAsTemplate(),
});
topbarMenuRegistry.addChild("download", ["file"], {
    name: _lt("Download"),
    sequence: 50,
    action: (env) => env.download(),
    isReadonlyAllowed:true,
});
topbarMenuRegistry.add("data", {
    name: _lt("Data"),
    sequence: 60,
    children: function (env) {
        const pivots = env.getters.getPivotIds();
        const children = pivots.map((pivotId, index) =>
            createFullMenuItem(`item_pivot_${pivotId}`, {
                name: env.getters.getPivotDisplayName(pivotId),
                sequence: index,
                action: (env) => {
                    env.dispatch("SELECT_PIVOT", { pivotId: pivotId });
                    env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
                },
                icon: "fa fa-table",
                separator: index === env.getters.getPivotIds().length - 1,
            })
        );
        const lists = env.getters.getListIds().map((listId, index) => {
            return createFullMenuItem(`item_list_${listId}`, {
                name: env.getters.getListDisplayName(listId),
                sequence: index + pivots.length,
                action: (env) => {
                    env.dispatch("SELECT_ODOO_LIST", { listId: listId });
                    env.openSidePanel("LIST_PROPERTIES_PANEL", {});
                },
                icon: "fa fa-list",
                separator: index === env.getters.getListIds().length - 1,
            });
        });
        return children.concat(lists).concat([
            createFullMenuItem(`refresh_all_data`, {
                name: _t("Refresh all data"),
                sequence: 1000,
                action: (env) => {
                    env.dispatch("REFRESH_ALL_DATA_SOURCES");
                },
                separator: true,
            }),
            createFullMenuItem(`reinsert_pivot`, {
                name: _t("Re-insert pivot"),
                sequence: 1010,
                children: REINSERT_PIVOT_CHILDREN,
                isVisible: (env) => env.getters.getPivotIds().length,
            }),
            createFullMenuItem(`insert_pivot_cell`, {
                name: _t("Insert pivot cell"),
                sequence: 1020,
                children: INSERT_PIVOT_CELL_CHILDREN,
                isVisible: (env) => env.getters.getPivotIds().length,
                separator: true,
            }),
            createFullMenuItem(`reinsert_list`, {
                name: _t("Re-insert list"),
                sequence: 1020,
                children: REINSERT_LIST_CHILDREN,
                isVisible: (env) => env.getters.getListIds().length,
            }),
        ]);
    },
    isVisible: (env) => env.getters.getPivotIds().length || env.getters.getListIds().length,
});

cellMenuRegistry
    .add("reinsert_pivot", {
        name: _lt("Re-insert pivot"),
        sequence: 185,
        children: REINSERT_PIVOT_CHILDREN,
        isVisible: (env) => env.getters.getPivotIds().length,
        separator: true,
    })
    .add("insert_pivot_cell", {
        name: _lt("Insert pivot cell"),
        sequence: 180,
        children: INSERT_PIVOT_CELL_CHILDREN,
        isVisible: (env) => env.getters.getPivotIds().length,
    })
    .add("pivot_properties", {
        name: _lt("Pivot properties"),
        sequence: 170,
        action(env) {
            const [col, row] = env.getters.getPosition();
            const sheetId = env.getters.getActiveSheetId();
            const pivotId = env.getters.getPivotIdFromPosition(sheetId, col, row);
            env.dispatch("SELECT_PIVOT", { pivotId });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
        },
        isVisible: (env) => {
            const cell = env.getters.getActiveCell();
            return cell && cell.isFormula() && cell.content.match(pivotFormulaRegex);
        },
    })
    .add("listing_properties", {
        name: _lt("List properties"),
        sequence: 190,
        action(env) {
            const [col, row] = env.getters.getPosition();
            const sheetId = env.getters.getActiveSheetId();
            const listId = env.getters.getListIdFromPosition(sheetId, col, row);
            env.dispatch("SELECT_ODOO_LIST", { listId });
            env.openSidePanel("LIST_PROPERTIES_PANEL", {});
        },
        isVisible: (env) => {
            const [col, row] = env.getters.getPosition();
            const sheetId = env.getters.getActiveSheetId();
            return env.getters.getListIdFromPosition(sheetId, col, row) !== undefined;
        },
    })
    .add("reinsert_list", {
        name: _lt("Re-insert list"),
        sequence: 195,
        children: REINSERT_LIST_CHILDREN,
        isVisible: (env) => env.getters.getListIds().length,
        separator: true,
    })
    .add("see records", {
        name: _lt("See records"),
        sequence: 175,
        async action(env) {
            const cell = env.getters.getActiveCell();
            const {col, row, sheetId } = env.getters.getCellPosition(cell.id);
            const { args } = getFirstPivotFunction(cell.content);
            const evaluatedArgs = args
                .map(astToFormula)
                .map((arg) => env.getters.evaluateFormula(arg));
            const pivotId = env.getters.getPivotIdFromPosition(sheetId, col, row);
            const model = env.getters.getPivotModel(pivotId);
            await env.getters.waitForPivotMetaData(pivotId);
            const cache = env.getters.getPivotStructureData(pivotId);
            const domain = cache.getDomainFromFormula(evaluatedArgs);
            const name = env.getters.getPivotModelDisplayName(pivotId);
            await env.services.action.doAction({
                type: "ir.actions.act_window",
                name,
                res_model: model,
                view_mode: "list",
                views: [[false, "list"]],
                target: "current",
                domain,
            });
        },
        isVisible: (env) => {
            const cell = env.getters.getActiveCell();
            return (
                cell &&
                cell.evaluated.value !== "" &&
                !cell.evaluated.error &&
                getNumberOfPivotFormulas(cell.content) === 1
            );
        },
    });
