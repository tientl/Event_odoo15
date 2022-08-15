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
        'click input[name="fsm_quantity"]': '_editQuantity',
        'blur input[name="fsm_quantity"]': '_onBlur',
        'keydown input[name="fsm_quantity"]': '_onKeyDown'
    }),

    /**
     * @override
     */
    init: function (parent, name, record, options) {
        options.mode = 'edit';
        this._super.apply(this, arguments);
        this.isReadonly = !!record.context.hide_qty_buttons;
        this.mode = 'readonly';
        this.nodeOptions.type = 'number';
        this.muteRemoveQuantityButton = false;
        this.exitEditMode = false; // use to know when the user exits the edit mode.
    },

    /**
     * @override
     */
    start: function () {
        this.$buttons = this.$('button');
        this._prepareInput(this.$('input[name="fsm_quantity"]'));
        this.$el.on('click', (e) => this._onWidgetClick(e));
        this._super.apply(this, arguments);
    },

    /**
     * @override
     * Add the invalid class on a field
     */
    setInvalidClass: function () {
        this.$input.addClass('o_field_invalid');
        this.$input.attr('aria-invalid', 'true');
    },

    /**
     * @override
     * Remove the invalid class on a field
     */
    removeInvalidClass: function () {
        this.$input.removeClass('o_field_invalid');
        this.$input.removeAttr('aria-invalid');
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
    _addQuantity: function (e) {
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
            // When the user double clicks on the input, he cannot select the text to edit it
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
     *
     * @param {KeyboardEvent} e
     */
    _onKeyDown: function (e) {
        e.stopPropagation();
        if (e.keyCode === $.ui.keyCode.ENTER) {
            e.preventDefault();
            this.$input.focus().blur();
        }
    },

    /**
     * onInput is called when the user manually edits the quantity of the current product.
     *
     * @override
     */
    _onInput: function () {
        this.$input.toggleClass('small', this.$input.val().length > this._maxLengthBeforeSmall);
        this._super.apply(this, arguments);
        try {
            this._parseValue(this.$input.val());
            this.removeInvalidClass();
        } catch (e) {
            this.setInvalidClass();
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
     * Maximum length of value before the small class is applied to the input
     */
    _maxLengthBeforeSmall: 5,

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
                this.$input
                    .removeClass('o_input')
                    .toggleClass('text-muted', this.value === 0);
                if (this._getValue() === '') this.$input.val(0);
                this._isDirty = false;
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
     * @override
     */
    _render: function () {
        // We force to readonly because we manage the edit mode only in this widget and not with the kanban view.
        this.mode = 'readonly';
        this.exitEditMode = false;
        this.muteRemoveQuantityButton = this.record.data.hasOwnProperty('quantity_decreasable') && !this.record.data.quantity_decreasable;
        this._super.apply(this, arguments);
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
        this._prepareInput(this.$input);
        this.$input
            .removeAttr('readonly')
            .removeClass('text-muted')
            .toggleClass('small', this.value.toString().length > this._maxLengthBeforeSmall)
            .val(this.value === 0 ? "" : this.value)
            .focus()
            .select();
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        this._renderButtons();
        this.$input
            .attr('readonly', 'readonly')
            .removeClass('o_input')
            .toggleClass('small', this.value.toString().length > this._maxLengthBeforeSmall)
            .toggleClass('text-muted', this.value === 0)
            .val(this.value);
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
