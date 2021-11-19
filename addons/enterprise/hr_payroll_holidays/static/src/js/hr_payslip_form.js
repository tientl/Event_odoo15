odoo.define('hr_payroll_holidays.payslip.form', function (require) {
"use strict";
    var core = require('web.core');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var WorkEntryPayrollHolidaysControllerMixin = require('hr_payroll_holidays.WorkEntryPayrollHolidaysControllerMixin');

    var QWeb = core.qweb;

    var PayslipFormController = FormController.extend(WorkEntryPayrollHolidaysControllerMixin, {
        _displayWarning: function ($warning) {
            this.$('.o_form_statusbar').after($warning);
        },
    });

    var PayslipFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: PayslipFormController,
        }),
    });

    viewRegistry.add('hr_payslip_form', PayslipFormView);

    return PayslipFormController;
});
