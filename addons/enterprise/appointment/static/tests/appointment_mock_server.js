/** @odoo-module **/

import MockServer from 'web.MockServer';
import session from 'web.session';

MockServer.include({
    /**
     * Simulate the creation of a custom appointment type
     * by receiving a list of slots.
     * @override
     */
    async _performRpc(route, args) {
        const _super = this._super.bind(this);
        if (route === "/appointment/calendar_appointment_type/create_custom") {
            const slots = args.slots;
            if (slots.length === 0) {
                return false;
            }
            const customAppointmentTypeID = this._mockCreate('calendar.appointment.type', {
                name: "Appointment with Actual Employee",
                employee_ids: [session.uid],
                category: 'custom',
                website_published: true,
            });
            let slotIDs = [];
            slots.forEach(slot => {
                const slotID = this._mockCreate('calendar.appointment.slot', {
                    appointment_type_id: customAppointmentTypeID,
                    start_datetime: slot.start,
                    end_datetime: slot.end,
                    slot_type: 'unique',
                });
                slotIDs.push(slotID);
            });
            return {
                id: customAppointmentTypeID,
                url: `http://amazing.odoo.com/calendar/3?filter_employee_ids=%5B${session.uid}%5D`,
            };
        } else if (route === "/appointment/calendar_appointment_type/search_create_work_hours") {
            let workHoursAppointmentID = this._mockSearch(
                'calendar.appointment.type',
                [[['category', '=', 'work_hours'], ['employee_ids', 'in', [session.uid]]]],
                {},
            )[0];
            if (!workHoursAppointmentID) {
                workHoursAppointmentID = this._mockCreate('calendar.appointment.type', {
                    name: "Work Hours with Actual Employee",
                    employee_ids: [session.uid],
                    category: 'work_hours',
                    website_published: true,
                });
            }
            return {
                id: workHoursAppointmentID,
                url: `http://amazing.odoo.com/calendar/3?filter_employee_ids=%5B${session.uid}%5D`,
            };
        } else if (route === "/appointment/calendar_appointment_type/get_employee_appointment_types") {
            if (session.uid) {
                const employeeID = session.uid;
                const domain = [
                    ['employee_ids', 'in', [employeeID]],
                    ['category', '!=', 'custom'],
                    ['website_published', '=', true],
                ];
                const appointment_types_info = this._mockSearchRead('calendar.appointment.type', [domain, ['category', 'name']], {});

                return Promise.resolve({
                    employee_id: employeeID,
                    appointment_types_info: appointment_types_info
                });
            }
            return {};
        }
        return await _super(...arguments);
    },
});
