/** @odoo-module */

import { registry } from "@web/core/registry";
import { legacySetupProm } from "@web/legacy/legacy_setup";

// Adds to the legacy Owl environment the spreadsheet service.
// This is needed for the views having a legacy Owl env
// (i.e. FavoriteMenu->Link menu in spreadsheet)
(async () => {
    const legacyEnv = await legacySetupProm;
    registry.category("services").add("legacy_setup_spreadsheet", {
        dependencies: ["spreadsheet"],
        start(env, { spreadsheet }) {
            legacyEnv.services.spreadsheet = spreadsheet;
        },
    });
})();
