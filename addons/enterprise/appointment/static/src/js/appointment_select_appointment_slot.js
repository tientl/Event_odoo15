odoo.define('appointment.select_appointment_slot', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var qweb = core.qweb;

publicWidget.registry.appointmentSlotSelect = publicWidget.Widget.extend({
    selector: '.o_appointment',
    xmlDependencies: ['/appointment/static/src/xml/calendar_appointment_slots.xml'],
    events: {
        'change select[name="timezone"]': '_onRefresh',
        'change select[id="selectEmployee"]': '_onRefresh',
        'click .o_js_calendar_navigate': '_onCalendarNavigate',
        'click .o_day': '_onClickDaySlot',
    },

    /**
     * Navigate between the months available in the calendar displayed
     */
    _onCalendarNavigate: function (ev) {
        var parent = this.$('.o_appointment_month:not(.d-none)');
        let monthID = parseInt(parent.attr('id').split('-')[1]);
        monthID += ((this.$(ev.currentTarget).attr('id') === 'nextCal') ? 1 : -1);
        parent.addClass('d-none');
        this.$(`div#month-${monthID}`).removeClass('d-none');
    },

    /**
     * Display the list of slots available for the date selected
     */
    _onClickDaySlot: function (ev) {
        this.$('.o_slot_selected').removeClass('o_slot_selected');
        this.$(ev.currentTarget).addClass('o_slot_selected');

        const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
        const appointmentTypeIDs = this.$("input[name='filter_appointment_type_ids']").val();
        const slotDate = this.$(ev.currentTarget.firstElementChild).attr('id');
        const slots = JSON.parse(this.$(ev.currentTarget).find('div')[0].dataset['availableSlots']);

        let $slotsList = this.$('#slotsList').empty();
        $(qweb.render('appointment.slots_list', {
            slotDate: moment(slotDate).format("dddd D MMMM"),
            slots: slots,
            appointment_type_id: appointmentTypeID,
            filter_appointment_type_ids: appointmentTypeIDs,
        })).appendTo($slotsList);
    },

    /**
     * Refresh the slots info when the user modify the timezone or the employee
     */
    _onRefresh: function (ev) {
        if (this.$("#slots_availabilities")[0]) {
            var self = this;
            const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
            const employeeID = this.$("#slots_form select[name='employee_id']").val();
            const timezone = this.$("select[name='timezone']").val();
            this._rpc({
                route: `/calendar/${appointmentTypeID}/update_available_slots`,
                params: {
                    employee_id: employeeID,
                    timezone: timezone,
                },
            }).then(function (data) {
                if (data) {
                    self.$("#slots_availabilities").replaceWith(data);
                }
            });
        }
    },
});
});
