odoo.define('social_youtube.social_stream_post_kanban_controller', function (require) {
"use strict";

var StreamPostKanbanController = require('social.social_stream_post_kanban_controller');
var StreamPostYoutubeComments = require('social.StreamPostYoutubeComments');

StreamPostKanbanController.include({
    events: _.extend({}, StreamPostKanbanController.prototype.events, {
        'click .o_social_youtube_comments': '_onYoutubeCommentsClick',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onYoutubeCommentsClick: function (ev) {
        var self = this;
        var $target = $(ev.currentTarget);

        var postId = $target.data('postId');
        this._rpc({
            route: '/social_youtube/get_comments',
            params: {
                stream_post_id: postId,
                next_page_token: this.nextPageToken
            }
        }).then(function (result) {
            new StreamPostYoutubeComments(
                self,
                {
                    postId: postId,
                    accountId: $target.data('youtubeAccountId'),
                    originalPost: $target.data(),
                    comments: result.comments,
                    nextPageToken: result.nextPageToken
                }
            ).open();
        });
    },


    /**
     * The super implementation of this method allows to open the comments modal
     * when we click anywhere but on a link or an image (since images open the carousel).
     *
     * However, we also want to open the comments if the user clicks on the Youtube thumbnail.
     * Hence this small override.
     *
     * @param {MouseEvent} ev
     */
    _onClickRecord: function (ev) {
        var $target = $(ev.target);
        if ($target.closest('.o_social_youtube_thumbnail').length !== 0) {
            ev.preventDefault();
            $(ev.currentTarget).find('.o_social_comments').click();
        } else {
            this._super(...arguments);
        }
    },
});

return StreamPostKanbanController;

});
