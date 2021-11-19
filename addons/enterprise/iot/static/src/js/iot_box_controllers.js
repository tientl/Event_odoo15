odoo.define('iot.iot_box_controllers', function (require) {
"use strict";

var KanbanController = require('web.KanbanController');
var ListController = require('web.ListController');
const {_t} = require('web.core');

var IoTBoxControllerMixin = {
    /**
     * @override
     */
    renderButtons: function ($node) {
        this.$buttons = $('<button/>', {
            class: ['btn btn-primary o_iot_box_connect_button']
        }).text(_t('CONNECT'));

        if ($node) {
            this.$buttons.appendTo($node);
        }
    },
    _onConnectIoTBox: function () {
        this.do_action('iot.action_add_iot_box');
    },
};

var IoTBoxKanbanController = KanbanController.extend(IoTBoxControllerMixin, {
    events: _.extend({}, ListController.prototype.events, {
        'click .o_iot_box_connect_button': '_onConnectIoTBox',
    }),
});

var IoTBoxListController = KanbanController.extend(IoTBoxControllerMixin, {
    events: _.extend({}, ListController.prototype.events, {
        'click .o_iot_box_connect_button': '_onConnectIoTBox',
    }),
});

return {
    IoTBoxKanbanController: IoTBoxKanbanController,
    IoTBoxListController: IoTBoxListController,
};

});
