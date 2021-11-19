/** @odoo-module **/

import {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
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

registerInstancePatchModel('mail.activity', 'voip/static/src/models/activity/activity.js', {

    /**
     * @override
     */
    _created() {
        const res = this._super(...arguments);
        this._onReloadChatter = this._onReloadChatter.bind(this);
        this.env.bus.on('voip_reload_chatter', undefined, this._onReloadChatter);
        return res;
    },
    /**
     * @override
     */
    _willDelete() {
        this.env.bus.off('voip_reload_chatter', undefined, this._onReloadChatter);
        return this._super(...arguments);
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @private
     */
    _onReloadChatter() {
        if (!this.thread) {
            return;
        }
        this.thread.refreshActivities();
        this.thread.refresh();
    },
});
