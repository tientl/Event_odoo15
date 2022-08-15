/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { BurgerUserMenu } from "./user_menu/user_menu";
import { MobileSwitchCompanyMenu } from "./mobile_switch_company_menu/mobile_switch_company_menu";
import { MenuItem } from "@web/webclient/navbar/navbar";

/**
 * This file includes the widget Menu in mobile to render the BurgerMenu which
 * opens fullscreen and displays the user menu and the current app submenus.
 */

const SWIPE_ACTIVATION_THRESHOLD = 100;

export class BurgerMenu extends owl.Component {
    setup() {
        this.company = useService("company");
        this.user = useService("user");
        this.menuRepo = useService("menu");
        this.hm = useService("home_menu");
        this.state = owl.hooks.useState({
            isUserMenuOpened: false,
            isBurgerOpened: false,
        });
        this.swipeStartX = null;
        owl.hooks.onMounted(() => {
            this.env.bus.on("HOME-MENU:TOGGLED", this, () => {
                this._closeBurger();
            });
            this.env.bus.on("ACTION_MANAGER:UPDATE", this, (req) => {
                if (req.id) {
                    this._closeBurger();
                }
            });
        });
    }
    get currentApp() {
        return !this.hm.hasHomeMenu && this.menuRepo.getCurrentApp();
    }
    get currentAppSections() {
        return (
            (this.currentApp && this.menuRepo.getMenuAsTree(this.currentApp.id).childrenTree) || []
        );
    }
    get isUserMenuUnfolded() {
        return !this.isUserMenuTogglable || this.state.isUserMenuOpened;
    }
    get isUserMenuTogglable() {
        return this.currentApp && this.currentAppSections.length > 0;
    }
    _closeBurger() {
        this.state.isUserMenuOpened = false;
        this.state.isBurgerOpened = false;
    }
    _openBurger() {
        this.state.isBurgerOpened = true;
    }
    _toggleUserMenu() {
        this.state.isUserMenuOpened = !this.state.isUserMenuOpened;
    }
    _onMenuClicked(menu) {
        this.menuRepo.selectMenu(menu);
    }
    _onSwipeStart(ev) {
        this.swipeStartX = ev.changedTouches[0].clientX;
    }
    _onSwipeEnd(ev) {
        if (!this.swipeStartX) {
            return;
        }
        const deltaX = ev.changedTouches[0].clientX - this.swipeStartX;
        if (deltaX < SWIPE_ACTIVATION_THRESHOLD) {
            return;
        }
        this._closeBurger();
        this.swipeStartX = null;
    }
}
BurgerMenu.template = "web_enterprise.BurgerMenu";
BurgerMenu.components = {
    Portal: owl.misc.Portal,
    MenuItem,
    BurgerUserMenu,
    MobileSwitchCompanyMenu,
};

const systrayItem = {
    Component: BurgerMenu,
    isDisplayed: (env) => env.isSmall,
};

registry.category("systray").add("burger_menu", systrayItem, { sequence: 0 });
