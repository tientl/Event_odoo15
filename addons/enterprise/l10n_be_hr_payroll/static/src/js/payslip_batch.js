odoo.define('hr_payroll.payslip.run.tree', function (require) {
"use strict";
    var core = require('web.core');
    var PayslipRunPayrollHolidaysControllerMixin = require('hr_payroll_holidays.payslip.run.tree');

    var QWeb = core.qweb;

    var PayslipBatchListController = PayslipRunPayrollHolidaysControllerMixin.include({
        /**
         * Extends the renderButtons function of ListView by adding a button
         * on the payslip batch list.
         *
         * @override
         */
        renderButtons: function () {
            var self = this;
            this._super.apply(this, arguments);
            this.$buttons.append($(QWeb.render("PayslipBatchListView.generate_warrant_payslips", this)));
            this.$buttons.on('click', '.o_button_generate_warrant_payslips', function () {
                self.do_action('l10n_be_hr_payroll.action_hr_payroll_generate_warrant_payslips');
            });
        }
    });
});
