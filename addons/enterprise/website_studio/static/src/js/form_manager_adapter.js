/** @odoo-module **/

import { ComponentAdapter } from "web.OwlCompatibility";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

import FormManager from "website_studio.FormManager";

export class FormManagerAdapter extends ComponentAdapter {
    constructor(parent, props) {
        props.Component = FormManager;
        super(...arguments);
        this.studio = useService("studio");
        this.env = owl.Component.env;
    }

    get widgetArgs() {
        return [this.props.action, { action: this.studio.editedAction }];
    }
}

registry.category("actions").add("action_web_studio_form", FormManagerAdapter);
