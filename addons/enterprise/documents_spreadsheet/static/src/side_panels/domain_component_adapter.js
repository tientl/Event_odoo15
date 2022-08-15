/** @odoo-module */

import { ComponentAdapter } from "web.OwlCompatibility";

/**
 * ComponentAdapter to allow using DomainSelector in a owl Component
 */
export default class DomainComponentAdapter extends ComponentAdapter {
    setup() {
        this.env = owl.Component.env;
    }
    get widgetArgs() {
        return [this.props.model, this.props.domain, { readonly: true, filters: {} }];
    }
}
