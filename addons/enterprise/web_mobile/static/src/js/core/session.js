odoo.define('web_mobile.Session', function (require) {
"use strict";

const core = require('web.core');
const Session = require('web.Session');
const utils = require('web.utils');

const mobile = require('web_mobile.core');

/*
    Android webview not supporting post download and odoo is using post method to download
    so here override get_file of session and passed all data to native mobile downloader
    ISSUE: https://code.google.com/p/android/issues/detail?id=1780
*/

Session.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    get_file: function (options) {
        if (mobile.methods.downloadFile) {
            if (core.csrf_token) {
                options.csrf_token = core.csrf_token;
            }
            mobile.methods.downloadFile(options);
            // There is no need to wait downloadFile because we delegate this to
            // Download Manager Service where error handling will be handled correclty.
            // On our side, we do not want to block the UI and consider the request
            // as success.
            if (options.success) { options.success(); }
            if (options.complete) { options.complete(); }
            return true;
        } else {
            return this._super.apply(this, arguments);
        }
    },

    /**
     * Update the user's account details on the mobile app
     *
     * @returns {Promise}
     */
    async updateAccountOnMobileDevice() {
        if (!mobile.methods.updateAccount) {
            return;
        }
        const avatar = await this.fetchAvatar();
        const base64Avatar = await utils.getDataURLFromFile(avatar);
        return mobile.methods.updateAccount({
            avatar: base64Avatar.substring(base64Avatar.indexOf(',') + 1),
            name: this.name,
            username: this.username,
        });
    },

    /**
     * Fetch current user's avatar
     *
     * @returns {Promise<Blob>}
     */
    async fetchAvatar() {
        const url = this.url('/web/image', {
            model: 'res.users',
            field: 'image_medium',
            id: this.uid,
        });
        const response = await fetch(url);
        return response.blob();
    },
});

});
