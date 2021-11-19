/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class SignRequest extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.activity}
     */
    get activity() {
        return this.messaging && this.messaging.models['mail.activity'].get(this.props.activityLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onClickRequestSign() {
        this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("Signature Request"),
                type: 'ir.actions.act_window',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                res_model: 'sign.send.request',
            },
            options: {
                additional_context: {
                    'sign_directly_without_mail': false,
                    'default_activity_id': this.activity.id,
                },
                on_close: () => {
                    var activity = this.messaging.models['mail.activity'].get(this.props.activityLocalId);
                    activity.update();
                    this.trigger('reload');
                },
            },
        });
    }

}

Object.assign(SignRequest, {
    props: {
        activityLocalId: String,
    },
    template: 'sign.SignRequest',
});

registerMessagingComponent(SignRequest);

export default SignRequest;
