odoo.define('industry_fsm_sale.ProductKanbanView', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const KanbanModel = require('industry_fsm_sale.ProductKanbanModel');
const KanbanController = require('industry_fsm_sale.ProductKanbanController');
const KanbanRenderer = require('industry_fsm_sale.ProductKanbanRenderer');
const viewRegistry = require('web.view_registry');

const ProductKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: KanbanModel,
        Controller: KanbanController,
        Renderer: KanbanRenderer,
    }),
});

viewRegistry.add('fsm_product_kanban', ProductKanbanView);

return ProductKanbanView;

});
