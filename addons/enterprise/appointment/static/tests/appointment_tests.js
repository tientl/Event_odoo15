/** @odoo-module **/

import AttendeeCalendarView from 'calendar.CalendarView';
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import session from 'web.session';
import testUtils from 'web.test_utils';

const createCalendarView = testUtils.createCalendarView;
const initialDate = new Date(moment().add(1, 'years').format('YYYY-01-05 00:00:00'));

QUnit.module('appointment.appointment_link', {
    beforeEach: function () {
        patchWithCleanup(session, {
            uid: 1,
        });
        this.data = {
            'res.users': {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    name: {string: 'Name', type: 'char'},
                    partner_id: {string: 'Partner', type: 'many2one', relation: 'res.partner'},
                    employee_id: {string: 'Employee', type: 'many2one', relation: 'hr.employee'},
                },
                records: [
                    {id: session.uid, name: 'User 1', partner_id: 1, employee_id: 1},
                    {id: 214, name: 'User 214', partner_id: 214, employee_id: 214},
                    {id: 216, name: 'User 216', partner_id: 216, employee_id: 216},
                ],
            },
            'res.partner': {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    display_name: {string: "Displayed name", type: "char"},
                },
                records: [
                    {id: 1, display_name: 'Partner 1'},
                    {id: 214, display_name: 'Partner 214'},
                    {id: 216, display_name: 'Partner 216'},
                ],
            },
            'calendar.event': {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    user_id: {string: 'User', type: 'many2one', relation: 'res.users'},
                    partner_id: {string: 'Partner', type: 'many2one', relation: 'res.partner', related: 'user_id.partner_id'},
                    name: {string: 'Name', type: 'char'},
                    start_date: {string: 'Start date', type: 'date'},
                    stop_date: {string: 'Stop date', type: 'date'},
                    start: {string: 'Start datetime', type: 'datetime'},
                    stop: {string: 'Stop datetime', type: 'datetime'},
                    allday: {string: 'Allday', type: 'boolean'},
                    partner_ids: {string: 'Attendees', type: 'one2many', relation: 'res.partner'},
                    appointment_type_id: {string: 'Appointment Type', type: 'many2one', relation: 'calendar.appointment.type'},
                },
                records: [{
                    id: 1,
                    user_id: session.uid,
                    partner_id: session.uid,
                    name: 'Event 1',
                    start: moment().add(1, 'years').format('YYYY-01-12 10:00:00'),
                    stop: moment().add(1, 'years').format('YYYY-01-12 11:00:00'),
                    allday: false,
                    partner_ids: [1],
                }, {
                    id: 2,
                    user_id: session.uid,
                    partner_id: session.uid,
                    name: 'Event 2',
                    start: moment().add(1, 'years').format('YYYY-01-05 10:00:00'),
                    stop: moment().add(1, 'years').format('YYYY-01-05 11:00:00'),
                    allday: false,
                    partner_ids: [1],
                }, {
                    id: 3,
                    user_id: 214,
                    partner_id: 214,
                    name: 'Event 3',
                    start: moment().add(1, 'years').format('YYYY-01-05 10:00:00'),
                    stop: moment().add(1, 'years').format('YYYY-01-05 11:00:00'),
                    allday: false,
                    partner_ids: [214],
                }
                ],
                check_access_rights: function () {
                    return Promise.resolve(true);
                }
            },
            'calendar.appointment.type': {
                fields: {
                    name: {type: 'char'},
                    website_url: {type: 'char'},
                    employee_ids: {type: 'many2many', relation: 'hr.employee'},
                    website_published: {type: 'boolean'},
                    slot_ids: {type: 'one2many', relation: 'calendar.appointment.slot'},
                    category: {
                        type: 'selection',
                        selection: [['website', 'Website'], ['custom', 'Custom'], ['work_hours', 'Work Hours']]
                    },
                },
                records: [{
                    id: 1,
                    name: 'Very Interesting Meeting',
                    website_url: '/calendar/schedule-a-demo-1/appointment',
                    website_published: true,
                    employee_ids: [214],
                    category: 'website',
                }, {
                    id: 2,
                    name: 'Test Appointment',
                    website_url: '/calendar/test-appointment-2/appointment',
                    website_published: true,
                    employee_ids: [session.uid],
                    category: 'website',
                }],
            },
            'calendar.appointment.slot': {
                fields: {
                    appointment_type_id: {type: 'many2one', relation: 'calendar.appointment.type'},
                    start_datetime: {string: 'Start', type: 'datetime'},
                    end_datetime: {string: 'End', type: 'datetime'},
                    duration: {string: 'Duration', type: 'float'},
                    slot_type: {
                        string: 'Slot Type',
                        type: 'selection',
                        selection: [['recurring', 'Recurring'], ['unique', 'One Shot']],
                    },
                },
            },
            'hr.employee': {
                fields: {
                    id: {type: 'integer'},
                    name: {type: 'char'},
                    user_id: {type: 'many2one', relation: 'res.users'},
                },
                records: [{
                    id: session.uid,
                    name: 'Actual Employee',
                    user_id: session.uid,
                }, {
                    id: 214,
                    name: 'Denis Ledur',
                    user_id: 214,
                },{
                    id: 216,
                    name: 'Bhailalbhai',
                    user_id: 216,
                }],
            },
            'filter_partner': {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'res.users'},
                    partner_id: {string: "partner", type: "many2one", relation: 'res.partner'},
                    partner_checked: {string: "checked", type: "boolean"},
                },
                records: [
                    {
                        id: 4,
                        user_id: session.uid,
                        partner_id: session.uid,
                        partner_checked: true
                    }, {
                        id: 5,
                        user_id: 214,
                        partner_id: 214,
                        partner_checked: true,
                    }
                ]
            },
        };
    },
    afterReach() {
        session.uid = null;
    }
}, function () {

QUnit.test('verify appointment links button are displayed', async function (assert) {
    assert.expect(3);

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    attendee="partner_ids">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
            <field name="partner_id" filters="1" invisible="1"/>
        </calendar>`,
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: async function (route, args) {
            if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.containsOnce(calendar, 'button:contains("Share Availabilities")');

    await testUtils.dom.click(calendar.$('#dropdownAppointmentLink'));

    assert.containsOnce(calendar, 'button:contains("Test Appointment")');
    assert.containsOnce(calendar, 'button:contains("Work Hours")');

    calendar.destroy();
});

QUnit.test('discard slot in calendar', async function (assert) {
    assert.expect(11);

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        translateParameters: { // Avoid issues due to localization formats
            time_format: "%I:%M:%S",
        },
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: async function (route, args) {
            if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
    }, { positionalClicks: true });

    await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input'));
    await testUtils.dom.click(calendar.$('button:contains("Share Availabilities")'));
    await testUtils.nextTick();

    assert.strictEqual(calendar.model.calendarMode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(calendar, '.fc-event', 2);
    assert.containsNone(calendar, '.o_calendar_slot');
    
    await testUtils.dom.click(calendar.$('.o_calendar_button_next'));
    assert.containsOnce(calendar, '.fc-event', 'There is one calendar event');
    assert.containsNone(calendar, '.o_calendar_slot', 'There is no slot yet');

    const top = calendar.$('.fc-axis:contains(1pm)').offset().top + 5;
    const left = calendar.$('.fc-day:last()').offset().left + 5;

    testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
    testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
    await testUtils.nextTick();
    assert.containsN(calendar, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(calendar, '.o_calendar_slot', 'One of them is a slot');

    await testUtils.dom.click(calendar.$('button.o_appointment_discard_slots'));
    await testUtils.nextTick();
    assert.containsOnce(calendar, '.fc-event', 'The calendar event is still here');
    assert.containsNone(calendar, '.o_calendar_slot', 'The slot has been discarded');

    await testUtils.dom.click(calendar.$('.o_calendar_button_prev'));
    assert.containsN(calendar, '.fc-event', 2);
    assert.containsNone(calendar, '.o_calendar_slot');

    calendar.destroy();
});

QUnit.test("cannot move real event in slots-creation mode", async function (assert) {
    assert.expect(4);

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="start"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: function (route, args) {
            if (args.method === "write") {
                assert.step('write event');
            } else if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
    });

    await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input'));
    await testUtils.dom.click(calendar.$('button:contains("Share Availabilities")'));

    assert.strictEqual(calendar.model.calendarMode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(calendar, '.fc-event', 2);
    assert.containsNone(calendar, '.o_calendar_slot');

    await testUtils.dom.dragAndDrop(calendar.$('.fc-event:first()'), calendar.$('.fc-day').first());
    await testUtils.nextTick();

    assert.verifySteps([]);
    calendar.destroy();
});

QUnit.test("create slots for custom appointment type", async function (assert) {
    assert.expect(13);

    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (value) => {
                    assert.strictEqual(
                        value,
                        `http://amazing.odoo.com/calendar/3?filter_employee_ids=%5B${session.uid}%5D`
                    );
                }
            }
        }
    });

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        translateParameters: { // Avoid issues due to localization formats
            time_format: "%I:%M:%S",
        },
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: function (route, args) {
            if (route === "/appointment/calendar_appointment_type/create_custom") {
                assert.step(route);
            } else if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            'web.base.url': 'http://amazing.odoo.com',
        },
    }, { positionalClicks: true });

    await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input'));
    await testUtils.dom.click(calendar.$('button:contains("Share Availabilities")'));

    assert.strictEqual(calendar.model.calendarMode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(calendar, '.fc-event', 2);
    assert.containsNone(calendar, '.o_calendar_slot');
    
    await testUtils.dom.click(calendar.$('.o_calendar_button_next'));
    assert.containsOnce(calendar, '.fc-event', 'There is one calendar event');
    assert.containsNone(calendar, '.o_calendar_slot', 'There is no slot yet');

    const top = calendar.$('.fc-axis:contains(1pm)').offset().top + 5;
    const left = calendar.$('.fc-day:last()').offset().left + 5;

    testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
    testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
    await testUtils.nextTick();
    assert.containsN(calendar, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(calendar, '.o_calendar_slot', 'One of them is a slot');

    await testUtils.dom.click(calendar.$('button.o_appointment_create_custom_appointment'));
    assert.verifySteps(['/appointment/calendar_appointment_type/create_custom']);
    assert.containsOnce(calendar, '.fc-event', 'The calendar event is still here');
    assert.containsNone(calendar, '.o_calendar_slot', 'The slot has been cleared after the creation');
    assert.strictEqual(this.data['calendar.appointment.slot'].records.length, 1);

    calendar.destroy();
});

