/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('planning_test_tour', {
    url: '/web',
    test: true,
}, [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Let's start managing your employees' schedule!",
    position: 'bottom',
}, {
    trigger: ".o_gantt_button_add",
    content: "Let's create your first <b>shift</b> by clicking on Add. <i>Tip: use the (+) shortcut available on each cell of the Gantt view to save time.</i>",
}, {
    trigger: ".o_field_widget[name='resource_id']",
    content: "Assign this shift to your <b>resource</b>, or leave it open for the moment.",
}, {
    trigger: ".o_field_widget[name='role_id']",
    content: "Select the <b>role</b> your employee will have (<i>e.g. Chef, Bartender, Waiter, etc.</i>).",
}, {
    trigger: ".o_field_widget[name='start_datetime']",
    content: "Set start datetime",
    run: function (actions) {
        this.$anchor.val(this.$anchor.val().replace(/(\d{2}:){2}\d{2}/g, '08:00:00'));
        this.$anchor.trigger("change");
    }
}, {
    trigger: ".o_field_widget[name='end_datetime']",
    content: "Set end datetime",
    run: function (actions) {
        this.$anchor.val(this.$anchor.val().replace(/(\d{2}:){2}\d{2}/g, '11:59:59'));
        this.$anchor.trigger("change");
    }
}, {
    trigger: "button[special='save']",
    content: "Save this shift once it is ready.",
}, {
    trigger: ".o_gantt_pill :contains('11:59 AM')",
    content: "<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period.",
    run: function () {
        if (this.$anchor.length) {
            const expected = "8:00 AM - 11:59 AM (4h)";
            const actual = this.$anchor[0].textContent;
            if (!actual.startsWith(expected)) {
                console.error("Test in gantt view doesn't start as expected. Expected : '" + expected + "', actual : '" + actual + "'");
            }
        } else {
            console.error("Not able to select pill ending at 11h59");
        }
    }
}, {
    trigger: ".o_gantt_button_send_all",
    content: "If you are happy with your planning, you can now <b>send</b> it to your employees.",
}, {
    trigger: "button[name='action_send']",
    content: "<b>Publish & send</b> your planning to make it available to your employees.",
}, {
    trigger: ".o_gantt_progressbar",
    content: "See employee progress bar",
    run: function () {
        const $progressbar = $(".o_gantt_progressbar:eq(0)");
        if ($progressbar.length) {
            if ($progressbar[0].style.width === '') {
                console.error("Progress bar should be displayed");
            }
            if (!$progressbar[0].classList.contains("o_gantt_group_success")) {
                console.error("Progress bar should be displayed in success");
            }
        } else {
            console.error("Not able to select progressbar");
        }
    }
}]);
