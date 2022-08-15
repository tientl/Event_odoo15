odoo.define("documents_spreadsheet.TemplateDialog", function (require) {
    "use strict";

    const Dialog = require("web.OwlDialog");
    const SearchBar = require("web.SearchBar");
    const Pager = require("web.Pager");
    const ActionModel = require("web.ActionModel");

    const spreadsheet = require("@documents_spreadsheet/js/o_spreadsheet/o_spreadsheet_loader")[Symbol.for("default")];
    const { UNTITLED_SPREADSHEET_NAME } = require("@documents_spreadsheet/constants");
    const { getDataFromTemplate } = require("documents_spreadsheet.pivot_utils");
    const { DropPrevious } = require("web.concurrency");

    const { useState, useSubEnv } = owl.hooks;

    const { createEmptyWorkbookData } = spreadsheet.helpers;

    class TemplateDialog extends owl.Component {
        constructor() {
            super(...arguments);
            this.dialogTitle = this.env._t("New Spreadsheet");
            this.limit = 9;
            this.state = useState({
                isOpen: true,
                templates: [],
                templatesCount: 0,
                selectedTemplateId: null,
                currentMinimum: 1,
                offset: 0,
                isCreating: false,
            });
            const searchModelConfig = {
                context: this.props.context,
                domain: [],
                env: owl.Component.env,
            };
            const archs = { search: this.props.searchView.arch };
            const { ControlPanel: controlPanelInfo } = ActionModel.extractArchInfo(archs);
            const extensions = {
                ControlPanel: {
                    archNodes: controlPanelInfo.children,
                    fields: this.props.searchView.fields,
                },
            };
            this.model = new ActionModel(extensions, searchModelConfig);
            this.model.on("search", this, this._fetchTemplates);
            useSubEnv({
                searchModel: this.model,
            });
            this.dp = new DropPrevious();
        }

        /**
         * @override
         */
        async willStart() {
            await this._fetchTemplates({
                domain: [],
                context: this.props.context,
            });
        }

        /**
         * Fetch templates according to the search domain and the pager
         * offset given as parameter.
         * @private
         * @param {Object} searchQuery
         * @param {number} offset
         * @returns {Promise<void>}
         */
        async _fetchTemplates(searchQuery, offset = 0) {
            const { domain, context, orderedBy } = searchQuery;
            const { length, records } = await this.dp.add(
                this.env.services.rpc({
                    route: "/web/dataset/search_read",
                    model: "spreadsheet.template",
                    fields: ["name"],
                    domain,
                    context,
                    offset,
                    limit: this.limit,
                    orderBy: orderedBy,
                })
            );
            this.state.templates = records;
            this.state.templatesCount = length;
        }

        /**
         * Will create a spreadsheet based on the currently selected template
         * and the current folder we are in. The user will be notified and
         * the newly created spreadsheet will be opened.
         * @private
         * @returns {Promise<void>}
         */
        async _createSpreadsheet() {
            if (!this._hasSelection()) return;
            this.state.isCreating = true;
            const templateId = this.state.selectedTemplateId;
            const data =
                templateId !== null
                    ? await getDataFromTemplate(this.env.services.rpc, templateId)
                    : createEmptyWorkbookData(`${this.env._t("Sheet")}1`);
            const name =
                templateId !== null
                    ? this.state.templates.find((template) => template.id === templateId).name
                    : UNTITLED_SPREADSHEET_NAME;
            const spreadsheetId = await this.env.services.rpc({
                model: "documents.document",
                method: "create",
                args: [
                    {
                        name,
                        mimetype: "application/o-spreadsheet",
                        folder_id: this.props.folderId,
                        handler: "spreadsheet",
                        raw: JSON.stringify(data),
                    },
                ],
                context: this.props.context,
            });
            this.env.services.notification.notify({
                type: "info",
                message: this.env._t("New sheet saved in Documents"),
                sticky: false,
            });
            this.trigger("spreadsheet-created", { spreadsheetId });
        }

        /**
         * Changes the currently selected template in the state.
         * @private
         * @param {number | null} templateId
         */
        _selectTemplate(templateId) {
            this.state.selectedTemplateId = templateId;
        }

        /**
         * Returns whether or not templateId is currently selected.
         * @private
         * @param {number | null} templateId
         * @returns {boolean}
         */
        _isSelected(templateId) {
            return this.state.selectedTemplateId === templateId;
        }

        /**
         * Check if any template or the Blank template is selected.
         * @private
         * @returns {boolean}
         */
        _hasSelection() {
            return (
                this.state.templates.find(
                    (template) => template.id === this.state.selectedTemplateId
                ) || this.state.selectedTemplateId === null
            );
        }

        /**
         * This function will be called when the user uses the pager. Based on the
         * pager state, new templates will be fetched.
         * @private
         * @param {CustomEvent} ev
         * @returns {Promise<void>}
         */
        _onPagerChanged(ev) {
            ev.stopPropagation();
            const { currentMinimum } = ev.detail;
            this.state.currentMinimum = currentMinimum;
            return this._fetchTemplates(this.model.get("query"), this.state.currentMinimum - 1);
        }

        /**
         * Check if the create button should be disabled.
         * @private
         * @returns {boolean}
         */
        _buttonDisabled() {
            return this.state.isCreating || !this._hasSelection();
        }
    }
    TemplateDialog.components = { Dialog, SearchBar, Pager };
    TemplateDialog.template = "documents_spreadsheet.TemplateDialog";
    return TemplateDialog;
});
