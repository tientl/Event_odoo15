odoo.define('l10n_be_hr_payroll_canteen', function (require) {
"use strict";

var SalaryPackageWidget = require("hr_contract_salary");
var core = require('web.core');

var qweb = core.qweb;

SalaryPackageWidget.include({
    getAdvantages() {
        var res = this._super.apply(this, arguments);
        res.contract.l10n_be_canteen_cost = parseFloat($("input[name='l10n_be_canteen_cost']").val() || "0.0");
        return res
    },
});
});
