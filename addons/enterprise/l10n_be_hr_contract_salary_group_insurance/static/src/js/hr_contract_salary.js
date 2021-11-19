odoo.define('l10n_be_hr_contract_salary_group_insurance', function (require) {
"use strict";

const hrContractSalary = require('hr_contract_salary');

hrContractSalary.include({
    events: _.extend({}, hrContractSalary.prototype.events, {
        "change input[name='l10n_be_has_ambulatory_insurance_radio']": "onchangeAmbulatory",
    }),

    start: async function () {
        const res = await this._super(...arguments);
        this.onchangeAmbulatory();
        // YTI TODO: There is probably a way to remove this crap
        $("input[name='l10n_be_ambulatory_insured_children']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insured_adults']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insured_spouse']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insured_children_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children < 19'
        }));
        $("input[name='l10n_be_ambulatory_insured_adults_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children >= 19'
        }));
        return res;
    },

    onchangeAmbulatory: function() {
        const hasInsurance = $("input[name='l10n_be_has_ambulatory_insurance_radio']:last").prop('checked');
        if (hasInsurance) {
            // Show fields
            $("label[for='l10n_be_ambulatory_insured_children']").parent().removeClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_adults']").parent().removeClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_spouse']").parent().removeClass('d-none');
        } else {
            // Reset values
            $("input[name='fold_l10n_be_ambulatory_insured_spouse']").prop('checked', false);
            $("input[name='l10n_be_ambulatory_insured_children_manual']").val(0);
            $("input[name='l10n_be_ambulatory_insured_adults_manual']").val(0);
            // Hide fields
            $("label[for='l10n_be_ambulatory_insured_children']").parent().addClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_adults']").parent().addClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_spouse']").parent().addClass('d-none');
        }
    },
});

});
