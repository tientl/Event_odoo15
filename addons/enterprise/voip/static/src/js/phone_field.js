odoo.define('voip.PhoneField', function (require) {
"use strict";

const basicFields = require('web.basic_fields');
const core = require('web.core');

const Phone = basicFields.FieldPhone;
const _t = core._t;

/**
 * Override of FieldPhone to use the DialingPanel to perform calls on clicks.
 */
Phone.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Uses the DialingPanel to perform the call.
     *
     * @private
     * @param {string} number
     */
    _call(number) {
        this.trigger_up('voip_call', {
            number,
            resId: this.res_id,
            resModel: this.model,
        });
    },

    async _hasPbxConfig() {

        const pbxConfiguration = await new Promise(resolve => {
            this.trigger_up('get_pbx_configuration', {
                callback: output => resolve(output.pbxConfiguration),
            });
        });

        return pbxConfiguration.mode !== 'prod' ||
        (
            pbxConfiguration.pbx_ip &&
            pbxConfiguration.wsServer &&
            pbxConfiguration.login &&
            pbxConfiguration.password
        );
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the phone number is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickLink(ev) {
        if (ev.target.matches("a")) {
            ev.stopImmediatePropagation();
        }
        if (this.mode !== 'readonly' || !window.RTCPeerConnection || !window.MediaStream || !navigator.mediaDevices) {
            return;
        }
        const canMadeVoipCall = await this._hasPbxConfig();
        if (canMadeVoipCall) {
            ev.preventDefault();
            this._call(this.value);
        }
    },
});

});
