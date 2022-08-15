odoo.define('industry_fsm.tour', function (require) {
"use strict";

var core = require('web.core');
const {Markup} = require('web.utils');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('industry_fsm_tour', {
    sequence: 90,
    url: "/web",
}, [{
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: Markup(_t('Ready to <b>manage your onsite interventions</b>? <i>Click Field Service to start.</i>')),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_fsm_kanban',
    content: _t('Let\'s create your first <b>task</b>.'),
    position: 'bottom',
}, {
    trigger: 'input.o_task_name',
    extra_trigger: '.o_form_editable',
    content: Markup(_t('Add a <b>title</b> <i>(e.g. Boiler maintenance, Air-conditioning installation, etc.).</i>')),
    position: 'right',
    width: 200,
}, {
    trigger: ".o_form_view .o_task_customer_field",
    extra_trigger: '.o_form_project_tasks.o_form_editable',
    content: _t('Select the <b>customer</b> of your task.'),
    position: "bottom",
    run: function (actions) {
        actions.text("Brandon Freeman", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-autocomplete > li > a",
    auto: true,
}, {
    content: "Save the task",
    trigger: 'button.o_form_button_save',
}, {
    trigger: 'button.o_form_button_edit',
    content: 'Go back to edit mode',
    run: function(){},
}, {
    trigger: 'button[name="action_timer_start"]',
    extra_trigger: '.o_form_project_tasks',
    content: _t('Launch the timer to <b>track the time spent</b> on your task.'),
    position: "bottom",
    id: 'fsm_start',
}, {
    trigger: 'button[name="action_timer_stop"]',
    content: _t('Stop the <b>timer</b> when you are done.'),
    position: 'bottom',
}, {
    trigger: 'button[name="save_timesheet"]',
    content: Markup(_t('Confirm the <b>time spent</b> on your task. <i>Tip: a rounding of 15min has automatically been applied.</i>')),
    position: 'bottom',
    id: 'fsm_save_timesheet',
}, {
    trigger: "button[name='action_fsm_validate']",
    extra_trigger: '.o_form_project_tasks',
    content: _t('Let\'s <b>mark your task as done!</b> <i>Tip: when doing so, your stock will automatically be updated, and your task will move to the next stage.</i>'),
    position: 'bottom',
    id: 'fsm_invoice_create',
}]);

});
