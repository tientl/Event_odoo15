odoo.define("documents_spreadsheet.field_selector_widget", function (require) {
    const config = require("web.config");
    const FieldSelectorWidget = require("web.ModelFieldSelector");
    const { ComponentAdapter } = require("web.OwlCompatibility");

    const filters = {
        text: ["many2one", "text", "char"],
        date: ["datetime", "date"],
        relation: ["many2one", "many2many", "one2many"],
    };

    /**
     * This adapter is used in the global filters to select a field for each
     * pivot.
     * It uses a FieldSelectorWidget.
     */
    class FieldSelectorAdapter extends ComponentAdapter {

        setup() {
            this.env = owl.Component.env;
        }
        /**
         * Only display the relevant fields
         * @param {Array} fields Fields to filter
         * @param {string} typeFilter Type of the filter (text, date, relation)
         * @param {string?} relatedModel Name of the related model
         */
        filter(fields, typeFilter, relatedModel) {
            const _fields = {};
            for (let [key, value] of Object.entries(fields)) {
                if (filters[typeFilter].includes(value.type)) {
                    if (!relatedModel || value.relation === relatedModel) {
                        _fields[key] = value;
                    }
                }
            }
            return _fields;
        }

        /**
         * @override
         */
        get widgetArgs() {
            const fields = this.filter(this.props.fields, this.props.type, this.props.relatedModel);
            const chain = this.props.selected ? [this.props.selected.field] : [];
            return [
                this.props.model,
                chain,
                {
                    fields,
                    readonly: false,
                    followRelations: false,
                    debugMode: config.isDebug(),
                },
            ];
        }
    }

    return { FieldSelectorWidget, FieldSelectorAdapter };
});
