/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { useService } from "@web/core/utils/hooks";

const { hooks } = owl;
const { useRef } = hooks;

export class EnterpriseNavBar extends NavBar {
    setup() {
        super.setup();
        this.hm = useService("home_menu");
        this.menuAppsRef = useRef("menuApps");
        this.menuBrand = useRef("menuBrand");
        hooks.onMounted(() => {
            this.env.bus.on("HOME-MENU:TOGGLED", this, () => this._updateMenuAppsIcon());
            this._updateMenuAppsIcon();
        });
        hooks.onPatched(() => {
            this._updateMenuAppsIcon();
        });
    }
    get hasBackgroundAction() {
        return this.hm.hasBackgroundAction;
    }
    get isInApp() {
        return !this.hm.hasHomeMenu;
    }
    _updateMenuAppsIcon() {
        const menuAppsEl = this.menuAppsRef.el;
        menuAppsEl.classList.toggle("o_hidden", !this.isInApp && !this.hasBackgroundAction);
        menuAppsEl.classList.toggle("fa-th", this.isInApp);
        menuAppsEl.classList.toggle("fa-chevron-left", !this.isInApp && this.hasBackgroundAction);
        const title = !this.isInApp && this.hasBackgroundAction ? "Previous view" : "Home menu";
        menuAppsEl.title = title;
        menuAppsEl.ariaLabel = title;

        const menuBrand = this.menuBrand.el;
        if (menuBrand) {
            menuBrand.classList.toggle("o_hidden", !this.isInApp);
        }

        const appSubMenus = this.appSubMenus.el;
        if (appSubMenus) {
            appSubMenus.classList.toggle("o_hidden", !this.isInApp);
        }
    }
}
EnterpriseNavBar.template = "web_enterprise.EnterpriseNavBar";
