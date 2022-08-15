odoo.define('marketing_automation.CampaignFormController', function (require) {
'use strict';

var FormController = require('web.FormController');

var CampaignFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        save_form_before_new_activity: '_saveFormBeforeNewActivity',
    }),

    _saveFormBeforeNewActivity: function (ev) {
        this.saveRecord(null, {
            stayInEdit: true,
            reload: true,
        }).then(function () {
            if (ev.data.callback)
                ev.data.callback();
        })
    }
});

return CampaignFormController;

});
