/** @odoo-module **/

import { useEffect } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

const { Component, hooks } = owl;
const { useSubEnv } = hooks;

/**
 * This file defines the ViewWrapper component, used to wrap sub views in the
 * dashboard. It allows to define a specific env for each sub view, with their
 * own callback recorders such that the dashboard can get their local and global
 * states, and their context.
 *
 * Moreover, it adds a button to open sub views in fullscreen, and changes some
 * classNames on control panel buttons to slightly change their style.
 */
export class ViewWrapper extends Component {
    setup() {
        useSubEnv(this.props.callbackRecorders);
        useEffect(() => {
            const btns = this.el.querySelectorAll(".btn-primary, .btn-secondary, .btn-light");
            btns.forEach((btn) => {
                btn.classList.remove("btn-primary", "btn-secondary", "btn-light");
                btn.classList.add("btn-outline-secondary");
            });
            if (this.props.type === "cohort") {
                this.el
                    .querySelectorAll("[class*=interval_button]")
                    .forEach((el) => el.classList.add("text-muted"));
            }
        });
    }
}
ViewWrapper.template = "web_dashboard.ViewWrapper";
ViewWrapper.components = { View };
