/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

import { mock } from 'web.test_utils';

import { methods } from 'web_mobile.core';

QUnit.module('mail_enterprise', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager', {}, function () {
QUnit.module('chat_window_manager_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            return start(Object.assign(
                {
                    data: this.data,
                    hasChatWindow: true,
                },
                params,
            ));
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test("'backbutton' event should close chat window", async function (assert) {
    assert.expect(1);

    // simulate the feature is available on the current device
    mock.patch(methods, {
        overrideBackButton({ enabled }) {},
    });

    this.data['mail.channel'].records.push({
        id: 20,
        is_minimized: true,
        state: 'open',
    });
    await this.start();
    await afterNextRender(() => {
        // simulate 'backbutton' event triggered by the mobile app
        const backButtonEvent = new Event('backbutton');
        document.dispatchEvent(backButtonEvent);
    });
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "chat window should be closed after receiving the backbutton event"
    );

    // component must be destroyed before the overrideBackButton is unpatched
    afterEach(this);
    mock.unpatch(methods);
});

QUnit.test('[technical] chat window should properly override the back button', async function (assert) {
    assert.expect(4);

    // simulate the feature is available on the current device
    mock.patch(methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createMessagingMenuComponent } = await this.start({
        env: {
            device: {
                isMobile: true,
            },
        },
    });
    await createMessagingMenuComponent();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    assert.verifySteps(
        ['overrideBackButton: true'],
        "the overrideBackButton method should be called with true when the chat window is mounted"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandBack').click()
    );
    // The messaging menu is re-open when a chat window is closed,
    // so we need to close it because it overrides the back button too.
    // As long as something overrides the back button, it can't be disabled.
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.verifySteps(
        ['overrideBackButton: false'],
        "the overrideBackButton method should be called with false when the chat window is unmounted"
    );

    // component must be destroyed before the overrideBackButton is unpatched
    afterEach(this);
    mock.unpatch(methods);
});

});
});
});
