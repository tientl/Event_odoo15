/** @odoo-module **/

import { attr } from '@mail/model/model_field';
import { registerFieldPatchModel } from '@mail/model/model_core';

/**
 * This should be moved inside the mail_enterprise
 * mail_enterprise/static/src/models/chatter/chatter.js
 */
registerFieldPatchModel('mail.chatter', 'mail/static/src/models/chatter/chatter.js', {
    /**
     * The chatter is inside .form_sheet_bg class
     */
    isInFormSheetBg: attr({
        default: false,
    }),
});