QUnit.test('filter works in slots-creation mode', async function (assert) {
    assert.expect(11);

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
            <field name="partner_id" filters="1" invisible="1"/>
        </calendar>`,
        translateParameters: { // Avoid issues due to localization formats
            time_format: "%I:%M:%S",
        },
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: function (route, args) {
            if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
    }, { positionalClicks: true });

    await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input'));
    // Two events are displayed
    assert.containsN(calendar, '.fc-event', 2);
    assert.containsNone(calendar, '.o_calendar_slot');

    // Switch to slot-creation mode and create a slot for a custom appointment type
    await testUtils.dom.click(calendar.$('button:contains("Share Availabilities")'));

    assert.strictEqual(calendar.model.calendarMode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");

    await testUtils.dom.click(calendar.$('.o_calendar_button_next'));
    assert.containsOnce(calendar, '.fc-event');
    assert.containsNone(calendar, '.o_calendar_slot');

    const top = calendar.$('.fc-axis:contains(1pm)').offset().top + 5;
    const left = calendar.$('.fc-day:last()').offset().left + 5;

    testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
    testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
    await testUtils.nextTick();
    assert.containsN(calendar, '.fc-event', 2, 'The slot is successfully created in the calendar');
    assert.containsOnce(calendar, '.o_calendar_slot');

    // Modify filters of the calendar to display less calendar event
    await testUtils.dom.click(calendar.$('.o_calendar_filter_item:last() > input'));
    assert.containsOnce(calendar, '.fc-event', 'There is now only 1 events displayed');
    assert.containsOnce(calendar, '.o_calendar_slot', 'The slot created is still displayed');

    await testUtils.dom.click(calendar.$('.o_calendar_filter_item:last() > input'));
    await testUtils.dom.click(calendar.$('button.o_appointment_discard_slots'));
    assert.containsOnce(calendar, '.fc-event', 'There is now only 1 calendar event displayed');
    assert.containsNone(calendar, '.o_calendar_slot', 'There is no more slots in the calendar view');

    calendar.destroy();
});

QUnit.test('click & copy appointment type url', async function (assert) {
    assert.expect(1);

    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (value) => {
                    assert.strictEqual(
                        value,
                        `http://amazing.odoo.com/calendar/2?filter_employee_ids=%5B${session.uid}%5D`
                    );
                }
            }
        }
    });

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: function (route, args) {
            if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            'web.base.url': 'http://amazing.odoo.com',
        },
    }, { positionalClicks: true });

    await testUtils.dom.click(calendar.$('#dropdownAppointmentLink'));
    await testUtils.dom.click(calendar.$('.o_appointment_appointment_link_clipboard:first'));

    calendar.destroy();
});

