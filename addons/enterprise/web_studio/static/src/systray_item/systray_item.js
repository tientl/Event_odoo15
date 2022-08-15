/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class StudioSystray extends owl.Component {
    setup() {
        this.hm = useService("home_menu");
        this.studio = useService("studio");
        this.env.bus.on("ACTION_MANAGER:UI-UPDATED", this, (mode) => {
            if (mode !== "new") {
                this.render();
            }
        });
    }
    /**
    should react to actionamanger and home menu, store the action descriptor
    determine if the action is editable
   **/
    get buttonDisabled() {
        return !this.studio.isStudioEditable();
    }
    _onClick() {
        this.studio.open();
    }
}
StudioSystray.template = "web_studio.SystrayItem";

export const systrayItem = {
    Component: StudioSystray,
    isDisplayed: (env) => env.services.user.isSystem,
};

registry.category("systray").add("StudioSystrayItem", systrayItem, { sequence: 1 });
