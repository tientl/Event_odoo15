/** @odoo-module **/

import { link } from '@mail/model/model_field_command';

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
QUnit.module('attachment', {}, function () {
QUnit.module('attachment_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { afterEvent, components, env, widget } = res;
            this.afterEvent = afterEvent;
            this.components = components;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test("'backbutton' event should close attachment viewer", async function (assert) {
    assert.expect(1);

    // simulate the feature is available on the current device
    mock.patch(methods, {
        overrideBackButton({ enabled }) {},
    });

    const { createMessageComponent } = await this.start({
        env: {
            device: {
                isMobile: true,
            },
        },
        hasDialog: true,
    });
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
    await afterNextRender(() => {
        // simulate 'backbutton' event triggered by the mobile app
        const backButtonEvent = new Event('backbutton');
        document.dispatchEvent(backButtonEvent);
    });
    assert.containsNone(
        document.body,
        '.o_Dialog',
        "attachment viewer should be closed after receiving the backbutton event"
    );

    // component must be destroyed before the overrideBackButton is unpatched
    afterEach(this);
    mock.unpatch(methods);
});

QUnit.test('[technical] attachment viewer should properly override the back button', async function (assert) {
    assert.expect(4);

    // simulate the feature is available on the current device
    mock.patch(methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });

    const { createMessageComponent } = await this.start({
        env: {
            device: {
                isMobile: true,
            },
        },
        hasDialog: true,
    });
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
    assert.verifySteps(
        ['overrideBackButton: true'],
        "the overrideBackButton method should be called with true when the attachment viewer is mounted"
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentViewer_headerItemButtonClose').click()
    );
    assert.verifySteps(
        ['overrideBackButton: false'],
        "the overrideBackButton method should be called with false when the attachment viewer is unmounted"
    );

    // component must be destroyed before the overrideBackButton is unpatched
    afterEach(this);
    mock.unpatch(methods);
});

});
});
});
