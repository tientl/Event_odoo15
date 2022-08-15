/** @odoo-module **/

import {
    afterEach,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('approvals', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createActivityComponent = async activity => {
            await createRootMessagingComponent(this, 'Activity', {
                props: { activityLocalId: activity.localId },
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('activity with approval to be made by logged user', async function (assert) {
    assert.expect(14);

    await this.start();
    const activityData = this.messaging.models['mail.activity'].convertData({
        activity_type_id: [1, 'Approval'],
        approver_id: 12,
        approver_status: 'pending',
        can_write: true,
        id: 10,
        user_id: [this.messaging.currentUser.id, "Eden Hazard"],
    });
    const activity = this.messaging.models['mail.activity'].create(activityData);
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_sidebar',
        "should have activity sidebar"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_core',
        "should have activity core"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_user',
        "should have activity user"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_info',
        "should have activity info"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_note',
        "should not have activity note"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_details',
        "should not have activity details"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_mailTemplates',
        "should not have activity mail templates"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_editButton',
        "should not have activity Edit button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_cancelButton',
        "should not have activity Cancel button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_markDoneButton',
        "should not have activity Mark as Done button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_uploadButton',
        "should not have activity Upload button"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_approveButton',
        "should have approval approve button"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_refuseButton',
        "should have approval refuse button"
    );
});

QUnit.test('activity with approval to be made by another user', async function (assert) {
    assert.expect(16);

    await this.start();
    const activityData = this.messaging.models['mail.activity'].convertData({
        activity_type_id: [1, 'Approval'],
        approver_id: 12,
        approver_status: 'pending',
        can_write: true,
        id: 10,
        user_id: [42, "Simon Mignolet"],
    });
    const activity = this.messaging.models['mail.activity'].create(activityData);
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_sidebar',
        "should have activity sidebar"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_core',
        "should have activity core"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_user',
        "should have activity user"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_info',
        "should have activity info"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_note',
        "should not have activity note"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_details',
        "should not have activity details"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_mailTemplates',
        "should not have activity mail templates"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_editButton',
        "should not have activity Edit button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_cancelButton',
        "should not have activity Cancel button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_markDoneButton',
        "should not have activity Mark as Done button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_uploadButton',
        "should not have activity Upload button"
    );
    assert.containsNone(
        document.body,
        '.o_Approval_approveButton',
        "should not have approval approve button"
    );
    assert.containsNone(
        document.body,
        '.o_Approval_refuseButton',
        "should not have approval refuse button"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_toApproveText',
        "should contain 'To approve' text container"
    );
    assert.strictEqual(
        document.querySelector('.o_Approval_toApproveText').textContent.trim(),
        "To Approve",
        "should contain 'To approve' text"
    );
});

QUnit.test('approve approval', async function (assert) {
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'action_approve') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
                assert.step('action_approve');
            }
            return this._super(...arguments);
        },
    });
    const activityData = this.messaging.models['mail.activity'].convertData({
        activity_type_id: [1, 'Approval'],
        approver_id: 12,
        approver_status: 'pending',
        can_write: true,
        id: 10,
        user_id: [this.messaging.currentUser.id, "Eden Hazard"],
    });
    const activity = this.messaging.models['mail.activity'].create(activityData);
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_approveButton',
        "should have approval approve button"
    );

    document.querySelector('.o_Approval_approveButton').click();
    assert.verifySteps(['action_approve'], "Approve button should trigger the right rpc call");
});

QUnit.test('refuse approval', async function (assert) {
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'action_refuse') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
                assert.step('action_refuse');
            }
            return this._super(...arguments);
        },
    });
    const activityData = this.messaging.models['mail.activity'].convertData({
        activity_type_id: [1, 'Approval'],
        approver_id: 12,
        approver_status: 'pending',
        can_write: true,
        id: 10,
        user_id: [this.messaging.currentUser.id, "Eden Hazard"],
    });
    const activity = this.messaging.models['mail.activity'].create(activityData);
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_refuseButton',
        "should have approval refuse button"
    );

    document.querySelector('.o_Approval_refuseButton').click();
    assert.verifySteps(['action_refuse'], "Refuse button should trigger the right rpc call");
});

});
});
});
