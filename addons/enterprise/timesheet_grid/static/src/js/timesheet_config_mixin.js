odoo.define('timesheet_grid.TimesheetConfigQRCodeMixin', function (require) {
    "use strict";

    const TimesheetConfigQRCodeMixin = {

        /**
         * Bind the event for play store icons
         * @private
         */
        _bindPlayStoreIcon() {
            const playStore = this.el.querySelector('.o_config_play_store');
            const appStore = this.el.querySelector('.o_config_app_store');

            if (playStore) {
                playStore.onclick = this._onClickAppStoreIcon.bind(this);
            }
            if (appStore) {
                appStore.onclick = this._onClickAppStoreIcon.bind(this);
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickAppStoreIcon(ev) {
            ev.preventDefault();
            const googleUrl = "https://play.google.com/store/apps/details?id=com.odoo.OdooTimesheets";
            const appleUrl = "https://apps.apple.com/be/app/awesome-timesheet/id1078657549";
            const url = ev.target.classList.contains("o_config_play_store") ? googleUrl : appleUrl;

            if (!this.env.device.isMobile) {
                const actionDesktop = {
                    name: this.env._t('Download our App'),
                    type: 'ir.actions.client',
                    tag: 'timesheet_qr_code_modal',
                    target: 'new',
                };
                this.trigger('do-action', {action: Object.assign(actionDesktop, {params: {'url': url}})});
            } else {
                this.trigger('do-action', {action: {type: 'ir.actions.act_url', url: url}});
            }
        },

    };

    return TimesheetConfigQRCodeMixin;
});
