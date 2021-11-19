odoo.define('timesheet_grid.timesheet_tests', function (require) {
    "use strict";

    const TimesheetGridView = require('timesheet_grid.GridView');
    const testUtils = require('web.test_utils');
    const createView = testUtils.createView;

    QUnit.module('Views', {
        beforeEach: function () {
            this.data = {
                'analytic.line': {
                    fields: {
                        project_id: {string: "Project", type: "many2one", relation: "project.project"},
                        task_id: {string: "Task", type: "many2one", relation: "project.task"},
                        employee_id: {string: "Employee", type: "many2one", relation: "hr.employee"},
                        date: {string: "Date", type: "date"},
                        unit_amount: {string: "Unit Amount", type: "float"},
                    },
                    records: [
                        {id: 1, project_id: 31, employee_id: 7, date: "2017-01-24", unit_amount: 2.5},
                        {id: 2, project_id: 31, task_id: 1, employee_id: 11, date: "2017-01-25", unit_amount: 2},
                        {id: 3, project_id: 31, task_id: 1, employee_id: 23, date: "2017-01-25", unit_amount: 5.5},
                        {id: 4, project_id: 142, task_id: 54, employee_id: 11, date: "2017-01-27", unit_amount: 10},
                        {id: 5, project_id: 142, task_id: 12, employee_id: 7, date: "2017-01-27", unit_amount: -3.5},
                        {id: 6, project_id: 142, task_id: 1, employee_id: 12, date: "2017-01-26", unit_amount: 4},
                    ]
                },
                'project.project': {
                    fields: {},
                    records: [
                        {id: 31, display_name: "P1"},
                        {id: 142, display_name: "Webocalypse Now"},
                    ]
                },
                'project.task': {
                    fields: {
                        project_id: {string: "Project", type: "many2one", relation: "project.project"},
                    },
                    records: [
                        {id: 1, display_name: "BS task", project_id: 31},
                        {id: 12, display_name: "Another BS task", project_id: 142},
                        {id: 54, display_name: "yet another task", project_id: 142},
                    ]
                },
                'hr.employee': {
                    fields: {},
                    records: [{
                        id: 11,
                        name: "Mario",
                    }, {
                        id: 7,
                        name: "Luigi",
                    }, {
                        id: 23,
                        name: "Yoshi",
                    }, {
                        id: 12,
                        name: "Toad",
                    }],
                    get_timesheet_and_working_hours_for_employees(args) {
                        const employeeIds = [...new Set(args[0].map(item => item.employee_id))];
                        const result = {};
                        employeeIds.forEach(employeeId => {

                            // Employee 11 hasn't done all his hours
                            if (employeeId === 11) {
                                result[employeeId] = {
                                    'units_to_work': 987,
                                    'uom': 'hours',
                                    'worked_hours': 789
                                };
                            }

                            // Employee 7 has done all his hours
                            else if (employeeId === 7) {
                                result[employeeId] = {
                                    'units_to_work': 654,
                                    'uom': 'hours',
                                    'worked_hours': 654
                                };
                            }

                            else if (employeeId === 12) {
                                result[employeeId] = {
                                    'units_to_work': 21,
                                    'uom': 'days',
                                    'worked_hours': 20,
                                };
                            }

                            // The others have done too much hours (overtime)
                            else {
                                result[employeeId] = {
                                    'units_to_work': 6,
                                    'uom': 'hours',
                                    'worked_hours': 10
                                };
                            }

                        });
                        return result;
                    }
                },
            };
            this.arch = '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                        '<field name="employee_id" type="row"/>' +
                        '<field name="project_id" type="row"/>' +
                        '<field name="task_id" type="row"/>' +
                        '<field name="date" type="col">' +
                            '<range name="week" string="Week" span="week" step="day"/>' +
                            '<range name="month" string="Month" span="month" step="day" invisible="context.get(\'hide_second_button\')"/>' +
                            '<range name="year" string="Year" span="year" step="month"/>' +
                        '</field>' +
                        '<field name="unit_amount" type="measure" widget="float_time"/>' +
                        '<button string="Action" type="action" name="action_name"/>' +
                    '</grid>';
        }
    }, function () {
        QUnit.module('TimesheetGridView');

        QUnit.test('basic timesheet - no groupby', async function (assert) {
            assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
            });

            assert.containsN(grid, '.o_standalone_avatar_employee', 6,
                'should have 6 employee avatars');

            assert.containsN(grid, '.o_grid_section_subtext', 6,
                'should have 6 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('basic timesheet - groupby employees', async function (assert) {
            assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
                groupBy: ['employee_id'],
            });

            assert.containsN(grid, '.o_standalone_avatar_employee', 4,
                'should have 4 employee avatars');

                 assert.containsN(grid, '.o_grid_section_subtext', 4,
                'should have 4 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('basic timesheet - groupby employees>task', async function (assert) {
            assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
                groupBy: ['employee_id', 'task_id'],
            });

            assert.containsN(grid, '.o_standalone_avatar_employee', 6,
                'should have 6 employee avatars');

            assert.containsN(grid, '.o_grid_section_subtext', 6,
                'should have 6 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('basic timesheet - groupby task>employees', async function (assert) {
            assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
                groupBy: ['task_id', 'employee_id'],
            });

            assert.containsN(grid, '.o_standalone_avatar_employee', 6,
                'should have 6 employee avatars');

            assert.containsN(grid, '.o_grid_section_subtext', 6,
                'should have 6 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('timesheet with employee section - no groupby', async function (assert) {
            assert.expect(2);

            this.arch = this.arch.replace(
                '<field name="employee_id" type="row"/>',
                '<field name="employee_id" type="row" section="1"/>'
            );

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
            });

            assert.containsN(grid, '.o_grid_section > tr > th > .o_standalone_avatar_employee', 4,
                'should have 4 employee avatars');

            assert.containsN(grid, '.o_grid_section_subtext', 4,
                'should have 4 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('timesheet with employee section - groupby employee>task', async function (assert) {
            assert.expect(2);

            this.arch = this.arch.replace(
                '<field name="employee_id" type="row"/>',
                '<field name="employee_id" type="row" section="1"/>'
            );

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
                groupBy: ['employee_id', 'task_id'],
            });

            assert.containsN(grid, '.o_grid_section > tr > th > .o_standalone_avatar_employee', 4,
                'should have 4 employee avatars');

            assert.containsN(grid, '.o_grid_section_subtext', 4,
                'should have 4 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('timesheet with employee section - groupby task>employee', async function (assert) {
            assert.expect(2);

            this.arch = this.arch.replace(
                '<field name="employee_id" type="row"/>',
                '<field name="employee_id" type="row" section="1"/>'
            );

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
                groupBy: ['task_id', 'employee_id'],
            });

            assert.containsN(grid, '.o_standalone_avatar_employee', 6,
                'should have 6 employee avatars');

            assert.containsN(grid, '.o_grid_section_subtext', 6,
                'should have 6 timesheet employee avatars');

            grid.destroy();
        });

        QUnit.test('timesheet avatar widget should display hours in gray if in the view show the current period', async function(assert) {

           assert.expect(1);

            const unPatchDate = await testUtils.mock.patchDate(2017, 0, 25, 14, 0, 0);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
            });


            const numberOfAvatarWidget = grid.$('.o_standalone_avatar_employee').length;
            const numberOfTimesheetHoursAvatarWidgetWithoutHoursRedAlert = grid.$('.o_grid_section_subtext:not(.o_grid_section_subtext_not_enough_hours)').length;

            assert.ok(numberOfAvatarWidget === numberOfTimesheetHoursAvatarWidgetWithoutHoursRedAlert,
                'All the hours should be displayed in gray');

            await unPatchDate();
            grid.destroy();
        });

        QUnit.test('timesheet avatar widget should display hours in gray if all the hours were performed', async function(assert) {

           assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
            });
            // worked_hours - units_to_work = 0 => we add d-none class (for the employee who has not done all his hours (employee.id = 7))
            const numberOfSpanWhereAllHoursCompleted = grid.$(`span.d-none`).length;
            assert.ok(numberOfSpanWhereAllHoursCompleted > 0, 'There must be at least one element or this test is useless');

            const numberOfSpanWhereAllHoursCompletedYetAreRed = grid.$(`span.o_grid_section_subtext_overtime_indication.d-none`).length;
            assert.ok(numberOfSpanWhereAllHoursCompletedYetAreRed === 0, 'Completed hours should not red');

            grid.destroy();
        });

        QUnit.test('timesheet avatar widget should display hours in red if all the hours were not performed and we are in the past', async function(assert) {

           assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
            });

            const numberOfSpanWhereAllHoursCompleted = grid.$("span:contains('+04:00')").length;
            assert.ok(numberOfSpanWhereAllHoursCompleted > 0, 'There must be at least one element or this test is useless');

            const numberOfSpanWhereAllHoursCompletedYetAreGreen = grid.$("span.o_grid_section_subtext_overtime:contains('+04:00')").length;
            assert.strictEqual(numberOfSpanWhereAllHoursCompletedYetAreGreen, numberOfSpanWhereAllHoursCompleted, 'The employee has done too much hours, thus we have an overtime.');

            grid.destroy();
        });

        QUnit.test('timesheet avatar widget should display days in red if all the days were not performed and we are in the past', async function(assert) {

            assert.expect(2);

            const grid = await createView({
                View: TimesheetGridView,
                model: 'analytic.line',
                data: this.data,
                arch: this.arch,
                currentDate: "2017-01-25",
            });

            const numberOfSpanWhereAllHoursCompleted = grid.$("span:contains('-1.00 days')").length;
            assert.ok(numberOfSpanWhereAllHoursCompleted > 0, 'There must be at least one element or this test is useless');

            const numberOfSpanWhereAllDaysAreNotDoneYetAreRed = grid.$("span.o_grid_section_subtext_not_enough_hours:contains('-1.00 days')").length;
            assert.strictEqual(numberOfSpanWhereAllDaysAreNotDoneYetAreRed, numberOfSpanWhereAllHoursCompleted, 'The employee has not done enough days, thus we display the number of days in red.');

            grid.destroy();
        });

    });
});
