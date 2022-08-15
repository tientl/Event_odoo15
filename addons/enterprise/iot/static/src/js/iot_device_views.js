odoo.define('iot.iot_device_views', function (require) {
"use strict";

var IoTDeviceControllers = require('iot.iot_device_controllers');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var IoTDeviceFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: IoTDeviceControllers.IoTDeviceFormController,
    }),
});

viewRegistry.add('iot_device_form', IoTDeviceFormView);

return {
    IoTDeviceFormView: IoTDeviceFormView,
};

});
