/** @odoo-module **/

import { ComponentAdapter } from 'web.OwlCompatibility';

export default class ViewsWidgetAdapter extends ComponentAdapter {
    setup() {
        super.setup(...arguments);
        // Overwrite the OWL/legacy env with the WOWL's one.
        this.env = owl.Component.env;
    }

    get widgetArgs() {
        const {model, view, additionalContext, params, mode, view_type} = this.props.data;
        return [
            model,
            view,
            additionalContext,
            params,
            mode,
            view_type
        ];
    }
}
