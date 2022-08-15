/** @odoo-module **/

import FieldHtml from 'web_editor.field.html';
import fieldRegistry from 'web.field_registry';
import MailEmojisMixin from '@mail/js/emojis_mixin';
import SocialPostFormatterMixin from 'social.post_formatter_mixin';

/**
 * Simple FieldHtml extension that will just wrap the emojis correctly.
 * See 'MailEmojisMixin' documentation for more information.
 */
var FieldPostPreview = FieldHtml.extend(MailEmojisMixin, SocialPostFormatterMixin, {
    _textToHtml: function (text) {
        var html = this._super.apply(this, arguments);
        var $html = $(html);
        var $previewMessage = $html.find('.o_social_preview_message');
        $previewMessage.html(this._formatPost($previewMessage.text().trim()));

        return $html[0].outerHTML;
    }
});

fieldRegistry.add('social_post_preview', FieldPostPreview);

export default FieldPostPreview;
