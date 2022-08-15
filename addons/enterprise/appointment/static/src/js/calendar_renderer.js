/** @odoo-module **/

import { qweb, _t } from 'web.core';
import { AttendeeCalendarRenderer } from 'calendar.CalendarRenderer';

AttendeeCalendarRenderer.include({
    events: Object.assign({}, AttendeeCalendarRenderer.prototype.events, {
        'click .o_appointment_appointment_link_clipboard': '_onClickAppointmentLink',
        'click .o_appointment_change_display': '_onChangeDisplay',
        'click .o_appointment_create_custom_appointment': '_onCreateCustomAppointment',
        'click .o_appointment_discard_slots': '_onDiscardSlots',
        'click .o_appointment_get_last_copy_link': '_onGetLastCopyLink',
        'click .o_appointment_search_create_work_hours_appointment': '_onSearchCreateWorkHoursAppointment',
        'click .o_appointment_select_slots': '_onSelectSlots',
    }),
    /**
     * Add the group of buttons where the users can create custom
     * appointment type and/or have a link to share.
     */
     _initSidebar() {
        this._super(...arguments);
        if (this.state.employeeId) {
            const appointments = this.state.employeeAppointmentTypes || [];
            this.$sidebar.prepend(qweb.render('Calendar.calendar_link_buttons', {
                appointments: appointments,
                work_hours_appointment: appointments.find(appointment => appointment.category == 'work_hours'),
                employee_id: this.state.employeeId,
            }));
        }
    },
    /**
     * Adapt the options of the calendar when we are in the
     * slot creation mode. For more details check each individual
     * functions
     * @override
     * @param {Object} fcOptions 
     * @returns {Object}
     */
    _getFullCalendarOptions(fcOptions) {
        let options = this._super(...arguments);

        // Event Listeners
        const oldEventClick = options.eventClick;
        const oldEventRender = options.eventRender;
        const oldYearDateClick = options.yearDateClick;
        const oldEventAllow = options.eventAllow;
        const oldSelectAllow = options.selectAllow;
        const oldSelect = options.select;
        const oldEventDrop = options.eventDrop;
        const oldEventResize = options.eventResize;
        const oldEventDragStart = options.eventDragStart;
        const oldEventResizeStart = options.eventResizeStart;
        const oldEventMouseEnter = options.eventMouseEnter;
        const oldEventMouseLeave = options.eventMouseLeave;

        // Display a message to the user letting him know he can't create a slot in the past
        options.dateClick = (ev) => {
            if (this.state.calendarMode === 'slots-creation' && moment(ev.date) < moment()) {
                this.displayNotification({
                    message: _t("You can not create a slot in the past."),
                    type: 'warning',
                });
            }
        };

        // Stop the propagation when we click on an event and if it's a slot we remove it
        options.eventClick = (eventClickInfo) => {
            if (this.state.calendarMode === 'default') {
                if (oldEventClick) {
                    oldEventClick.call(this.calendar, eventClickInfo);
                }
            } else {
                eventClickInfo.jsEvent.preventDefault();
                eventClickInfo.jsEvent.stopPropagation();
                if (eventClickInfo.event.extendedProps.slot) {
                    eventClickInfo.event.remove();
                    const hasSlots = this.calendar.getEvents().filter(ev => ev.extendedProps.slot).length;
                    if (!hasSlots) {
                        this.$sidebar.find('.o_appointment_create_custom_appointment').addClass('disabled');
                    }
                }
            }
        };

        // Add a button that will show onhover for slot events
        options.eventRender = (info) => {
            if (oldEventRender) {
                oldEventRender.call(this.calendar, info);
            }
            if (this.state.calendarMode === 'slots-creation') {
                let $element = $(info.el);
                if ($element.hasClass('o_calendar_slot')) {
                    const duration = (info.event.end - info.event.start) / 3600000;
                    const iconSize = (duration < 1 || info.event.allDay) || this.state.scale === 'month' ? '' : 'h1';
                    const $button = $('<button/>', {
                        class: 'close w-100 h-100 disabled o_hidden',
                        html: `<i class="fa fa-trash text-white m-0 ${iconSize}"/>`,
                    });
                    $element.find('.fc-bg').append($button);
                }
            }
        };

        // Manage the creation of a slot when using the year scale view
        options.yearDateClick = (info) => {
            if (this.state.calendarMode === 'slots-creation') {
                const alldaySlotEvents = this.calendar.getEvents().filter(ev => ev.extendedProps.slot && ev.allDay && ev.start.toString() === info.date.toString());
                const hasSlot = !!alldaySlotEvents.length;
                if (!hasSlot && info.selectable) {
                    if (moment(info.date).startOf('day') > moment()) {
                        this.calendar.addEvent({
                            title: `${moment(info.date).format('LL')}`,
                            start: info.date,
                            allDay: true,
                            color: 'green',
                            slot: true,
                            classNames: ['o_calendar_slot'],
                        });
                    } else {
                        this.displayNotification({
                            message: _t("You can not create a slot in the past."),
                            type: 'warning',
                        });
                    }
                } else if (hasSlot && info.selectable) {
                    alldaySlotEvents.forEach(event => event.remove());
                }
                this.calendar.unselect();
                this.$sidebar.find('.o_appointment_create_custom_appointment').removeClass('disabled');
            } else {
                if (oldYearDateClick) {
                    oldYearDateClick.call(this.calendar, info);
                }
            }
        };

        // Disable the drag and drop of event when in slot creation mode
        options.eventAllow = (dropInfo, draggedEvent) => {
            if (this.state.calendarMode === 'default') {
                if (oldEventAllow) {
                    return oldEventAllow.call(this.calendar, dropInfo, draggedEvent);
                }
                return true;
            } else {
                return !!draggedEvent.extendedProps.slot && moment(dropInfo.start) > moment();
            }   
        };

        // Like the others, we don't let the user create a slot in the past
        options.selectAllow = (event) => {
            let result = true
            if (oldEventAllow) {
                result = oldSelectAllow.call(this.calendar, event);
            }
            if (this.state.calendarMode === 'slots-creation') {
                result = result && moment(event.start) > moment();
            }
            return result;
        };

        // Manage the creation of a slot when the user select an area
        options.select = (selectionInfo) => {
            if (this.state.calendarMode === 'default') {
                if (oldSelect) {
                    return oldSelect.call(this.calendar, selectionInfo);
                }
            } else {
                const duration = (selectionInfo.end - selectionInfo.start) / (24 * 3600000);
                const title = (duration <= 1) ? moment(selectionInfo.start).format('LL') : `${moment(selectionInfo.start).format('LL')} to ${moment(selectionInfo.end).format('LL')}`;
                this.calendar.addEvent({
                    title: selectionInfo.allDay ? title : '',
                    start: selectionInfo.start,
                    end: selectionInfo.end,
                    allDay: selectionInfo.allDay,
                    color: 'green',
                    slot: true,
                    classNames: ['o_calendar_slot'],
                });
                this.calendar.unselect();
                this.$sidebar.find('.o_appointment_create_custom_appointment').removeClass('disabled');
            }
        };

        // Execute these only when in default mode
        options.eventDragStart = (mouseDragInfo) => {
            if (this.state.calendarMode === 'default') {
                if (oldEventDragStart) {
                    oldEventDragStart.call(this.calendar, mouseDragInfo);
                }
            }
        };
        options.eventResizeStart = (mouseResizeInfo) => {
            if (this.state.calendarMode === 'default') {
                oldEventResizeStart.call(this.calendar, mouseResizeInfo);
            }
        };
        options.eventResize = (eventResizeInfo) => {
            if (this.state.calendarMode === 'default') {
                oldEventResize.call(this.calendar, eventResizeInfo);
            }
        };
        options.eventDrop = (eventDropInfo) => {
            if (this.state.calendarMode === 'default') {
                oldEventDrop.call(this.calendar, eventDropInfo);
            }
        };

        // Show/hide the button on slot events
        options.eventMouseEnter = (mouseEnterInfo) => {
            if (this.state.calendarMode === 'default') {
                if (oldEventMouseEnter) {
                    oldEventMouseEnter.call(this.calendar, mouseEnterInfo);
                }
            } else {
                $(mouseEnterInfo.el).find('.fc-bg > button').removeClass('o_hidden');
            }
        };
        options.eventMouseLeave = (mouseLeaveInfo) => {
            if (this.state.calendarMode === 'default') {
                if (oldEventMouseLeave) {
                    oldEventMouseLeave.call(this.calendar, mouseLeaveInfo);
                }
            } else {
                $(mouseLeaveInfo.el).find('.fc-bg > button').addClass('o_hidden');
            }
        };
        return options;
    },
    /**
     * Used when clicking on an appointment link in the dropdown.
     * We display an info box to the user to let him know that the url was copied
     * and that it allows him to recopy it until he closes the box
     * @param {Event} ev 
     */
     _onClickAppointmentLink(ev) {
        ev.stopPropagation();
        this.trigger_up('appointment_link_clipboard', ev);
        this._onChangeDisplay(ev);
    },
    /**
     * Used when creating a custom appointment type.
     * Switch the calendar mode and display an info box to the user to let him know 
     * that the url was copied and that it allows him to recopy it until he closes the box
     * @param {Event} ev 
     */
    _onCreateCustomAppointment(ev) {
        if (!$(ev.currentTarget).hasClass("disabled")) {
            this.trigger_up('create_custom_appointment', ev);
            this._switchMode();
            this.$sidebar.find('.o_appointment_create_custom_appointment').addClass('disabled');
            this._onChangeDisplay(ev);
        }
    },
    /**
     * Used when clicking on the Work Hours appointment type in the dropdown.
     * We display an info box to the user to let him know that the url was copied
     * and that it allows him to recopy it until he closes the box
     * @param {Event} ev 
     */
     _onSearchCreateWorkHoursAppointment(ev) {
        ev.stopPropagation();
        this.trigger_up('search_create_work_hours_appointment_type', ev);
        this._onChangeDisplay(ev);
    },
    /**
     * Switch the calendar mode to slots-creation to create slots for
     * a custom appointment type
     * @param {Event} ev 
     */
    _onSelectSlots(ev) {
        this.trigger_up('set_slots_creation_mode', ev);
        this._switchMode();
    },
    /**
     * Discard the slots created in slots-creation mode and return to the default mode
     * @param {Event} ev 
     */
    _onDiscardSlots(ev) {
        this.trigger_up('slots_discard', ev);
        this._switchMode();
    },
    /**
     * Copy the last appointment URL and return to the original display (dropdown button)
     * @param {Event} ev 
     */
    _onGetLastCopyLink(ev) {
        ev.stopPropagation();
        this.trigger_up('appointment_get_copied_url', ev);
        this.$sidebar.find('.o_appointment_get_last_copy_link').tooltip('show');
        _.delay(() => {
            this.$sidebar.find('.o_appointment_get_last_copy_link').tooltip('hide');
        }, 800);
    },
    /**
     * Change the display to show the default dropdown button or the info message with buttons
     * @param {Event} ev 
     */
    _onChangeDisplay(ev) {
        this.$sidebar.find('.o_appointment_appointment_group_buttons').toggleClass('o_hidden');
        this.$sidebar.find('#copy_text').toggleClass('o_hidden');
        this.$sidebar.find('#scheduling_box').toggleClass('o_appointment_scheduling_message_box');
        this.$sidebar.find('.o_appointment_get_last_copy_link').toggleClass('o_hidden');
        this.$sidebar.find('.o_appointment_change_display').toggleClass('o_hidden');
    },
    /**
     * Switch the mode of the calendar
     * - default: default mode of the calendar
     * - slots-creation: mode to select slots in the calendar view for a custom appointment type
     * 
     * This allows to know the type of slots we create in the calendar view and adapt the behavior
     * of the calendar views in accordance.
     * 
     * We also adapt the design to display/hide the design necessary for the mode we are into.
     * 
     */
    _switchMode() {
        this.state.calendarMode = this.state.calendarMode === 'default' ? 'slots-creation' : 'default';
        this.$sidebar.find('.o_appointment_create_custom_appointment').toggleClass('o_hidden');
        this.$sidebar.find('.o_appointment_appointment_group_buttons').toggleClass('o_hidden');
        this.$sidebar.find('.o_appointment_discard_slots').toggleClass('o_hidden');
        this.$sidebar.find('#message_text').toggleClass('o_hidden');
        this.$sidebar.find('#scheduling_box').toggleClass('o_appointment_scheduling_message_box');
    },
    /**
     * Execute this only when in default mode. Allow to disable
     * the dblclick event on a calendar event when we are in slot
     * creation mode
     * @override
     * @param {Event} event 
     */
    _onEditEvent(event) {
        if (this.state.calendarMode === 'default') {
            this._super(...arguments);
        }
    },
});
