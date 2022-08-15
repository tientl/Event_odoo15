odoo.define('appointment.select_appointment_type', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.appointmentTypeSelect = publicWidget.Widget.extend({
    selector: '.o_appointment_choice',
    events: {
        'change select[id="calendarType"]': '_onAppointmentTypeChange',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        // Check if we cannot replace this by a async handler once the related
        // task is merged in master
        this._onAppointmentTypeChange = _.debounce(this._onAppointmentTypeChange, 250);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * On appointment type change: adapt appointment intro text and available
     * employees (if option enabled)
     *
     * @override
     * @param {Event} ev
     */
    _onAppointmentTypeChange: function (ev) {
        var self = this;
        const appointmentTypeID = $(ev.target).val();
        this.$(".o_website_appointment_form").attr('action', `/calendar/${appointmentTypeID}/appointment`);
        this._rpc({
            route: `/calendar/${appointmentTypeID}/get_message_intro`,
        }).then(function (message_intro) {
            self.$('.o_calendar_intro').empty().append(message_intro);
        });
    },
});
});
