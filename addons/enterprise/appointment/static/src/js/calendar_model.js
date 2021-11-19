/** @odoo-module **/

import { _t } from 'web.core';
import time from 'web.time';
import CalendarModel from 'calendar.CalendarModel';

CalendarModel.include({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.calendarMode = 'default';
    },
    /**
     * Set a new mode for the calendar
     * @param {String} newMode 
     */
     setCalendarMode(newMode) {
        this.calendarMode = newMode;
    },
    /**
     * @override
     */
    __get() {
        var result = this._super(...arguments);
        result.employeeAppointmentTypes = this.data.employeeAppointmentTypes;
        result.employeeId = this.data.employeeId;
        result.calendarMode = this.calendarMode;
        return result;
    },
    /**
     * Fetch the employee of the user and the assiociated appointment types.
     * This appointment types will be rendered in a dropdown button on the calendar
     * view for the user to copy its url in order to be share with a client.
     * In case the user has no employee, this dropdown button will not be displayed.
     * @override
     * @returns {Promise}
     */
    async _loadCalendar() {
        const _super = this._super.bind(this);
        const appointmentEmployeeInfo = await this._rpc({
            route: '/appointment/calendar_appointment_type/get_employee_appointment_types',
        });
        this.data.employeeId = appointmentEmployeeInfo.employee_id;
        this.data.employeeAppointmentTypes = appointmentEmployeeInfo.appointment_types_info;
        return _super(...arguments);
    },
    /**
     * Modify some of the calendar options depending on the mode currently used
     * @override
     * @returns {Object}
     */
    _getFullCalendarOptions() {
        let options = this._super(...arguments);
        const format12Hour = {
            hour: 'numeric',
            minute: '2-digit',
            omitZeroMinute: true,
            meridiem: 'short'
        };
        const format24Hour = {
            hour: 'numeric',
            minute: '2-digit',
            hour12: false,
        };
        options.eventTimeFormat = time.getLangTimeFormat().search("HH") == 0 ? format24Hour : format12Hour;
        return options;
    },
});
