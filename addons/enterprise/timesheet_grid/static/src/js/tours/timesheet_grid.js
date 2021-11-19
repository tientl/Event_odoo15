"use strict";
odoo.define('timesheet.tour', function(require) {

var core = require('web.core');
const {Markup} = require('web.utils');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('timesheet_tour', {
    sequence: 100,
    rainbowManMessage: _t("Congratulations, you are now a master of Timesheets.</b> <i>Psst: try the  [a] - [Enter] - [b] - [Enter] - shift + [A]  sequence on your keyboard and see what happens next!</i>"),
    url: "/web",
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="hr_timesheet.timesheet_menu_root"]',
    content: Markup(_t('Track the <b>time spent</b> on your projects. <i>It starts here.</i>')),
    position: 'bottom',
}, {
    trigger: '.btn_start_timer',
    content: Markup(_t('Launch the <b>timer</b> to start a new activity.')),
    position: 'bottom',
}, {
    trigger: '.input_description_timer',
    content: Markup(_t('Describe your activity <i>(e.g. sent an e-mail, meeting with the customer...)</i>.')),
    position: 'bottom',
}, {
    trigger: '.timer_project_id .o_field_many2one',
    content: Markup(_t('Select the <b>project</b> on which you are working.')),
    position: 'bottom',
}, {
    trigger: '.btn_stop_timer',
    content: Markup(_t('Stop the <b>timer</b> when you are done. <i>Tip: hit <b>[Enter]</b> from the description to automatically log your entry.</i>')),
    position: 'bottom',
}, {
    trigger: '.btn_timer_line',
    content: Markup(_t('Launch the <b>timer</b> for this project by hitting the <b>[a] key</b>. You can easily switch from one project to another using those keys. <i>Tip: you can also directly add 15 minutes to this project by hitting the <b>shift + [A] keys</b>.</i>')),
    position: 'right',
}, {
    trigger: 'td:not(.o_grid_unavailable)',
    content: Markup(_t('Set the number of hours you spent on this project (e.g. 1:30 or 1.5). <i>Tip: use the tab keys to easily navigate from one cell to another.</i>')),
    position: 'bottom',
    consumeEvent: 'change',
}]);

});
