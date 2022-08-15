odoo.define('social.social_instagram_post_comments', function (require) {

var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

var StreamPostComments = require('@social/js/stream_post_comments')[Symbol.for("default")];

var StreamPostInstagramComments = StreamPostComments.extend({
    init: function (parent, options) {
        this.options = _.defaults(options || {}, {
            title: _t('Instagram Comments'),
            commentName: _t('comment/reply')
        });

        this.commentsCount = options.commentsCount;
        this.accountId = options.accountId;
        this.totalLoadedComments = options.comments.length;
        this.nextRecordsToken = options.nextRecordsToken;
        this.mediaType = 'instagram';

        this._super.apply(this, arguments);
    },

    willStart: function () {
        var self = this;
        var superDef = this._super.apply(this, arguments);

        var pageInfoDef = this._rpc({
            model: 'social.account',
            method: 'search_read',
            fields: [
                'name',
                'instagram_account_id'
            ],
            domain: [['id', '=', this.accountId]]
        }).then(function (result) {
            self.accountName = result[0].name;
            self.instagramAccountId = result[0].instagram_account_id;

            return Promise.resolve();
        });

        return Promise.all([superDef, pageInfoDef]);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * We can only compute the author picture if it comes from the user himself
     * (using his facebook ID).
     *
     * Instagram does not provide an endpoint to fetch an author's profile image.
     *
     * @param {Object} comment
     */
    getAuthorPictureSrc: function (comment) {
        if (!comment) {
            return _.str.sprintf(
                'https://graph.facebook.com/v10.0/%s/picture',
                this.originalPost.instagramFacebookAuthorId);
        } else {
            return '/social_instagram/static/src/img/instagram_user.png';
        }
    },

    getAuthorLink: function (comment) {
        return "https://www.instagram.com/" + encodeURI(comment.from.name);
    },

    getCommentLink: function (comment) {
        return this.originalPost.postLink;
    },

    getLikesClass: function () {
        return "fa-heart";
    },

    isCommentEditable: function (comment) {
        return false;
    },

    isCommentDeletable: function () {
        return true;
    },

    canAddImage: function () {
        return false;
    },

    getAddCommentEndpoint: function () {
        return '/social_instagram/comment';
    },

    getDeleteCommentEndpoint: function () {
        return '/social_instagram/delete_comment';
    },

    isCommentLikable: function () {
        return false;
    },

    showMoreComments: function () {
        return this.nextRecordsToken != null;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onLikeComment: function (ev) {
        // empty on purpose - not supported by Instagram as we cannot know if the post
        // is already liked or not
        ev.preventDefault();
    },

    _onLoadMoreComments: function (ev) {
        var self = this;
        ev.preventDefault();

        this._rpc({
            route: '/social_instagram/get_comments',
            params: {
                stream_post_id: this.postId,
                next_records_token: this.nextRecordsToken,
                comments_count: this.commentsCount
            }
        }).then(function (result) {
            var $moreComments = $(QWeb.render("social.StreamPostCommentsWrapper", {
                widget: self,
                comments: result.comments
            }));
            self.$('.o_social_comments_messages').append($moreComments);

            self.nextRecordsToken = result.nextRecordsToken;
            if (!self.nextRecordsToken) {
                self.$('.o_social_load_more_comments').hide();
            }

            self.nextRecordsToken = result.nextRecordsToken;
        });
    }
});

return StreamPostInstagramComments;

});
