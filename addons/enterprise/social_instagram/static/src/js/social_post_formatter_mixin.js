odoo.define('social_instagram.post_formatter_mixin', function (require) {
"use strict";

var SocialPostFormatterMixin = require('social.post_formatter_mixin');
var _superFormatPost = SocialPostFormatterMixin._formatPost;

/*
* Add Instagram #hashtag and @mention support.
* Replace all occurrences of `#hashtag` and `@mention` by a HTML link to a
* search of the hashtag/mention on the media website
*/
SocialPostFormatterMixin._formatPost = function (formattedValue) {
    formattedValue = _superFormatPost.apply(this, arguments);
    var mediaType = SocialPostFormatterMixin._getMediaType.apply(this, arguments);
    if (mediaType === 'instagram') {
        formattedValue = formattedValue.replace(SocialPostFormatterMixin.REGEX_AT,
            `<a href='https://www.instagram.com/$1' target='_blank'>@$1</a>`);
        formattedValue = formattedValue.replace(SocialPostFormatterMixin.REGEX_HASHTAG,
            `<a href='https://www.instagram.com/explore/tags/$1' target='_blank'>#$1</a>`);
    }
    return formattedValue;
};

});
