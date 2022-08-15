odoo.define("industry_fsm_report.tour", function (require) {
"use strict";
/**
 * Add custom steps to take worksheets into account
 */
var tour = require('web_tour.tour');
    require('industry_fsm.tour');
var core = require('web.core');
const {Markup} = require('web.utils');
var _t = core._t;

var fsmStartStepIndex = _.findIndex(tour.tours.industry_fsm_tour.steps, function (step) {
    return (step.id === 'fsm_start');
});

tour.tours.industry_fsm_tour.steps.splice(fsmStartStepIndex + 1, 0, {
    trigger: 'button[name="action_fsm_worksheet"]',
    extra_trigger: 'button[name="action_timer_stop"]',
    content: _t('Fill in your <b>worksheet</b> with the details of your intervention.'),
    position: 'bottom',
}, {
    trigger: ".o_form_button_save",
    content: Markup(_t('Save your <b>worksheet</b> once it is complete.<br/><i>Tip: customize this form to your needs and create as many templates as you want.</i>')),
    extra_trigger: '.o_form_view',
    position: 'bottom'
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_form_view',
    content: Markup(_t("Use the breadcrumbs to go back to your <b>task</b>.")),
    position: 'bottom'

});

var fsmSaveTimesheetStepIndex = _.findIndex(tour.tours.industry_fsm_tour.steps, function (step) {
    return (step.id === 'fsm_save_timesheet');
});

tour.tours.industry_fsm_tour.steps.splice(fsmSaveTimesheetStepIndex + 1, 0, {
    trigger: 'button[name="action_preview_worksheet"]',
    extra_trigger: '.o_form_project_tasks',
    content: _t('<b>Review and sign</b> your <b>worksheet report</b> with your customer.'),
    position: 'bottom',
}, {
    trigger: 'a[data-target="#modalaccept"]',
    extra_trigger: 'div[id="o_fsm_worksheet_portal"]',
    content: _t('Invite your customer to <b>validate and sign your worksheet report</b>.'),
    position: 'right',
}, {
    trigger: '.o_web_sign_auto_button',
    extra_trigger: 'div[id="o_fsm_worksheet_portal"]',
    content: _t('Save time by generating a <b>signature</b> automatically.'),
    position: 'right',
}, {
    trigger: '.o_portal_sign_submit:enabled',
    extra_trigger: 'div[id="o_fsm_worksheet_portal"]',
    content: _t('Validate the <b>signature</b>.'),
    position: 'left',
}, {
    trigger: 'a:contains(Back to edit mode)',
    extra_trigger: 'div[id="o_fsm_worksheet_portal"]',
    content: _t('Go back to your Field Service <b>task</b>.'),
    position: 'right',
}, {
    trigger: 'button[name="action_send_report"]',
    extra_trigger: '.o_form_project_tasks ',
    content: _t('<b>Send your worksheet report</b> to your customer.'),
    position: 'bottom',
}, {
    trigger: 'button[name="action_send_mail"]',
    extra_trigger: '.o_form_project_tasks ',
    content: _t('<b>Send your worksheet report</b> to your customer.'),
    position: 'right',
});

});
