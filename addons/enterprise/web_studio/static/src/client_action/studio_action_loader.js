/** @odoo-module **/

import { memoize } from "@web/core/utils/functions";
import { registry } from "@web/core/registry";
import { loadPublicAsset } from "@web/core/assets";
import { loadLegacyViews } from "@web/legacy/legacy_views";
import { loadWysiwyg } from "web_editor.loader";

const actionRegistry = registry.category("actions");

const loadStudioAction = memoize(async (env) => {
    // some parts of the studio client action depend on the wysiwyg widgets, so load them first
    await loadWysiwyg();
    const orm = env.services.orm;
    await Promise.all([
        loadPublicAsset("web_studio.compiled_assets_studio", orm),
        loadLegacyViews({ orm }),
    ]);

    if (actionRegistry.get("studio") === loadStudioAction) {
        // At this point, the real studio client action should be loaded and have
        // replaced this function in the action registry. If it's not the case,
        // it probably means that there was a crash in the bundle (e.g. syntax
        // error). In this case, this action will remain in the registry, which
        // will lead to an infinite loop. To prevent that, we push another action
        // in the registry.
        actionRegistry.add(
            "studio",
            () => {
                const msg = env._t("Studio couldn't be loaded");
                env.services.notification.add(msg, { type: "danger" });
            },
            { force: true }
        );
    }

    return {
        target: "current",
        tag: "studio",
        type: "ir.actions.client",
    };
});

actionRegistry.add("studio", loadStudioAction);
