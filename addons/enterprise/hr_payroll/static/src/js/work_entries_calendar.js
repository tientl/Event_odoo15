odoo.define('hr_payroll.work_entries_calendar', function (require) {
    'use strict';

    var WorkEntryPayrollControllerMixin = require('hr_payroll.WorkEntryPayrollControllerMixin');
    var WorkEntryCalendarController = require("hr_work_entry_contract.work_entries_calendar");

    var WorkEntryPayrollCalendarController = WorkEntryCalendarController.include(WorkEntryPayrollControllerMixin);

    return WorkEntryPayrollCalendarController;

});
