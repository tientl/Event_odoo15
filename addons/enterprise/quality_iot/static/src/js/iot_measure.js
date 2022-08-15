odoo.define('quality_iot.iot_measure', function (require) {
"use strict";

var registry = require('web.field_registry');
var iot_widgets = require('iot.widgets');

var IoTMeasureRealTimeValue = iot_widgets.IoTRealTimeValue.extend({
    /**
     * @private
     */
    _getDeviceInfo: function() {
        if (this.recordData.test_type === 'measure') {
            return this._super();
        }
    },
});

registry.add('iot_measure', IoTMeasureRealTimeValue);

return IoTMeasureRealTimeValue;
});
