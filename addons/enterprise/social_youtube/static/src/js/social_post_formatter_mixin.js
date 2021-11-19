odoo.define('social_youtube.post_formatter_mixin', function (require) {
"use strict";

var SocialPostFormatterMixin = require('social.post_formatter_mixin');
var _superFormatPost = SocialPostFormatterMixin._formatPost;

/*
* Add Youtube #hashtag support.
* Replace all occurrences of `#hashtag` by a HTML link to a search of the hashtag
* on the media website
*/
SocialPostFormatterMixin._formatPost = function (formattedValue) {
    formattedValue = _superFormatPost.apply(this, arguments);
    var mediaType = SocialPostFormatterMixin._getMediaType.apply(this, arguments);

    if (mediaType === 'youtube' || mediaType === 'youtube_preview') {
        formattedValue = formattedValue.replace(SocialPostFormatterMixin.REGEX_HASHTAG,
                `<a href='https://www.youtube.com/results?search_query=%23$1' target='_blank'>#$1</a>`);
    }
    return formattedValue;
};

});
