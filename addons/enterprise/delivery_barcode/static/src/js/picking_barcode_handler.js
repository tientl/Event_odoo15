odoo.define('delivery_barcode.PickingBarcodeHandler', function (require) {
"use strict";

var StockPickingBarcodeHandler = require('stock_barcode.PickingBarcodeHandler');


StockPickingBarcodeHandler.include({
    pre_onchange_hook: function(barcode) {
        var self = this;
        return this.try_put_in_pack_delivery(barcode).then(function(){
            return Promise.resolve(false);
        },function(){
            return self._super.apply(self, arguments);
        });
    },

    try_put_in_pack_delivery: function (barcode) {
        var self = this;
        var picking_id = this.view.datarecord.id;
        var package_type_field = this.form_view.fields.delivery_package_type_ids;
        var package_type_records = package_type_field.viewmanager.active_view.controller.records.records;
        var pack = _.find(package_type_records, function(pck){return pck.get('barcode') === barcode});
        if (pack) {
            var pack_id = pack.attributes.id;
            return self.form_view.save()
                .then(function() {
                    return self.picking_model.call('action_put_in_pack',[[picking_id]]);
                })
                .then(function(put_in_pack_action) {
                    put_in_pack_action.context = _.extend(
                        {'default_delivery_package_type_id': pack_id, 'active_id': picking_id},
                        put_in_pack_action.context || {}
                    );
                    self.open_wizard(put_in_pack_action);
                    return Promise.resolve();
                });
        } else {
            return Promise.reject();
        }
    }
});


});
