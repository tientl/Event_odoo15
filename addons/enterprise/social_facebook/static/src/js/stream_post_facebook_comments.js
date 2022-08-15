odoo.define('social.social_facebook_post_kanban_comments', function (require) {

var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

var StreamPostComments = require('@social/js/stream_post_comments')[Symbol.for("default")];

var StreamPostFacebookComments = StreamPostComments.extend({
    init: function (parent, options) {
        this.options = _.defaults(options || {}, {
            title: _t('Facebook Comments'),
            commentName: _t('comment/reply')
        });

        this.commentsCount = options.commentsCount;
        this.accountId = options.accountId;
        this.totalLoadedComments = options.comments.length;
        this.nextRecordsToken = options.nextRecordsToken;
        this.summary = options.summary;
        this.mediaType = 'facebook';

        this._super.apply(this, arguments);
    },

    willStart: function () {
        var self = this;

        var superDef = this._super.apply(this, arguments);
        var pageInfoDef = this._rpc({
            model: 'social.account',
            method: 'read',
            args: [this.accountId, ['name', 'facebook_account_id']],
        }).then(function (result) {
            self.accountName = result[0].name;
            self.pageFacebookId = result[0].facebook_account_id;

            return Promise.resolve();
        });

        return Promise.all([superDef, pageInfoDef]);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getAuthorPictureSrc: function (comment) {
        if (comment) {
            if (comment.from && comment.from.picture) {
                return comment.from.picture.data.url;
            } else {
                // unknown author
                return "/web/static/img/user_placeholder.jpg";
            }
        } else {
            return _.str.sprintf("https://graph.facebook.com/v10.0/%s/picture?height=48&width=48", this.pageFacebookId);
        }
    },

    getCommentLink: function (comment) {
        return _.str.sprintf("https://www.facebook.com/%s", comment.id);
    },

    getAuthorLink: function (comment) {
        if (comment.from.id) {
            return _.str.sprintf("/social_facebook/redirect_to_profile/%s/%s?name=%s", this.accountId, comment.from.id, encodeURI(comment.from.name));
        } else {
            // unknown author
            return "#";
        }
    },

    isCommentDeletable: function (comment) {
        return comment.from.id === this.pageFacebookId;
    },

    isCommentEditable: function (comment) {
        return comment.from.id === this.pageFacebookId;
    },

    getAddCommentEndpoint: function () {
        return '/social_facebook/comment';
    },

    getDeleteCommentEndpoint: function () {
        return '/social_facebook/delete_comment';
    },

    showMoreComments: function (result) {
        return this.totalLoadedComments < this.summary.total_count;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onLikeComment: function (ev) {
        ev.preventDefault();

        var $target = $(ev.currentTarget);
        var userLikes = $target.data('userLikes');
        this._rpc({
            route: '/social_facebook/like_comment',
            params: {
                stream_post_id: this.postId,
                comment_id: $target.data('commentId'),
                like: !userLikes
            }
        });

        $target.toggleClass('o_social_comment_user_likes');
        this._updateLikesCount($target);
    },

    _onLoadMoreComments: function (ev) {
        var self = this;
        ev.preventDefault();

        this._rpc({
            route: '/social_facebook/get_comments',
            params: {
                stream_post_id: this.postId,
                next_records_token: this.nextRecordsToken,
                comments_count: this.commentsCount
            },
        }).then(function (result) {
            var $moreComments = $(QWeb.render("social.StreamPostCommentsWrapper", {
                widget: self,
                comments: result.comments
            }));
            self.$('.o_social_comments_messages').append($moreComments);

            self.totalLoadedComments += result.comments.length;
            if (self.totalLoadedComments >= self.summary.total_count) {
                self.$('.o_social_load_more_comments').hide();
            }

            self.nextRecordsToken = result.nextRecordsToken;
        });
    }
});

return StreamPostFacebookComments;

});
