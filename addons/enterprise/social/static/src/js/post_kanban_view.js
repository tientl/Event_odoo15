odoo.define('social.PostKanbanView', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var viewRegistry = require('web.view_registry');

// Add images carousel support
var PostKanbanController = require('social.social_post_kanban_controller');
var PostKanbanRenderer = require('social.social_post_kanban_renderer');

var PostKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: PostKanbanController,
        Renderer: PostKanbanRenderer,
    })
});

viewRegistry.add('social_post_kanban_view', PostKanbanView);

return PostKanbanView;

});
