odoo.define("documents_spreadsheet.DocumentsControllerMixin", function (require) {
    "use strict";

    const TemplateDialog = require("documents_spreadsheet.TemplateDialog");
    const { ComponentWrapper } = require("web.OwlCompatibility");

    const DocumentsSpreadsheetControllerMixin = {
        events: {
            "click .o_documents_kanban_spreadsheet": "_onNewSpreadSheet",
        },
        custom_events: {
            spreadsheet_created: "_onSpreadsheetCreated",
            dialog_closed: "_destroyDialog",
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Disables the control panel buttons if there is no selected folder.
         *
         * @private
         */
        updateButtons() {
            const selectedFolderId = this.searchModel.get("selectedFolderId");
            this.$buttons[0].querySelector(
                ".o_documents_kanban_spreadsheet"
            ).disabled = !selectedFolderId;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * If there is a template dialog it will be unmounted.
         *
         * @private
         */
        _destroyDialog() {
            if (this.templateDialog) {
                this.templateDialog.destroy();
            }
            this.templateDialog = undefined;
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Create a new spreadsheet
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onNewSpreadSheet: async function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            const context = this.model.get(this.handle).getContext();
            const searchView = await this.loadFieldView(
                "spreadsheet.template",
                context,
                false,
                "search"
            );
            this.templateDialog = new ComponentWrapper(this, TemplateDialog, {
                searchView,
                folderId: this.searchModel.get("selectedFolderId"),
                context,
            });
            await this.templateDialog.mount(this.el);
        },
        /**
         * This handler is called to open en redirect a user to a sheet.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onSpreadsheetCreated(ev) {
            this.do_action({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: ev.data.spreadsheetId,
                },
            });
        },
    };

    return DocumentsSpreadsheetControllerMixin;
});
