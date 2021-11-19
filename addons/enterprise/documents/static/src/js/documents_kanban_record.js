odoo.define('documents.DocumentsKanbanRecord', function (require) {
'use strict';

/**
 * This file defines the KanbanRecord for the Documents Kanban view.
 */

const KanbanRecord = require('web.KanbanRecord');

const DocumentsKanbanRecord = KanbanRecord.extend({
    events: Object.assign({}, KanbanRecord.prototype.events, {
        'click': '_onSelectRecord',
        'click .o_record_selector': '_onAddRecordToSelection',
        'click .oe_kanban_previewer': '_onImageClicked',
        'click .o_request_image': '_onRequestImage',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {integer} resId of the record
     */
    getResId() {
        return this.id;
    },
    /**
     * When the record is updated and re-rendered, it loses its 'selected'
     * status (when a button in the kanban record is clicked, for example), so
     * here we ensure that it is kept if necessary.
     *
     * @override
     */
    async update() {
        const isSelected = this.$el.hasClass('o_record_selected');
        await this._super(...arguments);
        if (isSelected) {
            this.$el.addClass('o_record_selected');
        }
    },
    /**
     * @param {boolean} selected
     */
    updateSelection(selected) {
        this.$el.toggleClass('o_record_selected', selected);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
      * @param {jQueryEvent} ev
      * @param {Object} param1
      * @param {boolean} [param1.isKeepingSelection=false]
     */
    _toggleSelect(ev, { isKeepSelection=false }={}) {
        this.trigger_up('select_record', {
            isKeepSelection,
            originalEvent: ev,
            resId: this.getResId(),
        });
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle the selected status of the record
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddRecordToSelection(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._toggleSelect(ev, { isKeepSelection: true });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onImageClicked(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('kanban_image_clicked', {
            recordList: [this.recordData],
            recordId: this.recordData.id
        });
    },
    /**
     * Overrides to force the select/unselect as default action (instead of
     * opening the first link of the record)
     *
     * @override
     * @private
     */
    _onKeyDownOpenFirstLink(ev) {
        switch (ev.keyCode) {
            case $.ui.keyCode.ENTER:
                this._toggleSelect(ev, { isKeepSelection: false });
                break;
        }
    },
    /**
     * @private
     */
    _onRequestImage(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('set_file', {id: this.id});
    },
    /**
     * Toggle the selected status of the record (and unselect all other records)
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onSelectRecord(ev) {
        ev.preventDefault();
        // ignore clicks on oe_kanban_action elements
        if (!$(ev.target).hasClass('oe_kanban_action')) {
            this._toggleSelect(ev, { isKeepSelection: false });
        }
    },
});

return DocumentsKanbanRecord;

});
