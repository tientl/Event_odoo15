odoo.define('industry_fsm_sale.ProductKanbanRenderer', function (require) {
"use strict";

const KanbanRenderer = require('web.KanbanRenderer');
const KanbanRecord = require('industry_fsm_sale.ProductKanbanRecord');

return KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord
    }),
});

});
