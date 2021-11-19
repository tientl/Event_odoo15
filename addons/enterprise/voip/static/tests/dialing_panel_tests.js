/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

import mobile from 'web_mobile.core';
import DialingPanel from 'voip.DialingPanel';
import UserAgent from 'voip.UserAgent';

import testUtils from 'web.test_utils';

/**
 * Create a dialing Panel and attach it to a parent. Uses params to create the parent
 * and to define if mode debug is set
 *
 * @param {Object} params
 * @return {Promise<Object>} resolve with object: { dialingPanel, parent }
 */
async function createDialingPanel(params) {
    const { widget: parent } = await start(params);
    const dialingPanel = new DialingPanel(parent);
    const container = params.debug ? $('body') : $('#qunit-fixture');
    await dialingPanel.appendTo(container);
    dialingPanel._onToggleDisplay(); // show panel
    await dialingPanel._refreshPhoneCallsStatus();
    await testUtils.nextTick();
    return {
        dialingPanel,
        parent
    };
}

QUnit.module('voip', {}, function () {
QUnit.module('DialingPanel', {
    beforeEach() {
        beforeEach(this);

        this.onaccepted = undefined;
        this.recentList = {};
        // generate 3 records
        this.phoneCallDetailsData = [10,23,42].map(id => {
            return {
                activity_id: 50+id,
                activity_model_name: "A model",
                activity_note: false,
                activity_res_id: 200+id,
                activity_res_model: 'res.model',
                activity_summary: false,
                date_deadline: "2018-10-26",
                id,
                mobile: false,
                name: `Record ${id}`,
                note: false,
                partner_email: `partner ${100+id} @example.com`,
                partner_id: 100+id,
                partner_avatar_128: '',
                partner_name: `Partner ${100+id}`,
                phone: "(215)-379-4865",
                state: 'open',
             };
        });
        testUtils.mock.patch(UserAgent, {
            /**
             * Do not play() on media, to prevent "NotAllowedError". This may
             * be triggered if no DOM manipulation is detected before playing
             * the media (chrome policy to prevent from autoplaying)
             *
             * @override
             */
            PLAY_MEDIA: false,
            /**
             * Register callback to avoid the timeout that will accept the call
             * after 3 seconds in demo mode
             *
             * @override
             * @private
             * @param {function} func
             */
            _demoTimeout: func => {
                this.onaccepted = func;
            }
        });
    },
    afterEach() {
        testUtils.mock.unpatch(UserAgent);
        afterEach(this);
    },
}, function () {

QUnit.test('autocall flow', async function (assert) {
    assert.expect(34);

    const self = this;
    let counterNextActivities = 0;

    const {
        dialingPanel,
        parent,
    } = await createDialingPanel({
        data: this.data,
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                const id = args.args[0];
                switch (args.method) {
                case 'get_next_activities_list':
                    counterNextActivities++;
                    return self.phoneCallDetailsData.filter(phoneCallDetailData =>
                        ['done', 'cancel'].indexOf(phoneCallDetailData.state) === -1);
                case 'get_recent_list':
                    return self.phoneCallDetailsData.filter(phoneCallDetailData =>
                        phoneCallDetailData.state === 'open');
                case 'init_call':
                    assert.step('init_call');
                    return [];
                case 'hangup_call':
                    if (args.kwargs.done) {
                        self.phoneCallDetailsData.find(d => d.id === id).state = 'done';
                    }
                    assert.step('hangup_call');
                    return;
                case 'create_from_rejected_call':
                    (self.phoneCallDetailsData.find(d => d.id === id) || {}).state = 'pending';
                    assert.step('rejected_call');
                    return {id: 418};
                case 'canceled_call':
                    self.phoneCallDetailsData.find(d => d.id === id).state = 'pending';
                    assert.step('canceled_call');
                    return [];
                case 'remove_from_queue':
                    self.phoneCallDetailsData.find(d => d.id === id).state = 'cancel';
                    assert.step('remove_from_queue');
                    return [];
                case 'create_from_incoming_call':
                    assert.step('incoming_call');
                    return {id: 200};
                case 'create_from_incoming_call_accepted':
                    assert.step('incoming_call_accepted');
                    return {id: 201};
                }
            }
            return this._super(...arguments);
        },
    });

    // make a first call
    assert.containsNone(
        dialingPanel,
        '.o_phonecall_details',
        "Details should not be visible yet");
    assert.containsN(
        dialingPanel, `
            .o_dial_next_activities
            .o_dial_phonecalls
            .o_dial_phonecall`,
        3,
        "Next activities tab should have 3 phonecalls at the beginning");

    // select first call with autocall
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    assert.isVisible(
        dialingPanel.$('.o_phonecall_details'),
        "Details should have been shown");
    assert.strictEqual(
        dialingPanel
            .$(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                span`)
            .html(),
        'Partner 110',
        "Details should have been shown");

    // start call
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    assert.isVisible(
        dialingPanel
            .$('.o_phonecall_in_call')
            .first(),
        "in call info should be displayed");
    assert.ok(dialingPanel._isInCall);

    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.notOk(dialingPanel._isInCall);
    assert.strictEqual(
        dialingPanel
            .$(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                span`)
            .html(),
        'Partner 123',
        "Phonecall of second partner should have been displayed");

    // close details
    await testUtils.dom.click(dialingPanel.$('.o_phonecall_details_close'));
    assert.containsN(
        dialingPanel, `
            .o_dial_next_activities
            .o_dial_phonecall`,
        2,
        "Next activities tab should have 2 phonecalls after first call");

    // hangup before accept call
    // select first call with autocall
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    assert.strictEqual(
        dialingPanel
            .$(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                span`)
            .html(),
        'Partner 123',
        "Phonecall of second partner should have been displayed");

    // start call
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    assert.isVisible(
        dialingPanel
            .$('.o_phonecall_in_call')
            .first(),
        "in call info should be displayed");

    // hangup before accept
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    // we won't accept this call, better clean the current onaccepted
    this.onaccepted = undefined;
    // close details
    await testUtils.dom.click(dialingPanel.$('.o_phonecall_details_close'));

    assert.containsN(
        dialingPanel, `
            .o_dial_next_activities
            .o_dial_phonecall`,
        2,
        "No call should have been removed");

    // end list
    // select first call with autocall
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    assert.strictEqual(
        dialingPanel
            .$(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                span`)
            .html(),
        'Partner 142',
        "Phonecall of third partner should have been displayed (second one has already been tried)");

    // start call
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.strictEqual(
        dialingPanel
            .$(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                span`)
            .html(),
        'Partner 123',
        "Phonecall of second partner should have been displayed");

    // start call
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.containsNone(
        dialingPanel, `
            .o_dial_phonecalls
            .o_dial_phonecall`,
        "The list should be empty");
    assert.strictEqual(
        counterNextActivities,
        9,
        "avoid to much call to get_next_activities_list, would be great to lower this counter");

    const incomingCallParams = {
        data: {
            number: "123-456-789"
        }
    };
    // simulate an incoming call
    await dialingPanel._onIncomingCall(incomingCallParams);
    // Accept call
    await testUtils.dom.click(dialingPanel.$('.o_dial_accept_button'));
    assert.ok(
        dialingPanel._isInCall,
        "Should be in call");

    // Hangup call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.notOk(
        dialingPanel._isInCall,
        "Call should hang up");
    assert.containsOnce(
        dialingPanel,
        '.o_phonecall_details',
        "Details should be visible");

    // simulate an incoming call
    await dialingPanel._onIncomingCall(incomingCallParams);
    await testUtils.dom.click(dialingPanel.$('.o_dial_reject_button'));
    assert.notOk(dialingPanel._isInCall);
    assert.containsOnce(
        dialingPanel,
        '.o_phonecall_details',
        "Details should be visible");
    assert.verifySteps([
        'init_call',
        'hangup_call',
        'init_call',
        'canceled_call',
        'init_call',
        'hangup_call',
        'init_call',
        'hangup_call',
        'incoming_call',
        'incoming_call_accepted',
        // 'hangup_call', // disabled due to prevent crash from phonecall with no Id
        'incoming_call',
        'rejected_call'
    ]);

    parent.destroy();
});

QUnit.test('Call from Recent tab + keypad', async function (assert) {
    assert.expect(10);

    const self = this;

    const {
        dialingPanel,
        parent,
    } = await createDialingPanel({
        data: this.data,
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                switch (args.method) {
                case 'create_from_number':
                    assert.step('create_from_number');
                    self.recentList = [{
                        call_date: '2019-06-06 08:05:47',
                        create_date: '2019-06-06 08:05:47.00235',
                        create_uid: 2,
                        date_deadline: '2019-06-06',
                        id: 0,
                        in_queue: 't',
                        name: 'Call to 123456789',
                        user_id: 2,
                        phone: '123456789',
                        phonecall_type: 'outgoing',
                        start_time: 1559808347,
                        state: 'pending',
                        write_date: '2019-06-06 08:05:48.568076',
                        write_uid: 2,
                    }];
                    return self.recentList[0];
                case 'create_from_recent':
                    assert.step('create_from_recent');
                    return {id: 202};
                case 'get_recent_list':
                    return self.recentList;
                case 'get_next_activities_list':
                    return [];
                case 'init_call':
                    assert.step('init_call');
                    return [];
                case 'hangup_call':
                    assert.step('hangup_call');
                    return;
                }
            }
            return this._super(...arguments);
        },
    });

    // make a first call
    assert.containsNone(
        dialingPanel,
        '.o_phonecall_details',
        "Details should not be visible yet");
    assert.containsNone(
        dialingPanel, `
            .o_dial_recent
            .o_dial_phonecalls
            .o_dial_phonecall`,
        "Recent tab should have 0 phonecall at the beginning");

    // select keypad
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_icon'));
    // click on 1
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[0]);
    // click on 2
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[1]);
    // click on 3
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[2]);
    // click on 4
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[3]);
    // click on 5
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[4]);
    // click on 6
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[5]);
    // click on 7
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[6]);
    // click on 8
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[7]);
    // click on 9
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[8]);
    // call number 123456789
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));

    assert.strictEqual(
        dialingPanel
            .$(`
                .o_phonecall_details
                .o_phonecall_info_name
                span`)
            .html(),
        'Call to 123456789',
        "Details should have been shown");
    assert.ok(dialingPanel._isInCall);

    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.notOk(dialingPanel._isInCall);

    // call number 123456789
    await testUtils.dom.click(dialingPanel.$('.o_dial_call_button'));
    this.onaccepted();
    // end call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.verifySteps([
        'create_from_number',
        'hangup_call',
        'create_from_recent',
        'hangup_call',
    ]);

    parent.destroy();
});

QUnit.test('keyboard navigation on dial keypad input', async function (assert) {
    assert.expect(8);

    const self = this;

    const {
        dialingPanel,
        parent,
    } = await createDialingPanel({
        data: this.data,
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                if (args.method === 'create_from_number') {
                    assert.step('create_from_number');
                    self.recentList = [{
                        call_date: '2019-06-06 08:05:47',
                        create_date: '2019-06-06 08:05:47.00235',
                        create_uid: 2,
                        date_deadline: '2019-06-06',
                        id: 0,
                        in_queue: 't',
                        name: 'Call to 987654321',
                        user_id: 2,
                        phone: '987654321',
                        phonecall_type: 'outgoing',
                        start_time: 1559808347,
                        state: 'pending',
                        write_date: '2019-06-06 08:05:48.568076',
                        write_uid: 2,
                    }];
                    return self.recentList[0];
                }
                if (args.method === 'get_next_activities_list') {
                    return self.phoneCallDetailsData.filter(phoneCallDetailData =>
                        !['done', 'cancel'].includes(phoneCallDetailData.state));
                }
                if (args.method === 'hangup_call') {
                    if (args.kwargs.done) {
                        for (const phoneCallDetailData of self.phoneCallDetailsData) {
                            if (phoneCallDetailData.id === args.args[0]) {
                                phoneCallDetailData.state = 'done';
                            }
                        }
                    }
                    assert.step('hangup_call');
                    return [];
                }
            }
            return this._super(...arguments);
        },
    });

    // make a first call
    assert.containsNone(dialingPanel, '.o_phonecall_details', 'Details should not be visible yet');

    // select keypad
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_icon'));
    // click on 9
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[8]);
    // click on 8
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[7]);
    // click on 7
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[6]);
    // click on 6
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[5]);
    // click on 5
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[4]);
    // click on 4
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[3]);
    // click on 3
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[2]);
    // click on 2
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[1]);
    // click on 1
    await testUtils.dom.click(dialingPanel.$('.o_dial_keypad_button')[0]);

    // call number 987654321 (validated by pressing enter key)
    dialingPanel.$('.o_dial_keypad_input').trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}));
    await testUtils.nextTick();

    assert.verifySteps(['create_from_number']);
    assert.strictEqual(dialingPanel.$('.o_phonecall_details .o_phonecall_info_name').text().trim(),
        'Call to 987654321', 'Details should have been shown');
    assert.ok(dialingPanel._isInCall, 'should be in call on pressing ENTER after dialing a phone number');

    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(dialingPanel.$('.o_dial_hangup_button'));
    assert.notOk(dialingPanel._isInCall, 'should no longer be in call after hangup');
    assert.verifySteps(['hangup_call']);

    parent.destroy();
});

QUnit.test('DialingPanel is closable with the BackButton in the mobile app', async function (assert) {
    assert.expect(13);

    testUtils.mock.patch(mobile.methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });

    const { dialingPanel, parent } = await createDialingPanel({
        data: this.data,
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                if (args.method === 'get_missed_call_info') {
                    return [];
                }
                if (args.method === 'get_next_activities_list') {
                    return [];
                }
            }
            return this._super(...arguments);
        },
    });

    // ensure DialingPanel is open
    await dialingPanel._showWidget();
    assert.isVisible(dialingPanel, "should be visible");
    assert.verifySteps([
        'overrideBackButton: true',
    ], "should be enabled when opened");

    // simulate 'backbutton' events triggered by the app
    await testUtils.dom.triggerEvent(document, 'backbutton');
    assert.isNotVisible(dialingPanel, "should be closed");
    assert.verifySteps([
        'overrideBackButton: false',
    ], "should be disabled when closed");

    await dialingPanel._showWidget();
    await testUtils.dom.click(dialingPanel.$('.o_dial_fold'));
    assert.verifySteps([
        'overrideBackButton: true',
        'overrideBackButton: false',
    ]);
    await testUtils.dom.click(dialingPanel.$('.o_dial_fold'));
    assert.verifySteps([
        'overrideBackButton: true',
    ], "should be enabled when unfolded");

    await testUtils.dom.click(dialingPanel.$('.o_dial_window_close'));
    assert.verifySteps([
        'overrideBackButton: false',
    ], "should be disabled when closed");

    parent.destroy();
    testUtils.mock.unpatch(mobile.methods);
});

});
});
