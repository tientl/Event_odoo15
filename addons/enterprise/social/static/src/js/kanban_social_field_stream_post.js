/** @odoo-module **/

import FieldRegistry from 'web.field_registry';
import { FieldText } from 'web.basic_fields';
import MailEmojisMixin from '@mail/js/emojis_mixin';
import SocialStreamPostFormatterMixin from 'social.post_formatter_mixin';

var SocialKanbanMessageWrapper = FieldText.extend(MailEmojisMixin, SocialStreamPostFormatterMixin, {
    /**
     * Overridden to wrap emojis and apply special stream post formatting
     *
     * @override
     */
    _render: function () {
        if (this.value) {
            this.$el.html(this._formatPost(this.value));
        }
    },
});

FieldRegistry.add('social_kanban_field_stream_post', SocialKanbanMessageWrapper);

export default SocialKanbanMessageWrapper;
