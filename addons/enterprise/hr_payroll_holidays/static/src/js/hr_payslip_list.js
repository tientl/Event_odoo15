odoo.define('hr_payroll_holidays.payslip.tree', function (require) {
"use strict";
    var core = require('web.core');

    var PayslipListController = require("hr_payroll.payslip.tree");
    var QWeb = core.qweb;
    var WorkEntryPayrollHolidaysControllerMixin = require('hr_payroll_holidays.WorkEntryPayrollHolidaysControllerMixin');

    var PayslipHolidaysListController = PayslipListController.include(_.extend({}, WorkEntryPayrollHolidaysControllerMixin, {
        _displayWarning: function ($warning) {
            this.$('.o_list_view').before($warning);
        },
    }));

    return PayslipHolidaysListController;
});