QUnit.test('create/search work hours appointment type', async function (assert) {
    assert.expect(9);

    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (value) => {
                    assert.strictEqual(
                        value,
                        `http://amazing.odoo.com/calendar/3?filter_employee_ids=%5B${session.uid}%5D`
                    );
                }
            }
        }
    });

    const calendar = await createCalendarView({
        View: AttendeeCalendarView,
        model: 'calendar.event',
        data: this.data,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        viewOptions: {
            initialDate: initialDate,
        },
        mockRPC: function (route, args) {
            if (route === "/appointment/calendar_appointment_type/search_create_work_hours") {
                assert.step(route);
            } else if (route === '/microsoft_calendar/sync_data') {
                return Promise.resolve();
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            'web.base.url': 'http://amazing.odoo.com',
        },
    }, { positionalClicks: true });

    assert.strictEqual(2, this.data['calendar.appointment.type'].records.length)

    await testUtils.dom.click(calendar.$('#dropdownAppointmentLink'));

    await testUtils.dom.click(calendar.$('.o_appointment_search_create_work_hours_appointment'));
    await testUtils.nextTick();

    assert.verifySteps(['/appointment/calendar_appointment_type/search_create_work_hours']);
    assert.strictEqual(3, this.data['calendar.appointment.type'].records.length,
        "Create a new appointment type")

    await testUtils.dom.click(calendar.$('.o_appointment_change_display'));
    await testUtils.dom.click(calendar.$('#dropdownAppointmentLink'));

    await testUtils.dom.click(calendar.$('.o_appointment_search_create_work_hours_appointment'));
    await testUtils.nextTick();

    assert.verifySteps(['/appointment/calendar_appointment_type/search_create_work_hours']);
    assert.strictEqual(3, this.data['calendar.appointment.type'].records.length,
        "Does not create a new appointment type");

    calendar.destroy();
});
});
