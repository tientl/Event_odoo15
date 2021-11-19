odoo.define("documents.DocumentsSearchPanel", function (require) {
    "use strict";

    /**
     * This file defines the DocumentsSearchPanel component, an extension of the
     * SearchPanel to be used in the documents kanban/list views.
     */

    const { device } = require("web.config");
    const SearchPanel = require("web.searchPanel");
    const { sprintf } = require("web.utils");

    const VALUE_SELECTOR = [
        ".o_search_panel_category_value",
        ".o_search_panel_filter_value",
    ].join();

    class DocumentsSearchPanel extends SearchPanel {

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {number} valueId
         * @returns {boolean}
         */
        _isUploading(valueId) {
            return this.props.uploadingFolderIds.includes(Number(valueId));
        }

        /**
         * @private
         * @param {HTMLElement} target
         * @param {DataTransfer} [dataTransfer]
         * @returns {boolean}
         */
        _isValidElement(target, dataTransfer) {
            return (
                dataTransfer &&
                dataTransfer.types.includes("o_documents_data") &&
                target &&
                target.closest(VALUE_SELECTOR)
            );
        }

        /**
         * @private
         * @param {number} sectionId
         * @returns {boolean}
         */
        _hasValidFieldName(sectionId) {
            const { fieldName } = this.model.get("sections", s => s.id === sectionId)[0];
            return ["folder_id", "tag_ids"].includes(fieldName);
        }

        /**
         * Gives the "dragover" class to the given element or remove it if none
         * is provided.
         * @private
         * @param {HTMLElement} [newDragFocus]
         */
        _updateDragOverClass(newDragFocus) {
            const allSelected = this.el.querySelectorAll(":scope .o_drag_over_selector");
            for (const selected of allSelected) {
                selected.classList.remove("o_drag_over_selector");
            }
            if (newDragFocus) {
                newDragFocus.classList.add("o_drag_over_selector");
            }
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {number} sectionId
         * @param {number | false} valueId
         * @param {DragEvent} ev
         */
        _onDragEnter(sectionId, valueId, { currentTarget, dataTransfer }) {
            if (
                valueId !== false &&
                this._isValidElement(currentTarget, dataTransfer) &&
                this._hasValidFieldName(sectionId)
            ) {
                this._updateDragOverClass(currentTarget);
                const [section] = this.model.get("sections", (s) => s.id === sectionId);
                const { childrenIds } = section.values.get(valueId);
                if (childrenIds && childrenIds.length) {
                    // if the hovered folder has children, opens it and re renders the search panel
                    // to allow drops in its children.
                    this.state.expanded[sectionId][valueId] = true;
                }
            } else {
                this._updateDragOverClass();
            }
        }

        /**
         * @private
         * @param {DragEvent} ev
         */
        _onDragLeave({ relatedTarget, dataTransfer }) {
            if (!this._isValidElement(relatedTarget, dataTransfer)) {
                this._updateDragOverClass(null);
            }
        }

        /**
         * Allows the selected kanban cards to be dropped in folders (workspaces) or tags.
         * @private
         * @param {number} sectionId
         * @param {number | false} valueId
         * @param {DragEvent} ev
         */
        async _onDrop(sectionId, valueId, { currentTarget, dataTransfer }) {
            this._updateDragOverClass(null);
            if (
                valueId === false || // prevents dropping in "All" folder
                currentTarget.classList.contains("active") || // prevents dropping in the current folder
                !this._isValidElement(currentTarget, dataTransfer) ||
                !this._hasValidFieldName(sectionId)
            ) {
                return;
            }
            const { fieldName } = this.model.get("sections", s => s.id === sectionId)[0];
            const data = JSON.parse(dataTransfer.getData("o_documents_data"));
            if (data.lockedCount) {
                return this.env.services.notification.notify({
                    title: "Partial transfer",
                    message: sprintf(
                        this.env._t(
                            "%s file(s) not moved because they are locked by another user"
                        ),
                        data.lockedCount
                    ),
                    type: "warning",
                });
            }
            if (fieldName === "folder_id") {
                this.model.dispatch("updateRecordFolderId", data.recordIds, valueId);
            } else {
                this.model.dispatch("updateRecordTagId", data.recordIds, valueId);
            }
        }
    }
    DocumentsSearchPanel.modelExtension = "DocumentsSearchPanel";

    DocumentsSearchPanel.defaultProps = Object.assign({},
        SearchPanel.defaultProps,
        { uploadingFolderIds: [] }
    );
    DocumentsSearchPanel.props = Object.assign({}, SearchPanel.props, {
        uploadingFolderIds: Array,
    });
    if (!device.isMobile) {
        DocumentsSearchPanel.template = "documents.SearchPanel";
    }

    return DocumentsSearchPanel;
});
