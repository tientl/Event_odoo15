odoo.define("documents/static/src/js/documents_search_panel_model_extension", function (require) {
    "use strict";

    const ActionModel = require("web.ActionModel");
    const SearchPanelModelExtension = require("web.searchPanelModelExtension");

    // Helpers
    const isFolderCategory = (s) => s.type === "category" && s.fieldName === "folder_id";
    const isTagFilter = (s) => s.type === "filter" && s.fieldName === "tag_ids";

    class DocumentsSearchPanelModelExtension extends SearchPanelModelExtension {

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * @override
         * @returns {any}
         */
        get(property) {
            switch (property) {
                case "folders": return this.getFolders();
                case "selectedFolderId": return this.getSelectedFolderId();
                case "selectedTagIds": return this.getSelectedTagIds();
                case "tags": return this.getTags();
            }
            return super.get(...arguments);
        }

        //---------------------------------------------------------------------
        // Actions / Getters
        //---------------------------------------------------------------------

        /**
         * Returns a description of each folder (record of documents.folder).
         * @returns {Object[]}
         */
        getFolders() {
            const { values } = this.getSections(isFolderCategory)[0];
            return [...values.values()];
        }

        /**
         * Returns the id of the current selected folder, if any, false
         * otherwise.
         * @returns {number | false}
         */
        getSelectedFolderId() {
            const { activeValueId } = this.getSections(isFolderCategory)[0];
            return activeValueId;
        }

        /**
         * Returns ids of selected tags.
         * @returns {number[]}
         */
        getSelectedTagIds() {
            const { values } = this.getSections(isTagFilter)[0];
            return [...values.values()].filter((value) => value.checked).map((value) => value.id);
        }

        /**
         * Returns a description of each tag (record of documents.tag).
         * @returns {Object[]}
         */
        getTags() {
            const { values } = this.getSections(isTagFilter)[0];
            return [...values.values()].sort((a, b) => {
                if (a.group_sequence === b.group_sequence) {
                    return a.sequence - b.sequence;
                } else {
                    return a.group_sequence - b.group_sequence;
                }
            });
        }

        /**
         * Overridden to write the new value in the local storage.
         * @override
         */
        toggleCategoryValue(sectionId, valueId) {
            super.toggleCategoryValue(...arguments);
            const { fieldName } = this.state.sections.get(sectionId);
            const storageKey = this._getStorageKey(fieldName);
            this.env.services.local_storage.setItem(storageKey, valueId);
        }

        /**
         * Updates the folder id of a record matching the given value.
         * @param {number[]} recordIds
         * @param {number} valueId
         */
        async updateRecordFolderId(recordIds, valueId) {
            await this.env.services.rpc({
                model: "documents.document",
                method: "write",
                args: [recordIds, { folder_id: valueId }],
            });
        }

        /**
         * Updates the tag ids of a record matching the given value.
         * @param {number[]} recordIds
         * @param {number} valueId
         */
        async updateRecordTagId(recordIds, valueId) {
            await this.env.services.rpc({
                model: "documents.document",
                method: "write",
                args: [recordIds, { tag_ids: [[4, valueId]] }],
            });
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @override
         */
        _ensureCategoryValue(category, valueIds) {
            if (valueIds.includes(category.activeValueId)) {
                return;
            }
            // If not set in context, or set to an unknown value, set active value
            // from localStorage
            const storageKey = this._getStorageKey(category.fieldName);
            category.activeValueId = this.env.services.local_storage.getItem(storageKey);
            if (valueIds.includes(category.activeValueId)) {
                return;
            }
            // If still not a valid value, get the search panel default value
            // from the given valid values.
            category.activeValueId = valueIds[Math.min(valueIds.length - 1, 1)];
        }

        /**
         * @private
         * @param {string} fieldName
         * @returns {string}
         */
        _getStorageKey(fieldName) {
            return `searchpanel_${this.config.modelName}_${fieldName}`;
        }

        /**
         * @override
         */
        _shouldWaitForData() {
            return true;
        }
    }

    ActionModel.registry.add("DocumentsSearchPanel", DocumentsSearchPanelModelExtension, 30);

    return DocumentsSearchPanelModelExtension;
});
