/** @odoo-module **/

import {
    registerClassPatchModel,
    registerFieldPatchModel,
} from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerClassPatchModel('mail.activity', 'voip/static/src/models/activity/activity.js', {
    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('mobile' in data) {
            data2.mobile = data.mobile;
        }
        if ('phone' in data) {
            data2.phone = data.phone;
        }
        return data2;
    },
});

registerFieldPatchModel('mail.activity', 'voip/static/src/models/activity/activity.js', {
    /**
     * String to store the mobile number in a call activity.
     */
    mobile: attr(),
    /**
     * String to store the phone number in a call activity.
     */
    phone: attr(),
});
