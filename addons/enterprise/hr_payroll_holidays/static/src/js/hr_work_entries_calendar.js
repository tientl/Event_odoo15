odoo.define('hr_payroll_holidays.work_entries_calendar', function (require) {
    'use strict';

    var WorkEntryPayrollHolidaysControllerMixin = require('hr_payroll_holidays.WorkEntryPayrollHolidaysControllerMixin');
    var WorkEntryCalendarController = require("hr_work_entry_contract.work_entries_calendar");

    var WorkEntryPayrollHolidaysCalendarController = WorkEntryCalendarController.include(WorkEntryPayrollHolidaysControllerMixin);

    return WorkEntryPayrollHolidaysCalendarController;

});
