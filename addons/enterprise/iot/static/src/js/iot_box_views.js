odoo.define('iot.iot_box_views', function (require) {
"use strict";

var IoTBoxControllers = require('iot.iot_box_controllers');
var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var view_registry = require('web.view_registry');

var IoTBoxKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: IoTBoxControllers.IoTBoxKanbanController,
    }),
});

view_registry.add('box_kanban_view', IoTBoxKanbanView);

var IoTBoxListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: IoTBoxControllers.IoTBoxListController,
    }),
});

view_registry.add('box_list_view', IoTBoxListView);

});
