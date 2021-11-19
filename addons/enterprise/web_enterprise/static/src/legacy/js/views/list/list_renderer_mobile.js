odoo.define('web_enterprise.MobileListRenderer', function (require) {
"use strict";

const config = require('web.config');

if (!config.device.isMobile) {
    return;
}

const ListRenderer = require('web.ListRenderer');

ListRenderer.include({

    events: Object.assign({}, ListRenderer.prototype.events, {
        'touchstart .o_data_row': '_onTouchStartSelectionMode',
        'touchmove .o_data_row': '_onTouchMoveSelectionMode',
        'touchend .o_data_row': '_onTouchEndSelectionMode',
    }),

    init() {
        this._super(...arguments);
        this.longTouchTimer = null;
        this.LONG_TOUCH_THRESHOLD = 400;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * In mobile, disable the read-only editable list.
     *
     * @override
     */
    isEditable() {
        return this.editable;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the jQuery node used to update the selection ; visiblity insensitive.
     *
     * @override
     */
    _getSelectableRecordCheckboxes() {
        return this.$('tbody .o_list_record_selector input:not(:disabled)');
    },

    /**
     * In mobile, disable the read-only editable list.
     *
     * @override
     */
    _isRecordEditable() {
        return this.editable;
    },

    /**
     * Reset the current long-touch timer.
     *
     * @private
     */
    _resetLongTouchTimer() {
        if (this.longTouchTimer) {
            clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    },

    /**
     * @override
     */
    _updateSelection() {
        this._super(...arguments);
        this._getSelectableRecordCheckboxes()
            .each((index, input) => {
                $(input).closest('.o_data_row').toggleClass('o_data_row_selected', input.checked);
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Prevent from opening the record on click when in selection mode.
     *
     * @override
     */
    _onRowClicked(ev) {
        if (this.selection.length) {
            ev.preventDefault();
            return;
        }
        this._super(...arguments);
    },

    /**
     * Following @see _onTouchStartSelectionMode, we cancel the long-touch if it was shorter
     * than @see LONG_TOUCH_THRESHOLD.
     *
     * @private
     */
    _onTouchEndSelectionMode() {
        const elapsedTime = Date.now() - this.touchStartMs;
        if (elapsedTime < this.LONG_TOUCH_THRESHOLD) {
            this._resetLongTouchTimer();
        }
    },

    /**
     * Following @see _onTouchStartSelectionMode, we cancel the long-touch.
     *
     * @private
     */
    _onTouchMoveSelectionMode() {
        this._resetLongTouchTimer();
    },

    /**
     * We simulate a long-touch on a row by delaying (@see LONG_TOUCH_THRESHOLD)
     * the actual handler and potentially cancelling it if the user moves or end
     * its 'touch' before the timer's end.
     *
     * @private
     * @param ev
     */
    _onTouchStartSelectionMode(ev) {
        if (this.selection.length) {
            // in selection mode, only selection is allowed.
            ev.preventDefault();
            $(ev.currentTarget).find('.o_list_record_selector').click();
            return;
        }
        this.touchStartMs = Date.now();
        if (this.longTouchTimer === null) {
            this.longTouchTimer = setTimeout(() => {
                $(ev.currentTarget).find('.o_list_record_selector').click();
                this._resetLongTouchTimer();
            }, this.LONG_TOUCH_THRESHOLD);
        }
    },

});
});
