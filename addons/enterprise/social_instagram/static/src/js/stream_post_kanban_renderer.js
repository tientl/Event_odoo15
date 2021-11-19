odoo.define('social.social_instagram_stream_post_kanban_renderer', function (require) {
"use strict";

var StreamPostKanbanRenderer = require('social.social_stream_post_kanban_renderer');
StreamPostKanbanRenderer.include({
    /**
     * Instagram does not provide any information for stories.
     *
     * @param {Object} socialAccount  social.account search_read data
     * @private
     * @override
     */
    _hasStories: function (socialAccount) {
        return this._super.apply(this, arguments) && socialAccount.media_type !== 'instagram';
    }
});

return StreamPostKanbanRenderer;

});
