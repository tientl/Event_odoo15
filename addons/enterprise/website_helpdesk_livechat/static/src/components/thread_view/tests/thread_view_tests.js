/** @odoo-module **/

import { insertAndReplace, link } from '@mail/model/model_field_command';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('website_helpdesk_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_view', {}, function () {
QUnit.module('thread_view_tests.js', {
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

QUnit.test('[technical] /helpdesk command gets a body as kwarg', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 20,
        is_pinned: true,
        message_unread_counter: 0,
        seen_message_id: 10,
        name: "General",
    }];
    const { createThreadViewComponent } = await this.start({
        mockRPC(route, { model, method, kwargs }) {
            if (model === 'mail.channel' && method === 'execute_command_helpdesk') {
                assert.step(`execute command helpdesk. body: ${kwargs.body}`);
                return Promise.resolve();
            }
            return this._super(...arguments);
        }
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel'
    });
    const threadViewer = this.messaging.models['mail.thread_viewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: link(thread),
    });
    await createThreadViewComponent(threadViewer.threadView);

    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "/helpdesk something"));
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());
    assert.verifySteps([
        'execute command helpdesk. body: /helpdesk something',
    ]);
});

});
});
});
