odoo.define('barcodes_mobile.BarcodeEvents', function (require) {
"use strict";

var BarcodeEvents = require('barcodes.BarcodeEvents');

const mobile = require('web_mobile.core');


if (!mobile.methods.closeVirtualKeyboard) {
    return;
}
var barcodeEvents = BarcodeEvents.BarcodeEvents;

// Each time the input has the focus, the mobile virtual keyboard will
// be opened but we don't control exactly when.
// In some are cases, the opening is slowly deferred. The keyboard
// will appear anyway and closeVirtualKeyboard will be executed too early.
barcodeEvents.$barcodeInput.on('focus', function () {
    setTimeout(mobile.methods.closeVirtualKeyboard, 0);
});
});
