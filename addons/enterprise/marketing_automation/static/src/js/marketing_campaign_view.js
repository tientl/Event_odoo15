odoo.define('marketing_automation.CampaignFormView', function (require) {
'use strict';

var CampaignFormController = require('marketing_automation.CampaignFormController');
var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var CampaignFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: CampaignFormController,
        Renderer: FormRenderer,
    }),
});

viewRegistry.add('marketing_automation_campaign_form', CampaignFormView);

return CampaignFormView;

});
