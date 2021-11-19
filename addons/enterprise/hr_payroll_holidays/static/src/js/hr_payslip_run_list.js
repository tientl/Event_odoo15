odoo.define('hr_payroll_holidays.payslip.run.tree', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var WorkEntryPayrollHolidaysControllerMixin = require('hr_payroll_holidays.WorkEntryPayrollHolidaysControllerMixin');

    var QWeb = core.qweb;
    var PayslipRunController = ListController.extend(_.extend({}, WorkEntryPayrollHolidaysControllerMixin, {
        _displayWarning: function ($warning) {
            this.$('.o_list_view').before($warning);
        },
    }));

    var PayslipRunListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: PayslipRunController,
        }),
    });

    viewRegistry.add('hr_payslip_run_tree', PayslipRunListView);

    return PayslipRunController;
});
