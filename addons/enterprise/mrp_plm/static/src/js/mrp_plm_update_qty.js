odoo.define('mrp_plm.update_qty', function (require) {
    "use strict";
    
const BasicFields = require('web.basic_fields');
const FieldFloat = BasicFields.FieldFloat;
const fieldRegistry = require('web.field_registry');

const MrpPlmUpdateQty = FieldFloat.extend({

    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        if (this.value > 0){
            this.$el.text(this._formatValue(this.value));
            const $sign = $('<span>+</span>');
            this.setElement(this.$el.wrap($sign).parent());
        } else {
            this._super.apply(this);
        }
    },

});

fieldRegistry.add('plm_upd_qty', MrpPlmUpdateQty);

return {
    MrpPlmUpdateQty: MrpPlmUpdateQty,
};

});
