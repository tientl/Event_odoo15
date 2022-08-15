/** @odoo-module **/

// ensure the component is registered beforehand.
import '@mail/components/activity/activity';
import { getMessagingComponent } from '@mail/utils/messaging_component';
import {
    afterEach,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('voip', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createActivityComponent = async activity => {
            const ActivityComponent = getMessagingComponent('Activity');
            ActivityComponent.env = this.env;
            this.component = new ActivityComponent(null, {
                activityLocalId: activity.localId,
            });
            await this.component.mount(this.widget.el);
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

QUnit.test('activity: rendering - only with mobile number', async function (assert) {
    assert.expect(5);

    await this.start();
    const activity = this.messaging.models['mail.activity'].create({
        id: 100,
        mobile: '+3212345678',
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity_voipNumberMobile',
        "should have a container for mobile"
    );
    assert.containsOnce(
        document.querySelector('.o_Activity_voipNumberMobile'),
        '.o_Activity_voipCallMobile',
        "should have a link for mobile"
    );
    assert.containsNone(
        document.body,
        'o_Activity_voipNumberPhone',
        "should not have a container for phone"
    );
    assert.containsNone(
        document.body,
        'o_Activity_voipCallPhone',
        "should not have a link for phone"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_voipNumberMobile').textContent.trim(),
        '+3212345678',
        "should have correct mobile number without a tag"
    );
});

QUnit.test('activity: rendering - only with phone number', async function (assert) {
    assert.expect(5);

    await this.start();
    const activity = this.messaging.models['mail.activity'].create({
        id: 100,
        phone: '+3287654321',
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity_voipNumberPhone'
    );
    assert.containsOnce(
        document.querySelector('.o_Activity_voipNumberPhone'),
        '.o_Activity_voipCallPhone'
    );
    assert.containsNone(
        document.body,
        'o_Activity_voipNumberMobile',
        "should not have a container for mobile"
    );
    assert.containsNone(
        document.body,
        'o_Activity_voipCallMobile',
        "should not have a link for mobile"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_voipNumberPhone').textContent.trim(),
        '+3287654321',
        "should have correct phone number without a tag"
    );
});

QUnit.test('activity: rendering - with both mobile and phone number', async function (assert) {
    assert.expect(6);

    await this.start();
    const activity = this.messaging.models['mail.activity'].create({
        id: 100,
        mobile: '+3212345678',
        phone: '+3287654321',
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity_voipNumberMobile',
        "should have a container for mobile"
    );
    assert.containsOnce(
        document.querySelector('.o_Activity_voipNumberMobile'),
        '.o_Activity_voipCallMobile',
        "should have a link for mobile"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_voipNumberMobile').textContent.trim(),
        'Mobile: +3212345678',
        "should have correct mobile number with a tag"
    );

    assert.containsOnce(
        document.body,
        '.o_Activity_voipNumberPhone',
        "should have container for phone"
    );
    assert.containsOnce(
        document.querySelector('.o_Activity_voipNumberPhone'),
        '.o_Activity_voipCallPhone',
        "should have a link for phone"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_voipNumberPhone').textContent.trim(),
        'Phone: +3287654321',
        "should have correct phone number with a tag"
    );
});

QUnit.test('activity: calling - only with mobile', async function (assert) {
    assert.expect(4);

    await this.start();
    const onVoipActivityCallMobile = (ev) => {
        assert.step('voip_call_mobile_triggered');
        assert.strictEqual(
            ev.detail.number,
            '+3212345678',
            "Voip call should be triggered with the mobile number of the activity"
        );
        assert.strictEqual(
            ev.detail.activityId,
            100,
            "Voip call should be triggered with the id of the activity"
        );
    };
    document.addEventListener('voip_activity_call', onVoipActivityCallMobile);
    const activity = this.messaging.models['mail.activity'].create({
        id: 100,
        mobile: '+3212345678',
    });
    await this.createActivityComponent(activity);

    document.querySelector('.o_Activity_voipCallMobile').click();
    assert.verifySteps(
        ['voip_call_mobile_triggered'],
        "A voip call has to be triggered"
    );
    document.removeEventListener('voip_activity_call', onVoipActivityCallMobile);
});

QUnit.test('activity: calling - only with phone', async function (assert) {
    assert.expect(4);

    await this.start();
    const onVoipActivityCallPhone = (ev) => {
        assert.step('voip_call_phone_triggered');
        assert.strictEqual(
            ev.detail.number,
            '+3287654321',
            "Voip call should be triggered with the phone number of the activity"
        );
        assert.strictEqual(
            ev.detail.activityId,
            100,
            "Voip call should be triggered with the id of the activity"
        );
    };
    document.addEventListener('voip_activity_call', onVoipActivityCallPhone);
    const activity = this.messaging.models['mail.activity'].create({
        id: 100,
        phone: '+3287654321',
    });
    await this.createActivityComponent(activity);

    document.querySelector('.o_Activity_voipCallPhone').click();
    assert.verifySteps(
        ['voip_call_phone_triggered'],
        "A voip call has to be triggered"
    );
    document.removeEventListener('voip_activity_call', onVoipActivityCallPhone);
});

});
});
});
