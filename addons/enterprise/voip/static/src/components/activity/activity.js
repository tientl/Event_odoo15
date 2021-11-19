/** @odoo-module **/

import { Activity } from '@mail/components/activity/activity';

import { patch } from 'web.utils';

patch(Activity.prototype, 'voip/static/src/components/activity/activity.js', {
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onClickVoipCallMobile(ev) {
        ev.preventDefault();
        this.trigger('voip_activity_call', {
            activityId: this.activity.id,
            number: this.activity.mobile,
        });
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickVoipCallPhone(ev) {
        ev.preventDefault();
        this.trigger('voip_activity_call', {
            activityId: this.activity.id,
            number: this.activity.phone,
        });
    },
});
