odoo.define('documents.DocumentsKanbanRenderer', function (require) {
'use strict';

/**
 * This file defines the Renderer for the Documents Kanban view, which is an
 * override of the KanbanRenderer.
 */

const DocumentsKanbanRecord = require('documents.DocumentsKanbanRecord');

const KanbanRenderer = require('web.KanbanRenderer');
const core = require('web.core');

var qweb = core.qweb;

const DocumentsKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanRecord: DocumentsKanbanRecord,
    }),

    /**
     * @override
     */
    async start() {
        this.$el.addClass('o_documents_kanban_view o_documents_view position-relative align-content-start flex-grow-1 flex-shrink-1');
        await this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Marks records as selected
     *
     * @private
     * @param {integer[]} selectedRecordIds
     */
    updateSelection(selectedRecordIds) {
        for (const widget of this.widgets) {
            const isSelected = selectedRecordIds.includes(widget.getResId());
            widget.updateSelection(isSelected);
        }
    },

    /**
     * @param {Object[]} shareAliases
     */
    updateHelper(shareAliases) {
        this.$('.o_view_nocontent_smiling_face').append(
            qweb.render('documents.HelperMailLine', shareAliases[0]));
    },
});

return DocumentsKanbanRenderer;

});
