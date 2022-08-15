odoo.define('documents.DocumentsListRenderer', function (require) {
'use strict';

/**
 * This file defines the Renderer for the Documents List view, which is an
 * override of the ListRenderer.
 */

const ListRenderer = require('web.ListRenderer');
const core = require('web.core');

var qweb = core.qweb;

const DocumentsListRenderer = ListRenderer.extend({
    events: Object.assign({}, ListRenderer.prototype.events, {
        'click .o_data_row .o_list_record_selector': '_onClickListSelector',
    }),

    /**
     * @override
     */
    async start() {
        this.$el.addClass('o_documents_list_view o_documents_view');
        await this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {integer[]} selectedRecordIds
     */
    updateSelection(selectedRecordIds) {
        this.$('.o_data_row > .o_list_record_selector input:checked').prop('checked', false);
        for (const id of selectedRecordIds) {
            this.$(`.o_document_list_record[data-res-id="${id}"] .o_list_record_selector input`)
                .prop('checked', true);
        }
        this._updateSelection();
    },

    /**
     * @param {Object[]} shareAliases
     */
    updateHelper(shareAliases) {
        this.$('.o_view_nocontent_smiling_face').append(
            qweb.render('documents.HelperMailLine', shareAliases[0]));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Promise} resolved when the view has been rendered
     */
    async _renderView() {
        await this._super(...arguments);
        this.trigger_up('documents_view_rendered');
    },

    /**
     * @private
     * @param {boolean} param1.isKeepSelection if true, will ask to unselect other records
     * @param {integer} param1.resId
     * @param {jQueryEvent} ev
     */
    _toggleSelect(ev, { isKeepSelection, resId }) {
        if (!resId) {
            return;
        }
        this.trigger_up('select_record', {
            isKeepSelection,
            originalEvent: ev,
            resId,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickListSelector(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const resId = $(ev.currentTarget).closest('.o_data_row').data('res-id');
        this._toggleSelect(ev, {
            isKeepSelection: true,
            resId,
        });
    },
    /**
     * @override
     */
    _onKeyDown(ev) {
        if (ev.keyCode === 13) { // Enter key
            ev.stopPropagation();
            const $tr = $(ev.currentTarget).closest('tr');
            this._toggleSelect(ev, {
                isKeepSelection: false,
                resId: $tr.data('res-id'),
            });
        } else if (ev.keyCode === 32) {
            // press space on focused checkbox should be handled properly else it will
            // call _onClickListSelector as well as _onToggleCheckbox of list_renderer
            ev.preventDefault();
            ev.stopPropagation();
            const $tr = $(ev.currentTarget).closest('tr');
            this._toggleSelect(ev, {
                isKeepSelection: true,
                resId: $tr.data('res-id'),
            });
        } else {
            return this._super(...arguments);
        }
    },
    /**
     * @override
     * @param {MouseEvent} ev
     */
    _onRowClicked(ev) {
        ev.stopPropagation();
        this._toggleSelect(ev, {
            isKeepSelection: false,
            resId: $(ev.currentTarget).data('res-id'),
        });
    },
    /**
     *
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleSelection(ev) {
        const checked = $(ev.currentTarget).prop('checked') || false;
        this.trigger_up('toggle_all', {
            checked,
        });
    },

});

return DocumentsListRenderer;

});
