/** @odoo-module **/

import { registerInstancePatchModel } from "@mail/model/model_core";

registerInstancePatchModel("mail.chatter", "voip/static/src/models/chatter/chatter.js", {

    /**
     * @override
     */
    _created() {
        const res = this._super(...arguments);
        this._onReload = this._onReload.bind(this);
        this.env.bus.on("voip_reload_chatter", undefined, this._onReload);
        return res;
    },
    /**
     * @override
     */
    _willDelete() {
        this.env.bus.off("voip_reload_chatter", undefined, this._onReload);
        return this._super(...arguments);
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @private
     */
    _onReload() {
        if (!this.thread) {
            return;
        }
        this.thread.refreshActivities();
        this.thread.refresh();
    },
});
