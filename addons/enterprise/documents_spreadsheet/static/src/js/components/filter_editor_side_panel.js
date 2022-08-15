/* global _ */

odoo.define("documents_spreadsheet.filter_editor_side_panel", function (require) {
    "use strict";

    const core = require("web.core");
    const spreadsheet = require("documents_spreadsheet.spreadsheet_extended");
    const DateFilterValue = require("documents_spreadsheet.DateFilterValue");
    const CommandResult = require("documents_spreadsheet.CommandResult");
    const {
        FieldSelectorWidget,
        FieldSelectorAdapter,
    } = require("documents_spreadsheet.field_selector_widget");
    const {
        ModelSelectorWidgetAdapter,
    } = require("documents_spreadsheet.model_selector_widget");
    const { StandaloneMany2OneField } = require("@documents_spreadsheet/js/widgets/standalone_many2one_field");
    const {
        TagSelectorWidget,
        TagSelectorWidgetAdapter,
    } = require("documents_spreadsheet.tag_selector_widget");
    const { useService } = require("@web/core/utils/hooks");
    const _t = core._t;
    const { useState } = owl.hooks;
    const sidePanelRegistry = spreadsheet.registries.sidePanelRegistry;
    const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

    /**
     * @typedef {import("../o_spreadsheet/helpers/basic_data_source").Field} Field
     */

    /**
     * This is the side panel to define/edit a global filter.
     * It can be of 3 different type: text, date and relation.
     */
    class FilterEditorSidePanel extends owl.Component {
        /**
         * @constructor
         */
        constructor(parent, props) {
            super(...arguments);
            this.id = undefined;
            this.state = useState({
                saved: false,
                label: undefined,
                type: undefined,
                pivotFields: {},
                listFields: {},
                text: {
                    defaultValue: undefined,
                },
                date: {
                    defaultValue: {},
                    type: undefined, // "year" | "month" | "quarter"
                    options: [],
                },
                relation: {
                    defaultValue: [],
                    displayNames: [],
                    relatedModelID: undefined,
                    relatedModelName: undefined,
                },
            });
            this.getters = this.env.getters;
            this.pivotIds = this.getters.getPivotIds();
            this.listIds = this.getters.getListIds();
            this.loadValues(props);
            // Widgets
            this.FieldSelectorWidget = FieldSelectorWidget;
            this.StandaloneMany2OneField = StandaloneMany2OneField;
            this.TagSelectorWidget = TagSelectorWidget;
            this.orm = useService("orm");
            this.notification = useService("notification");
        }

        /**
         * Retrieve the placeholder of the label
         */
        get placeholder() {
            return _.str.sprintf(_t("New %s filter"), this.state.type);
        }

        get missingLabel() {
            return this.state.saved && !this.state.label;
        }

        get missingPivotField() {
            return this.state.saved && Object.keys(this.state.pivotFields).length === 0;
        }

        get missingListField() {
            return this.state.saved && Object.keys(this.state.listFields).length === 0;
        }

        get missingModel() {
            return (
                this.state.saved &&
                this.state.type === "relation" &&
                !this.state.relation.relatedModelID
            );
        }

        /**
         * List of model names of all related models of all pivots
         * @returns {Array<string>}
         */
        get relatedModels() {
            const pivots = this.pivotIds.map((pivotId) =>
                Object.values(this.getters.getPivotFields(pivotId))
            );
            const lists = this.listIds.map((listId) =>
                Object.values(this.getters.getListFields(listId))
            );
            const all = pivots.concat(lists);
            return [
                ...new Set(
                    all
                        .flat()
                        .filter((field) => field.type === "many2one")
                        .map((field) => field.relation)
                ),
            ];
        }

        loadValues(props) {
            this.id = props.id;
            const globalFilter = this.id && this.getters.getGlobalFilter(this.id);
            this.state.label = globalFilter && globalFilter.label;
            this.state.type = globalFilter ? globalFilter.type : props.type;
            this.state.pivotFields = globalFilter ? globalFilter.pivotFields : {};
            this.state.listFields = globalFilter ? globalFilter.listFields : {};
            this.state.date.type =
                this.state.type === "date" && globalFilter ? globalFilter.rangeType : "year";
            if (globalFilter) {
                this.state[this.state.type].defaultValue = globalFilter.defaultValue;
                if (this.state.type === "relation") {
                    this.state.relation.relatedModelName = globalFilter.modelName;
                }
            }
        }

        async willStart() {
            const proms = [];
            proms.push(this.fetchModelFromName());
            for (const pivotId of this.getters.getPivotIds()) {
                proms.push(this.getters.waitForPivotMetaData(pivotId));
            }
            await Promise.all(proms);
        }

        mounted() {
            this.el.querySelector(".o_global_filter_label").focus();
        }

        /**
         * Get the first field which could be a relation of the current related
         * model
         *
         * @param {{Object.<string, Field>}} fields Fields to look in
         * @returns {Array<string, Field>|undefined}
         */
        _findRelation(fields) {
            return Object.entries(fields).find(
                    ([, fieldDesc]) =>
                        fieldDesc.type === "many2one" &&
                        fieldDesc.relation === this.state.relation.relatedModelName
                ) || [];
        }

        async onModelSelected(ev) {
            if (this.state.relation.relatedModelID !== ev.detail.value) {
                this.state.relation.defaultValue = [];
            }
            this.state.relation.relatedModelID = ev.detail.value;
            await this.fetchModelFromId();
            for (const pivotId of this.pivotIds) {
                const [field, fieldDesc] = this._findRelation(this.getters.getPivotFields(pivotId));
                this.state.pivotFields[pivotId] = field
                    ? { field, type: fieldDesc.type }
                    : undefined;
            }
            for (const listId of this.listIds) {
                const [field, fieldDesc] = this._findRelation(this.getters.getListFields(listId));
                this.state.listFields[listId] = field ? { field, type: fieldDesc.type } : undefined;
            }
        }

        async fetchModelFromName() {
            if (!this.state.relation.relatedModelName) {
                this.state.relation.relatedModelID = undefined;
                return;
            }
            const result = await this.orm.searchRead(
                "ir.model",
                [["model", "=", this.state.relation.relatedModelName]],
                ["id", "name"]
            );
            this.state.relation.relatedModelID = result[0] && result[0].id;
            if (!this.state.label) {
                this.state.label = result[0] && result[0].name;
            }
        }

        async fetchModelFromId() {
            if (!this.state.relation.relatedModelID) {
                this.state.relation.relatedModelName = undefined;
                return;
            }
            const result = await this.orm.searchRead(
                "ir.model",
                [["id", "=", this.state.relation.relatedModelID]],
                ["model", "name"]
            );

            this.state.relation.relatedModelName = result[0] && result[0].model;
            if (!this.state.label) {
                this.state.label = result[0] && result[0].name;
            }
        }

        onSelectedPivotField(id, ev) {
            const fieldName = ev.detail.chain[0];
            const field = this.getters.getPivotField(id, fieldName);
            if (field) {
                this.state.pivotFields[id] = {
                    field: fieldName,
                    type: field.type,
                };
            }
        }

        onSelectedListField(listId, ev) {
            const fieldName = ev.detail.chain[0];
            const field = this.getters.getListField(listId, fieldName);
            if (field) {
                this.state.listFields[listId] = {
                    field: fieldName,
                    type: field.type,
                };
            }
        }

        onSave() {
            this.state.saved = true;
            const missingField =
                (this.listIds.length !== 0 && this.missingListField) ||
                (this.pivotIds.length !== 0 && this.missingPivotField);
            if (this.missingLabel || missingField || this.missingModel) {
                this.notification.add(this.env._t("Some required fields are not valid"), {
                    type: "danger",
                    sticky: false,
                });
                return;
            }
            const cmd = this.id ? "EDIT_GLOBAL_FILTER" : "ADD_GLOBAL_FILTER";
            const id = this.id || uuidGenerator.uuidv4();
            const filter = {
                id,
                type: this.state.type,
                label: this.state.label,
                modelName: this.state.relation.relatedModelName,
                defaultValue: this.state[this.state.type].defaultValue,
                defaultValueDisplayNames: this.state[this.state.type].displayNames,
                rangeType: this.state.date.type,
                pivotFields: this.state.pivotFields,
                listFields: this.state.listFields,
            };
            const result = this.env.dispatch(cmd, { id, filter });
            if (result.isCancelledBecause(CommandResult.DuplicatedFilterLabel)) {
                this.notification.add(this.env._t("Duplicated Label"), {
                    type: "danger",
                    sticky: false,
                });
                return;
            }
            this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
        }

        onCancel() {
            this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
        }

        onValuesSelected(ev) {
            this.state.relation.defaultValue = ev.detail.value.map((record) => record.id);
            this.state.relation.displayNames = ev.detail.value.map((record) => record.display_name);
        }

        onTimeRangeChanged(ev) {
            this.state.date.defaultValue = ev.detail;
        }

        onDelete() {
            if (this.id) {
                this.env.dispatch("REMOVE_GLOBAL_FILTER", { id: this.id });
            }
            this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
        }

        onDateOptionChange(ev) {
            // TODO t-model does not work ?
            this.state.date.type = ev.target.value;
            this.state.date.defaultValue = {};
        }
    }
    FilterEditorSidePanel.template = "documents_spreadsheet.FilterEditorSidePanel";
    FilterEditorSidePanel.components = {
        FieldSelectorAdapter,
        ModelSelectorWidgetAdapter,
        TagSelectorWidgetAdapter,
        DateFilterValue,
    };

    sidePanelRegistry.add("FILTERS_SIDE_PANEL", {
        title: _t("Filter properties"),
        Body: FilterEditorSidePanel,
    });

    return FilterEditorSidePanel;
});
