odoo.define('l10n_be_hr_contract_salary', function (require) {
"use strict";

const hrContractSalary = require('hr_contract_salary');

hrContractSalary.include({
    events: _.extend({}, hrContractSalary.prototype.events, {
        "change input[name='has_hospital_insurance_radio']": "onchangeHospital",
        "change input[name='fold_company_car_total_depreciated_cost']": "onchangeCompanyCar",
        "change input[name='fold_private_car_reimbursed_amount']": "onchangePrivateCar",
    }),

    updateGrossToNetModal(data) {
        this._super(data);
        $("input[name='double_holiday_wage']").val(data['double_holiday_wage']);
    },

    onchangeCompanyCar: function(event) {
        var private_car_input = $("input[name='fold_private_car_reimbursed_amount']")
        if (event.target.checked && private_car_input[0].checked) {
            private_car_input.click()
        }
    },

    onchangePrivateCar: function(event) {
        var company_car_input = $("input[name='fold_company_car_total_depreciated_cost']")
        if (event.target.checked && company_car_input[0].checked) {
            company_car_input.click()
        }
    },

    onchange_mobility: function() {
        this._super.apply(this, arguments);
        var fuel_card_div = $("div[name='fuel_card']");
        // Don't hide the fuel card if no car is chosen
        fuel_card_div.removeClass("hidden");
    },

    start: async function () {
        const res = await this._super(...arguments);
        this.onchangeHospital();
        // YTI TODO: There is probably a way to remove this crap
        $("input[name='insured_relative_children']").parent().addClass('d-none');
        $("input[name='insured_relative_adults']").parent().addClass('d-none');
        $("input[name='insured_relative_spouse']").parent().addClass('d-none');
        $("input[name='insured_relative_children_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children < 19'
        }));
        $("input[name='insured_relative_adults_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children >= 19'
        }));
        return res;
    },

    onchangeHospital: function() {
        const hasInsurance = $("input[name='has_hospital_insurance_radio']:last").prop('checked');
        if (hasInsurance) {
            // Show fields
            $("label[for='insured_relative_children']").parent().removeClass('d-none');
            $("label[for='insured_relative_adults']").parent().removeClass('d-none');
            $("label[for='insured_relative_spouse']").parent().removeClass('d-none');
        } else {
            // Reset values
            $("input[name='fold_insured_relative_spouse']").prop('checked', false);
            $("input[name='insured_relative_children_manual']").val(0);
            $("input[name='insured_relative_adults_manual']").val(0);
            // Hide fields
            $("label[for='insured_relative_children']").parent().addClass('d-none');
            $("label[for='insured_relative_adults']").parent().addClass('d-none');
            $("label[for='insured_relative_spouse']").parent().addClass('d-none');
        }
    },
});

});
