odoo.define('quality_iot.iot_picture', function (require) {
"use strict";

var registry = require('web.field_registry');
var TabletImage = require('quality.tablet_image_field').TabletImage;
var iot_widgets = require('iot.widgets');
var core = require('web.core');
var _t = core._t;

var TabletImageIoT = TabletImage.extend(iot_widgets.IoTValueFieldMixin, {
    events: _.extend({}, TabletImage.prototype.events, {
        'click .o_input_file': '_onButtonClick',
    }),

    /**
     * @private
     */
    _getDeviceInfo: function() {
        if (this.recordData.test_type === 'picture') {
            return iot_widgets.IoTValueFieldMixin._getDeviceInfo.apply(this);
        }
    },

    _onButtonClick: function (ev) {
        var self = this;
        ev.stopImmediatePropagation();
        if (this.iot_device) {
            ev.preventDefault();
            this.displayNotification({ message: _t('Capture image...') });
            this.iot_device.action({})
                .then(function(data) {
                    self._onIoTActionResult(data);
                })
                .guardedCatch(self._onIoTActionFail.bind(self));
        }
    },
    /**
     * When the camera change state (after a action that call to take a picture) this function render the picture to the right owner
     *
     * @param {Object} data.owner
     * @param {Object} data.session_id
     * @param {Object} data.message
     * @param {Object} data.image in base64
     */
    _onValueChange: function (data){
        if (data.owner && data.owner === data.session_id) {
            this.displayNotification({ title: data.message });
            if (data.image){
                this._setValue(data.image);
            }
        }
    },
});

registry.add('iot_picture', TabletImageIoT);

return TabletImageIoT;
});
