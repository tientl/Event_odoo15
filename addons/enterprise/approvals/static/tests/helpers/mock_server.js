/** @odoo-module **/

import MockServer from 'web.MockServer';

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRpc(route, args) {
        if (args.model === 'approval.approver' && args.method === 'action_approve') {
            const ids = args.args[0];
            return this._mockApprovalApproverActionApprove(ids);
        }
        if (args.model === 'approval.approver' && args.method === 'action_refuse') {
            const ids = args.args[0];
            return this._mockApprovalApproverActionApprove(ids);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * Simulates `action_approve` on `approval.approver`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockApprovalApproverActionApprove(ids) {
        // TODO implement this mock and improve related tests (task-2300537)
    },
    /**
     * Simulates `action_refuse` on `approval.approver`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockApprovalApproverActionRefuse(ids) {
        // TODO implement this mock and improve related tests (task-2300537)
    },
});
