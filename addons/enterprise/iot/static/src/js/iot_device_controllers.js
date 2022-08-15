odoo.define('iot.iot_device_controllers', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');
var DeviceProxy = require('iot.DeviceProxy');

var _t = core._t;

var IoTDeviceFormController = FormController.extend({
    /**
     * @override
     */
    saveRecord: function () {
        var self = this;
        var _super = this._super.bind(this);
        if (['keyboard', 'scanner'].indexOf(this.renderer.state.data.type) >= 0) {
            return this._updateKeyboardLayout().then(self._processResult.bind(self, _super));
        } else if (this.renderer.state.data.type === 'display') {
            return this._updateDisplayUrl().then(() => _super());
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     *
     */
    _processResult: function (saveRecord, data) {
        if (data.result === true) {
            saveRecord();
        } else {
            this.displayNotification({ title: _t('Connection to device failed'), message: _t('Check if the device is still connected'), type: 'danger' });
        }
    },
    /**
     * Send an action to the device to update the keyboard layout
     */
    _updateKeyboardLayout: function () {
        var keyboard_layout = this.renderer.state.data.keyboard_layout;
        var is_scanner = this.renderer.state.data.is_scanner;
        var iot_device = new DeviceProxy(this, { iot_ip: this.renderer.state.data.iot_ip, identifier: this.renderer.state.data.identifier });
        iot_device.action({'action': 'update_is_scanner', 'is_scanner': is_scanner});
        if (keyboard_layout) {
            return this._rpc({
                model: 'iot.keyboard.layout',
                method: 'read',
                args: [[keyboard_layout.res_id], ['layout', 'variant']],
            }).then(function (res) {
                return iot_device.action({'action': 'update_layout', 'layout': res[0].layout, 'variant': res[0].variant});
            });
        } else {
            return iot_device.action({'action': 'update_layout'});
        }
    },
    /**
     * Send an action to the device to update the screen url
     */
    _updateDisplayUrl: function () {
        var display_url = this.renderer.state.data.display_url;
        var iot_device = new DeviceProxy(this, { iot_ip: this.renderer.state.data.iot_ip, identifier: this.renderer.state.data.identifier });
        return iot_device.action({'action': 'update_url', 'url': display_url});
    },
});

return {
    IoTDeviceFormController: IoTDeviceFormController,
};

});
