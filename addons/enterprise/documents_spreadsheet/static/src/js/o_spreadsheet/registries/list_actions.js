/** @odoo-module */

import { MAXIMUM_CELLS_TO_INSERT } from "../constants";
import spreadsheet from "../o_spreadsheet_loader";

const { createFullMenuItem } = spreadsheet.helpers;

export const REINSERT_LIST_CHILDREN = (env) =>
    env.getters.getListIds().map((listId, index) => {
        return createFullMenuItem(`reinsert_list_${listId}`, {
            name: env.getters.getListDisplayName(listId),
            sequence: index,
            action: async (env) => {
                const zone = env.getters.getSelectedZone();
                const columns = env.getters.getListColumns(listId);
                env.getLinesNumber((linesNumber) => {
                    linesNumber = Math.min(
                        linesNumber,
                        Math.floor(MAXIMUM_CELLS_TO_INSERT / columns.length)
                    );
                    env.dispatch("REBUILD_ODOO_LIST", {
                        listId: listId,
                        anchor: [zone.left, zone.top],
                        sheetId: env.getters.getActiveSheetId(),
                        linesNumber,
                    });
                });
            },
        });
    });
