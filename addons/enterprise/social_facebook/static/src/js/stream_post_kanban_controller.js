odoo.define('social_facebook.social_stream_post_kanban_controller', function (require) {
"use strict";

var StreamPostKanbanController = require('social.social_stream_post_kanban_controller');
var StreamPostFacebookComments = require('social.social_facebook_post_kanban_comments');

StreamPostKanbanController.include({
    events: _.extend({}, StreamPostKanbanController.prototype.events, {
        'click .o_social_facebook_comments': '_onFacebookCommentsClick',
        'click .o_social_facebook_likes': '_onFacebookPostLike',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onFacebookCommentsClick: function (ev) {
        var self = this;
        var $target = $(ev.currentTarget);

        var postId = $target.data('postId');
        this._rpc({
            route: '/social_facebook/get_comments',
            params: {
                stream_post_id: postId,
                comments_count: this.commentsCount
            }
        }).then(function (result) {
            new StreamPostFacebookComments(
                self,
                {
                    commentsCount: self.commentsCount,
                    postId: postId,
                    accountId: $target.data('facebookPageId'),
                    originalPost: $target.data(),
                    comments: result.comments,
                    summary: result.summary,
                    nextRecordsToken: result.nextRecordsToken
                }
            ).open();
        });
    },

    _onFacebookPostLike: function (ev) {
        ev.preventDefault();

        var $target = $(ev.currentTarget);
        var userLikes = $target.data('userLikes');
        this._rpc({
            route: '/social_facebook/like_post',
            params: {
                stream_post_id: $target.data('postId'),
                like: !userLikes
            }
        });

        this._updateLikesCount($target);
        $target.toggleClass('o_social_facebook_user_likes');
    },
});

return StreamPostKanbanController;

});
