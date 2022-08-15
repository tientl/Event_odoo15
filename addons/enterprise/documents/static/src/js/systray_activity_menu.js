/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';

import session from 'web.session';

ActivityMenu.include({
    events: _.extend({}, ActivityMenu.prototype.events, {
        'click .o_sys_documents_request': '_onRequestDocument',
    }),

    /**
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        this.hasDocumentUserGroup = await session.user_has_group('documents.group_documents_user');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
   _onRequestDocument: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.$('.dropdown-toggle').dropdown('toggle');
        this.do_action('documents.action_request_form');
    },
});
