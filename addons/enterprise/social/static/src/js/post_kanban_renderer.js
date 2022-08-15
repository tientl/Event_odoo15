odoo.define('social.social_post_kanban_renderer', function (require) {
"use strict";

const KanbanRenderer = require('web.KanbanRenderer');
const SocialStreamPostFormatterMixin = require('social.post_formatter_mixin');

const SocialPostKanbanRenderer = KanbanRenderer.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the message and handle emojis as well as link anchors styling.
     *
     * @override
     * @private
     * @returns {Promise}
     */
    _render: function () {
        const self = this;
        return this._super.apply(this, arguments).then(function () {
            const messages = self.$el.find('.o_social_stream_post_message_text');

            for (const message of messages) {
                // Replace text links with anchor tags and add emojis support
                // https://odoo.com => <a href="https://odoo.com">https://odoo.com</a>
                const body = SocialStreamPostFormatterMixin._formatPost(message.innerText);
                message.innerHTML = body;
            }
        });
    },
});

return SocialPostKanbanRenderer;

});
