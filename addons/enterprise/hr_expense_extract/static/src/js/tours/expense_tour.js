odoo.define('hr_expense_extract.tour', function(require) {
    "use strict";
    
    var core = require('web.core');
    var tour = require('web_tour.tour');
    
    var _t = core._t;
    
    tour.register('hr_expense_extract_tour' , {
        url: "/web",
        rainbowMan: true,
        rainbowManMessage: "<b>Congratulations</b>, you are now an expert of Expenses.",
        sequence: 42,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
        content: _t("Wasting time recording your receipts? Let’s try a better way."),
        position: 'bottom',
    }, {
        trigger: '.o_nocontent_help a.btn-primary',
        content: _t("Try the AI with a sample receipt."),
        position: 'bottom',
        width: 200,
    }, {
        trigger: ".o_expense_flex",
        content: _t("Choose a receipt."),
        position: 'top',
        width: 120,
    }, {
        trigger: "button[name='action_submit_expenses']",
        content: _t("Report this expense to your manager for validation."),
        position: 'bottom',
    }, {
        trigger: '.o_menu_header_lvl_1[data-menu-xmlid="hr_expense.menu_hr_expense_report"]',
        extra_trigger: '.o_form_button_edit',
        content: _t("Your manager will have to approve (or refuse) your expense reports."),
        position: 'bottom',
    }, {
        trigger: '.o_menu_entry_lvl_2[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_all_to_approve"]',
        extra_trigger: '.o_form_button_edit',
        content: _t("Your manager will have to approve (or refuse) your expense reports."),
        position: 'bottom',
    }]);
    
    });
    