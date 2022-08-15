odoo.define("documents_spreadsheet.tag_selector_widget", function (require) {
    "use strict";

    const core = require("web.core");
    const { ComponentAdapter } = require("web.OwlCompatibility");
    const { FieldMany2ManyTags } = require("web.relational_fields");
    const StandaloneFieldManagerMixin = require("web.StandaloneFieldManagerMixin");
    const Widget = require("web.Widget");

    const QWeb = core.qweb;

    /**
     * This widget is used in the global filters to select a value for a
     * relation filter
     * It uses a FieldMany2ManyTags widget.
     */
    const TagSelectorWidget = Widget.extend(StandaloneFieldManagerMixin, {
        /**
         * @constructor
         *
         * @param {string} relatedModel Name of the related model
         * @param {Array<number>} selectedValues Values already selected
         */
        init: function (parent, relatedModel, selectedValues) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.relatedModel = relatedModel;
            this.selectedValues = selectedValues;
            this.widget = undefined;
        },
        /**
         * @override
         */
        willStart: async function () {
            await this._super.apply(this, arguments);
            await this._makeM2MWidget();
        },
        /**
         * @override
         */
        start: function () {
            const $content = $(QWeb.render("documents_spreadsheet.RelationTags", {}));
            this.$el.append($content);
            this.widget.appendTo($content);
            return this._super.apply(this, arguments);
        },
        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _confirmChange: async function () {
            const result = await StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            this.trigger_up("value_changed", { value: this.widget.value.data.map((record) => record.data) });
            return result;
        },
        /**
         * Create a record for the related model and a FieldMany2ManyTags linked
         * to this record
         */
        _makeM2MWidget: async function () {
            const options = {};
            options[this.relatedModel] = {
                options: {
                    no_create_edit: true,
                    no_create: true,
                },
            };
            const recordID = await this.model.makeRecord(
                this.relatedModel,
                [
                    {
                        fields: [
                            {
                                name: "id",
                                type: "integer",
                            },
                            {
                                name: "display_name",
                                type: "char",
                            },
                        ],
                        name: this.relatedModel,
                        relation: this.relatedModel,
                        type: "many2many",
                        value: this.selectedValues,
                    },
                ],
                options
            );
            this.widget = new FieldMany2ManyTags(
                this,
                this.relatedModel,
                this.model.get(recordID),
                { mode: "edit" }
            );
            this._registerWidget(recordID, this.relatedModel, this.widget);
        },
    });

    class TagSelectorWidgetAdapter extends ComponentAdapter {
        setup() {
            this.env = owl.Component.env;
        }
        /**
         * @override
         */
        get widgetArgs() {
            return [this.props.relatedModel, this.props.selectedValues];
        }
    }

    return { TagSelectorWidget, TagSelectorWidgetAdapter };
});
