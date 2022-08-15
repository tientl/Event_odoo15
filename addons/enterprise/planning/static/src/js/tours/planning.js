odoo.define('planning.tour', function (require) {
    "use strict";

    var core = require('web.core');
    var tour = require('web_tour.tour');

    var _t = core._t;

    tour.register('planning_tour', {
        sequence: 120,
        'skip_enabled': false,
	url: '/web',
    }, [{
        trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
        content: _t("Let's start managing your employees' schedule!"),
        position: 'bottom',
    }, {
        trigger: ".o_gantt_button_add",
        content: _t("Let's create your first <b>shift</b> by clicking on Add. <i>Tip: use the (+) shortcut available on each cell of the Gantt view to save time.</i>"),
        position: "bottom",
    }, {
        trigger: ".o_field_widget[name='resource_id']",
        content: _t("Assign this shift to your <b>resource</b>, or leave it open for the moment."),
        position: "bottom",
    }, {
        trigger: ".o_field_widget[name='role_id']",
        content: _t("Select the <b>role</b> your employee will have (<i>e.g. Chef, Bartender, Waiter, etc.</i>)."),
        position: "bottom",
    }, {
        trigger: "button[special='save']",
        content: _t("Save this shift once it is ready."),
        position: "bottom",
    }, {
        trigger: ".o_gantt_pill:not(.o_gantt_consolidated_pill)",
        content: _t("<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period."),
        position: "bottom",
    }, {
        trigger: ".o_gantt_button_send_all",
        content: _t("If you are happy with your planning, you can now <b>send</b> it to your employees."),
        position: "bottom",
    },{
        trigger: "button[name='action_send']",
        content: _t("<b>Publish & send</b> your planning to make it available to your employees."),
        position: "bottom",
    },
    ]);
});
