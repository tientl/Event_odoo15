/** @odoo-module **/

import { _t } from 'web.core';
import { browser } from "@web/core/browser/browser";
import field_utils from "web.field_utils";
import CalendarController from 'calendar.CalendarController';

const legacy = {
    field_utils,
};

CalendarController.include({
    custom_events: Object.assign({}, CalendarController.prototype.custom_events, {
        'appointment_get_copied_url': '_onCopyLastAppointmentURL',
        'appointment_link_clipboard': '_onClickAppointmentLink',
        'create_custom_appointment': '_onCreateCustomAppointment',
        'search_create_work_hours_appointment_type': '_onSearchCreateWorkHoursAppointment',
        'slots_discard': '_onDiscardSlots',
        'set_slots_creation_mode': '_setModeToSlotsCreation',
    }),
    /**
     * Save in the clipboard in the URL of the appointment type selected
     * @param {Event} ev 
     */
     _onClickAppointmentLink(ev) {
        const $currentTarget = $(ev.data.currentTarget);
        const appointmentURL = window.encodeURI(`${this.getSession()['web.base.url']}${$currentTarget.attr('data-url')}`);
        browser.navigator.clipboard.writeText(appointmentURL);
        this.lastAppointmentURL = appointmentURL;
    },
    /**
     * Copy in the clipboard the last appointment URL
     * @param {Event} ev 
     */
     _onCopyLastAppointmentURL(ev) {
        browser.navigator.clipboard.writeText(this.lastAppointmentURL);
    },
    /**
     * Create a custom appointment type and fill the slots with the ones
     * created on the calendar view.
     * The URL of the new appointment type is then saved in the clipboard.
     * @param {Event} ev 
     */
    async _onCreateCustomAppointment(ev) {
        const events = this.renderer.calendar.getEvents();
        const slotEvents = events.filter(event => event.extendedProps.slot);
        const slots = slotEvents.map(slot => {
            return {
                start: legacy.field_utils.parse.datetime(slot.start).toJSON(),
                end: (
                    slot.end ? legacy.field_utils.parse.datetime(slot.end) : legacy.field_utils.parse.datetime(moment(slot.start).add(1, 'days'))
                ).toJSON(),
                allday: slot.allDay,
            };
        });
        if (slots.length) {
            slotEvents.forEach(event => event.remove());
            const customAppointment = await this._rpc({
                route: '/appointment/calendar_appointment_type/create_custom',
                params: {
                    slots: slots,
                },
            });
            if (customAppointment.id) {
                browser.navigator.clipboard.writeText(customAppointment.url);
                this.lastAppointmentURL = customAppointment.url;
            }
        }
        this.model.setCalendarMode('default');
    },
    /**
     * Discard the slots created in the calendar view and reset the calendar to the
     * default mode.
     * @param {Event} ev 
     */
     _onDiscardSlots(ev) {
        const events = this.renderer.calendar.getEvents();
        const slotEvents = events.filter(event => event.extendedProps.slot);
        slotEvents.forEach(event => event.remove());
        this.model.setCalendarMode('default');
    },
    /**
     * Search/create the work hours appointment type of the user when
     * he clicks on the button "Work Hours".
     * @param {Event} ev 
     */
     async _onSearchCreateWorkHoursAppointment(ev) {
        const workHoursAppointment = await this._rpc({
            route: '/appointment/calendar_appointment_type/search_create_work_hours',
        });
        if (workHoursAppointment.id) {
            browser.navigator.clipboard.writeText(workHoursAppointment.url);
            this.lastAppointmentURL = workHoursAppointment.url;
        }
    },
    /**
     * Update the mode of the calendar to slots-creation
     * (mode to select slots in the calendar view for a custom appointment type)
     * @param {Event} ev
     */
    _setModeToSlotsCreation(ev) {
        this.model.setCalendarMode('slots-creation');
    },
});
