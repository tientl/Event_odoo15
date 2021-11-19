/** @odoo-module **/

import widgetRegistry from 'web.widget_registry';
import Widget from 'web.Widget';

const SetReservedQuantityButton = Widget.extend({
    template: 'stock_barcode.SetReservedQuantityButtonTemplate',
    events: { click: '_onClickButton' },

    /**
     * @override
     */
    init: function (parent, data, options) {
        this._super(...arguments);
        this.parent = parent;
        this.dataPointID = data.id;
        this.viewType = data.viewType;
        this.record = this.parent.state.data;
        this.quantityField = options.attrs.field_to_set;
        this.qty = this.record[options.attrs.quantity];
        const uom = this.record.product_uom_id;
        this.uom = uom && uom.data.display_name;
    },

    /**
     * @override
     */
    willStart: function () {
        this.display_uom = this.uom && this.getSession().user_has_group('uom.group_uom');
        return Promise.all([
            this._super(...arguments),
            this.display_uom,
        ]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickButton: function (ev) {
        ev.preventDefault();
        const { dataPointID, viewType } = this;
        const changes = { [this.quantityField]: this.qty };
        this.trigger_up('field_changed', { dataPointID, changes, viewType });
    },
});

widgetRegistry.add('set_reserved_qty_button', SetReservedQuantityButton);
export default SetReservedQuantityButton;
