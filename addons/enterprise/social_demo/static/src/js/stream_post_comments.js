odoo.define('social_demo.social_post_kanban_comments', function (require) {

var StreamPostFacebookComments = require('social.social_facebook_post_kanban_comments');
var StreamPostInstagramComments = require('social.social_instagram_post_comments');
var StreamPostLinkedInComments = require('social_linkedin.social_linkedin_post_kanban_comments');
var StreamPostTwitterComments = require('social.StreamPostTwitterComments');
var StreamPostLinkedinComments = require('social_linkedin.social_linkedin_post_kanban_comments');
var StreamPostYoutubeComments = require('social.StreamPostYoutubeComments');

/**
 * Return custom author image.
 * We use the 'profile_image_url_https' field to get a nicer demo effect.
 *
 * @param {string} comment
 */
var getDemoAuthorPictureSrc = function (comment) {
    if (comment) {
        return comment.from.profile_image_url_https;
    } else {
        return '/web/image/res.partner/2/image_128';
    }
};

StreamPostFacebookComments.include({
    getAuthorPictureSrc: function () {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }
});

StreamPostInstagramComments.include({
    getAuthorPictureSrc: function () {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }
});

StreamPostLinkedInComments.include({
    getAuthorPictureSrc: function () {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }
});

StreamPostTwitterComments.include({
    getAuthorPictureSrc: function () {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }
});

StreamPostLinkedinComments.include({
    getAuthorPictureSrc: function () {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }
});

StreamPostYoutubeComments.include({
    getAuthorPictureSrc: function () {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }
});

});
