/** @odoo-module **/

// ensure `.include()` on `mail` is applied before `approvals`
import '@mail/widgets/form_renderer/form_renderer';

import FormRenderer from 'web.FormRenderer';


/**
 * Include the FormRenderer to instantiate the chatter area containing (a
 * subset of) the mail widgets (mail_thread, mail_followers and mail_activity).
 */
FormRenderer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _destroyChatterContainer() {
        this.off('o_approval_approved', this);
        this.off('o_approval_refused', this);
        this._super(...arguments);
    },
    /**
     * @override
     */
    _makeChatterContainerComponent() {
        this._super(...arguments);
        this.on('o_approval_approved', this, ev => this.trigger_up('reload', { keepChanges: true }));
        this.on('o_approval_refused', this, ev => this.trigger_up('reload', { keepChanges: true }));
    },
});
