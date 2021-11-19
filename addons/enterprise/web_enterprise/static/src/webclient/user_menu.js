/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { systrayItem } from "@web/webclient/user_menu/user_menu";

/**
 * The user menu in enterprise should be removed if the screen is small
 * It is handled by the burger menu.
 */

patch(systrayItem, "web_enterprise.UserMenuItem", {
    isDisplayed: (env) => !env.isSmall,
});
