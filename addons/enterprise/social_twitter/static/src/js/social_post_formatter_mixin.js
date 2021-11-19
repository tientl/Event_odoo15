odoo.define('social_twitter.post_formatter_mixin', function (require) {
"use strict";

var SocialPostFormatterMixin = require('social.post_formatter_mixin');
var _superFormatPost = SocialPostFormatterMixin._formatPost;

/*
 * Add Twitter @tag and #hashtag support.
 * Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
 * on the media website
 */
SocialPostFormatterMixin._formatPost = function (formattedValue) {
    formattedValue = _superFormatPost.apply(this, arguments);
    var mediaType = SocialPostFormatterMixin._getMediaType.apply(this, arguments);
    if (mediaType === 'twitter') {
        formattedValue = formattedValue.replace(SocialPostFormatterMixin.REGEX_HASHTAG,
                `<a href='https://twitter.com/hashtag/$1?src=hash' target='_blank'>#$1</a>`);
        formattedValue = formattedValue.replace(SocialPostFormatterMixin.REGEX_AT,
                `<a href='https://twitter.com/$1' target='_blank'>@$1</a>`);
    }
    return formattedValue;
};

});
