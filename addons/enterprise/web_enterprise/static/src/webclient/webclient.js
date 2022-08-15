/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { useService } from "@web/core/utils/hooks";
import { EnterpriseNavBar } from "./navbar/navbar";
import { hasTouch } from "@web/core/browser/feature_detection";

const { hooks } = owl;

export class WebClientEnterprise extends WebClient {
    setup() {
        super.setup();
        this.hm = useService("home_menu");
        useService("enterprise_legacy_service_provider");
        hooks.onMounted(() => {
            this.env.bus.on("HOME-MENU:TOGGLED", this, () => {
                if (!this.el) {
                    return;
                }
                this._updateClassList();
            });
            this._updateClassList();
            this.el.classList.toggle("o_touch_device", hasTouch());
        });
    }
    _updateClassList() {
        this.el.classList.toggle("o_home_menu_background", this.hm.hasHomeMenu);
        this.el.classList.toggle("o_has_home_menu", this.hm.hasHomeMenu);
    }
    _loadDefaultApp() {
        return this.hm.toggle(true);
    }
}
WebClientEnterprise.components = { ...WebClient.components, NavBar: EnterpriseNavBar };
