/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class Approval extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {approvals.approval}
     */
    get approval() {
        return this.messaging && this.messaging.models['approvals.approval'].get(this.props.approvalLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onClickApprove() {
        await this.approval.approve();
        this.trigger('o-approval-approved');
    }

    /**
     * @private
     */
    async _onClickRefuse() {
        await this.approval.refuse();
        this.trigger('o-approval-refused');
    }

}

Object.assign(Approval, {
    props: {
        approvalLocalId: String,
    },
    template: 'approvals.Approval',
});

registerMessagingComponent(Approval);

export default Approval;
