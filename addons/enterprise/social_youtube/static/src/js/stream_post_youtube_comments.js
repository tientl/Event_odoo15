odoo.define('social.StreamPostYoutubeComments', function (require) {

var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

var StreamPostComments = require('@social/js/stream_post_comments')[Symbol.for("default")];

var StreamPostYoutubeComments = StreamPostComments.extend({
    init: function (parent, options) {
        this.options = _.defaults(options || {}, {
            title: _t('YouTube Comments'),
            commentName: _t('comment/reply')
        });

        this.accountId = options.accountId;
        this.nextPageToken = options.nextPageToken;
        this.mediaType = 'youtube';

        this._super.apply(this, arguments);
    },

    willStart: function () {
        var self = this;

        var superDef = this._super.apply(this, arguments);
        var pageInfoDef = this._rpc({
            model: 'social.account',
            method: 'read',
            args: [this.accountId, ['name', 'youtube_channel_id']],
        }).then(function (result) {
            self.accountName = result[0].name;
            self.youtubeChannelId = result[0].youtube_channel_id;

            return Promise.resolve();
        });

        return Promise.all([superDef, pageInfoDef]);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    canAddImage: function () {
        return false;
    },

    getAddCommentEndpoint: function () {
        return '/social_youtube/comment';
    },

    getAuthorLink: function (comment) {
        return comment && comment.from ? comment.from.author_channel_url : null;
    },

    getAuthorPictureSrc: function (comment) {
        if (comment) {
            return comment.from.author_image_url;
        } else {
            return _.str.sprintf('/web/image/social.account/%s/image/48x48', this.accountId);
        }
    },

    /**
     * This is not *officially* supported by Google.
     * I retro-engineered the links they send by email to redirect the user to a specific comment
     * and this is a crafted URL that seems to work.
     * It sends the user to the video with the specific comment marked as "Highlighted Comment".
     *
     * Worst case scenario you just land on the video, which is fine too.
     *
     * @param {Object} comment
     */
    getCommentLink: function (comment) {
        return `https://www.youtube.com/watch?v=${this.originalPost.youtubeVideoId}&lc=${comment.id}&feature=em-comments`
    },

    getDeleteCommentEndpoint: function () {
        return '/social_youtube/delete_comment';
    },

    getLikesClass: function () {
        return "fa-thumbs-up";
    },

    isCommentDeletable: function (comment) {
        return true;
    },

    isCommentEditable: function (comment) {
        return comment && comment.from && comment.from.id === this.youtubeChannelId;
    },

    isCommentLikable: function () {
        return false;
    },

    showMoreComments: function () {
        return this.nextPageToken;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onLoadMoreComments: function (ev) {
        var self = this;
        ev.preventDefault();

        this._rpc({
            model: 'social.stream.post',
            method: 'get_youtube_comments',
            args: [[this.postId], this.nextPageToken]
        }).then(function (result) {
            var $moreComments = $(QWeb.render("social.StreamPostCommentsWrapper", {
                widget: self,
                comments: result.comments
            }));
            self.$('.o_social_comments_messages').append($moreComments);

            if (!result.nextPageToken) {
                self.$('.o_social_load_more_comments').hide();
            } else {
                self.nextPageToken = result.nextPageToken;
            }
        });
    },
});

return StreamPostYoutubeComments;

});
