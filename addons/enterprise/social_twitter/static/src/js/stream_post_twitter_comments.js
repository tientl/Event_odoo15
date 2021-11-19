odoo.define('social.StreamPostTwitterComments', function (require) {
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;

    var StreamPostComments = require('@social/js/stream_post_comments')[Symbol.for("default")];

    var StreamPostTwitterComments = StreamPostComments.extend({
        init: function (parent, options) {
            this.accountId = options.accountId;
            this.streamId = options.streamId;
            this.hasMoreComments = options.hasMoreComments;
            this.page = 1;
            this.allComments = options.allComments;
            this.commentsCount = options.commentsCount;
            this.comments = this.allComments.slice(0, this.commentsCount);
            this.mediaType = 'twitter';

            this.options = _.defaults(options || {}, {
                title: _t('Twitter Comments'),
                commentName: _t('tweet'),
                comments: this.comments
            });

            this._super.apply(this, arguments);
        },

        willStart: function () {
            var self = this;

            var superDef = this._super.apply(this, arguments);
            var pageInfoDef = this._rpc({
                model: 'social.account',
                method: 'read',
                args: [this.accountId, ['name', 'twitter_user_id']],
            }).then(function (result) {
                self.accountName = result[0].name;
                self.twitterUserId = result[0].twitter_user_id;

                return Promise.resolve();
            });

            return Promise.all([superDef, pageInfoDef]);
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        getAuthorPictureSrc: function (comment) {
            if (comment) {
                return comment.from.profile_image_url_https;
            } else {
                return _.str.sprintf('/web/image/social.account/%s/image/48x48', this.accountId);
            }
        },

        getLikesClass: function () {
            return "fa-heart";
        },

        getCommentLink: function (comment) {
            return _.str.sprintf("https://www.twitter.com/%s/statuses/%s", comment.from.id, comment.id);
        },

        getAuthorLink: function (comment) {
            return _.str.sprintf("https://twitter.com/intent/user?user_id=%s", comment.from.id);
        },

        isCommentDeletable: function (comment) {
            return comment.from.id === this.twitterUserId;
        },

        getAddCommentEndpoint: function () {
            return _.str.sprintf('/social_twitter/%s/comment', this.streamId);
        },

        getDeleteCommentEndpoint: function () {
            return '/social_twitter/delete_tweet';
        },

        isCommentEditable: function () {
            return false;
        },

        showMoreComments: function (result) {
            return this.page * this.commentsCount < this.allComments.length;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _onLikeComment: function (ev) {
            ev.preventDefault();

            var $target = $(ev.currentTarget);
            var userLikes = $target.data('userLikes');
            this._rpc({
                route: _.str.sprintf('social_twitter/%s/like_tweet', this.streamId),
                params: {
                    tweet_id: $target.data('commentId'),
                    like: !userLikes
                }
            });

            $target.toggleClass('o_social_comment_user_likes');
            this._updateLikesCount($target);
        },

        _onLoadMoreComments: function (ev) {
            var self = this;
            ev.preventDefault();

            this.page += 1;
            var start = (this.page - 1) * this.commentsCount;
            var end = start + this.commentsCount;
            var $moreComments = $(QWeb.render("social.StreamPostCommentsWrapper", {
                widget: this,
                comments: this.allComments.slice(start, end)
            }));
            self.$('.o_social_comments_messages').append($moreComments);

            if (end >= this.allComments.length) {
                self.$('.o_social_load_more_comments').hide();
            }
        },
    });

    return StreamPostTwitterComments;
});
