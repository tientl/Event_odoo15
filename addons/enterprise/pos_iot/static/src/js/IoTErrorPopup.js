odoo.define('pos_iot.IoTErrorPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class IoTErrorPopup extends AbstractAwaitablePopup {
        mounted() {
            this.playSound('error');
        }
    }
    IoTErrorPopup.template = 'IoTErrorPopup';
    IoTErrorPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error',
    };

    Registries.Component.add(IoTErrorPopup);

    return IoTErrorPopup;
});
