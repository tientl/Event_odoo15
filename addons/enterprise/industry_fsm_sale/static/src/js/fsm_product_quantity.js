odoo.define('industry_fsm_sale.fsm_product_quantity', function (require) {
"use strict";

const { _t } = require('web.core');
const { FieldInteger } = require('web.basic_fields');
const field_registry = require('web.field_registry');


/**
 * FSMProductQty is a widget to  get the FSM Product Quantity in product kanban view
 */
const FSMProductQty = FieldInteger.extend({
    description: _t("FSM Product Quantity"),
    template: "FSMProductQuantity",
    events: _.extend({}, FieldInteger.prototype.events, {
        'click button[name="fsm_remove_quantity"]': '_removeQuantity',
        'click button[name="fsm_add_quantity"]': '_addQuantity',
        'click span[name="fsm_quantity"]': '_editQuantity',
        'blur span[name="fsm_quantity"]': '_onBlur',
        'keypress span[name="fsm_quantity"]': '_onKeyPress',
        'keydown span[name="fsm_quantity"]': '_onKeyDown',
    }),

    /**
     * @override
     */
    init: function (parent, name, record, options) {
        options.mode = 'edit';
        this._super.apply(this, arguments);
        this.isReadonly = !!record.context.hide_qty_buttons;
        this.mode = 'readonly';
        this.muteRemoveQuantityButton = false;
        this.exitEditMode = false; // use to know when the user exits the edit mode.
    },

    /**
     * @override
     */
    start: function () {
        this.$buttons = this.$('button');
        this.$fsmQuantityElement = this.$('span[name="fsm_quantity"]');
        this.$el.on('click', (e) => this._onWidgetClick(e));
        this._super.apply(this, arguments);
    },

    /**
     * @override
     * Add the invalid class on a field
     */
    setInvalidClass: function () {
        this.$fsmQuantityElement.addClass('o_field_invalid');
        this.$fsmQuantityElement.attr('aria-invalid', 'true');
    },

    /**
     * @override
     * Remove the invalid class on a field
     */
    removeInvalidClass: function () {
        this.$fsmQuantityElement.removeClass('o_field_invalid');
        this.$fsmQuantityElement.removeAttr('aria-invalid');
    },

    /**
     * Stop propagation to the widget parent.
     *
     * This method is useful when the fsm_remove_quantity button is disabled because it allows to prevent the click on kanban record.
     *
     * @param {MouseEvent} event
     */
    _onWidgetClick: function (event) {
        event.stopImmediatePropagation();
    },

    /**
     * Changes the quantity when the user clicks on a button (fsm_remove_quantity or fsm_add_quantity).
     *
     * @param {string} action is equal to either fsm_remove_quantity or fsm_add_quantity.
     */
    _changeQuantity: function (action) {
        this.trigger_up(action, {
            dataPointID: this.dataPointID,
        });
    },

    /**
     * Remove 1 unit to the product quantity when the user clicks on the '-' button.
     *
     * @param {MouseEvent} e
     */
    _removeQuantity: function (e) {
        e.stopPropagation();
        if (this.muteRemoveQuantityButton) {
            return;
        }

        if (this._isValid) {
            if (this._isDirty) {
                const value = Number(this._getValue());
                if (value > 0) {
                    this._setValue((value - 1).toString());
                }
            } else if (this.value > 0) {
                this._changeQuantity('fsm_remove_quantity');
            }
        }
    },

    /**
     * Add an unit to the product quantity when the user clicks on the '+' button.
     *
     * @param {MouseEvent} e
     */
    _addQuantity: async function (e) {
        e.stopPropagation();
        if (this._isValid) {
            if (this._isDirty) {
                const value = Number(this._getValue()) + 1;
                this._setValue(value.toString());
            } else {
                this._changeQuantity('fsm_add_quantity');
            }
        }
    },

    /**
     * Edit manually the product quantity.
     *
     * @param {Event} e
     */
    _editQuantity: function (e) {
        e.stopPropagation();
        if (this.mode == 'edit') {
            // When the user double clicks on the span, he cannot select the text to edit it
            // This condition is used to allow the double click on this element to select all into it.
            return;
        }

        if (!this.isReadonly) {
            this.exitEditMode = false;
            this.mode = 'edit';
            this._renderEdit();
        }
    },

    /**
     * Key Down Listener function.
     *
     * The main goal of this function is to validate the edition when the ENTER key is down.
     * The other goal is to know if the text edited is selected at least a part.
     * It is useful to not have more than 9 digits for the product quantity.
     *
     * @param {KeyboardEvent} e
     */
    _onKeyDown: function (e) {
        e.stopPropagation();
        if (e.keyCode === $.ui.keyCode.ENTER) {
            e.preventDefault();
            this._onBlur();
        } else if ((e.ctrlKey || e.metaKey) && ['c', 'v'].includes(e.key)) {
            // the "copy-paste" is not managed in this widget, because we cannot keep the number of digits at most 9 digits.
            e.preventDefault();
        }
    },

    /**
     * Key Press Listener function.
     *
     * This method prevents the user to enter a character different than a digit.
     *
     * @param {KeyboardEvent} e
     */
    _onKeyPress: function (e) {
        e.stopPropagation();
        if (e.key.length === 1) { // then it is a character
            if (!/[0-9]/.test(e.key) || (!this._getSelectedText() && e.target.innerText.length >= 9)) { // if the key is not a number then bypass it.
                e.preventDefault();
            }
        }
    },

    /**
     * onInput is called when the user manually edits the quantity of the current product.
     *
     * @override
     */
    _onInput: function () {
        this._formatFSMQuantity();
        if (this.hasOwnProperty('range')) {
            this._removeFSMQuantitySelection();
        }
        this.$input.val(this.$fsmQuantityElement.text());
        this._super.apply(this, arguments);
        if (!this._isValid) {
            this.setInvalidClass();
        } else {
            this.removeInvalidClass();
        }
    },

    /**
     * @override
     * @returns the value of the fsm_quantity for the current product, if the user is editing then we return the value entered in the input.
     */
    _getValue: function () {
        return this.$input ? this.$input.val() : this.value;
    },

    /**
     * _onBlur is called when the user stops and focus out the edition of the quantity for the current product.
     * @override
     */
    _onBlur: async function () {
        if (!this._isValid && this._isLastSetValue(this._getValue())) return; // nothing to do.
        try {
            await this._setValue(this._getValue(), this.options || { notifyChange: false });
            this.removeInvalidClass();
            if (this.mode !== 'readonly') {
                this.mode = 'readonly';
                this.exitEditMode = true;
                this._renderReadonly();
            }
        } catch (err) {
            // incase of UserError do not display the warning
            if (err.message.data.name !== 'odoo.exceptions.UserError') {
                this.displayNotification({ message: _t("The set quantity is invalid"), type: 'danger' });
            }
            this.setInvalidClass();
        }
    },

    /**
     * Format fsm quantity span based on the number of digits
     *
     * If the number of digits is greater than 5 then the font size is reduced.
     */
    _formatFSMQuantity: function () {
        this.$fsmQuantityElement.toggleClass('small', this.$fsmQuantityElement.text().length > 5);
    },

    /**
     * Get the selected text in the span when we are in edit mode.
     *
     * Source: https://stackoverflow.com/a/3545105
     */
    _getSelectedText: function () {
        if (window.getSelection) {
            return window.getSelection().toString();
        } else if (document.selection) {
            return document.selection.createRange().text;
        }
        return '';
    },

    /**
     * Select the FSM quantity when the user want to edit the quantity.
     *
     * If the value is 0 then we remove it, otherwise we select all content in the span.
     *
     * Source: https://stackoverflow.com/questions/12243898/how-to-select-all-text-in-contenteditable-div/12244703#12244703
     */
    _selectFSMQuantity: function () {
        if (this.value === 0) {
            return;
        }
        const element = this.$fsmQuantityElement[0];
        if (document.body.createTextRange) {
            this.range = document.body.createTextRange();
            this.range.moveToElementText(element);
            this.range.select();
        } else if (window.getSelection) {
            const selection = window.getSelection();
            this.range = document.createRange();
            this.range.selectNodeContents(element);
            selection.removeAllRanges();
            selection.addRange(this.range);
        }
    },

    _removeFSMQuantitySelection: function () {
        if (window.getSelection) {
            const selection = window.getSelection();
            if (selection.removeRange) {
                selection.removeRange(this.range);
            } else { // for Safari browser
                selection.removeAllRanges();
            }
        }
        delete this.range;
    },

    /**
     * @override
     */
    _render: function () {
        // We force to readonly because we manage the edit mode only in this widget and not with the kanban view.
        this.mode = 'readonly';
        this.exitEditMode = false;
        this.muteRemoveQuantityButton = this.record.data.hasOwnProperty('quantity_decreasable') && !this.record.data.quantity_decreasable;
        this._super.apply(this, arguments);
        this._formatFSMQuantity();
    },

    _renderButtons: function () {
        this.$buttons
            .toggleClass('btn-primary', this.value !== 0);
        this.$buttons
            .filter('button[name="fsm_add_quantity"]')
            .toggleClass('btn-light text-muted', this.value === 0);
        this.$buttons
            .filter('button[name="fsm_remove_quantity"]')
            .toggleClass('btn-light text-muted', this.value === 0 || this.muteRemoveQuantityButton)
            .attr('disabled', this.value === 0 || this.muteRemoveQuantityButton);
    },

    /**
     * @override
     */
    _renderEdit: function () {
        this._renderButtons();
        this._prepareInput(this.$fsmQuantityElement);
        this.$fsmQuantityElement
            .attr('contenteditable', true)
            .removeClass('text-muted')
            .text(this.value === 0 ? "" : this.value)
            .focus();
        this._selectFSMQuantity();
    },

    /**
     * @override
     */
    _renderReadonly: function () {
        this._renderButtons();
        this.$fsmQuantityElement
            .attr('contenteditable', false)
            .removeClass('o_input')
            .toggleClass('text-muted', this.value === 0)
            .text(this.value);
        this._isDirty = false;
    },
    destroy: function () {
        this.$el.off('click');
        this._super.apply(this, arguments);
    }
});

field_registry.add('fsm_product_quantity', FSMProductQty);

return { FSMProductQty };

});
