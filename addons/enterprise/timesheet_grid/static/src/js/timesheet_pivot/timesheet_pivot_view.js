/** @odoo-module **/

import { PivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

const { onMounted, onPatched } = owl.hooks;

const viewRegistry = registry.category("views");

class TimesheetPivotView extends PivotView {
    setup() {
        super.setup();
        onMounted(this.bindPlayStoreIcon);
        onPatched(this.bindPlayStoreIcon);
    }

    /**
     * Bind the event for play store icons
     */
    bindPlayStoreIcon() {
        const playStore = this.el.querySelector(".o_config_play_store");
        const appStore = this.el.querySelector(".o_config_app_store");

        if (playStore) {
            playStore.onclick = this.onClickAppStoreIcon.bind(this);
        }
        if (appStore) {
            appStore.onclick = this.onClickAppStoreIcon.bind(this);
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onClickAppStoreIcon(ev) {
        ev.preventDefault();
        const googleUrl = "https://play.google.com/store/apps/details?id=com.odoo.OdooTimesheets";
        const appleUrl = "https://apps.apple.com/be/app/awesome-timesheet/id1078657549";
        const url = ev.target.classList.contains("o_config_play_store") ? googleUrl : appleUrl;

        if (!this.env.isSmall) {
            const actionDesktop = {
                name: this.env._t("Download our App"),
                type: "ir.actions.client",
                tag: "timesheet_qr_code_modal",
                target: "new",
                params: { url },
            };
            this.actionService.doAction(actionDesktop);
        } else {
            this.actionService.doAction({ type: "ir.actions.act_url", url });
        }
    }
}

viewRegistry.add("timesheet_pivot_view", TimesheetPivotView);
