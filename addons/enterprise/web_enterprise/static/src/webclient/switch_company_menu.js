/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { systrayItem } from "@web/webclient/switch_company_menu/switch_company_menu";

/**
 * The company menu in enterprise should be removed if the screen is small
 * It is handled by the burger menu.
 */

patch(systrayItem, "web_enterprise.CompanyMenuItem", {
    isDisplayed(env) {
        return this._super(...arguments) && !env.isSmall;
    },
});
