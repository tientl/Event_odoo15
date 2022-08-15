odoo.define('timesheet_grid.GridModel', function (require) {
    "use strict";

    const GridModel = require('web_grid.GridModel');
    const GroupByNoDateMixin = require('timesheet_grid.GroupByNoDateMixin');

    const TimesheetGridModel = GridModel.extend(GroupByNoDateMixin).extend({

        /**
         * @override
         */
        async __load(params) {
            const result = await this._super(...arguments);

            this._gridData.timeBoundariesContext = this.getTimeContext();
            this._gridData.workingHoursData = await this.fetchAllTimesheetM2OAvatarData(this.getEmployeeGridValues(), this._gridData.timeBoundariesContext.start, this._gridData.timeBoundariesContext.end);

            return result;
        },

        /**
         * @override
         */
        async __reload(handle, params) {

            // Sometimes, like after a cell update, we only need to update the hours widget data.
            if (params && params.onlyHoursData) {
                const { start, end } = this.getTimeContext();
                this._gridData.workingHoursData = await this.fetchAllTimesheetM2OAvatarData(this.getEmployeeGridValues(), start, end);
                return;
            }

            const result = await this._super(...arguments);

            this._gridData.timeBoundariesContext = this.getTimeContext();
            this._gridData.workingHoursData = await this.fetchAllTimesheetM2OAvatarData(this.getEmployeeGridValues(), this._gridData.timeBoundariesContext.start, this._gridData.timeBoundariesContext.end);

            return result;

        },

        /**
         * Retrieves from the grid data about the employees.
         * This data is useful for the widget timesheet avatar's rpc.
         *
         * It needs to pay attention that depending on the way the grid is grouped or not,
         * the data is not at the same place and at the same format.
         *
         * @returns [ { employee_id, employee_display_name, grid_row_index }, ... ]
         */
        getEmployeeGridValues() {
            const employees = [];
            if (this._gridData.isGrouped && this._gridData.groupBy[0] === 'employee_id') {
                this._gridData.data // all the rows
                    .filter(row => row.__label)
                    .forEach((row, index) => {
                        employees.push({
                            'employee_id': row.__label[0],
                            'employee_display_name': row.__label[1],
                            'grid_row_index': index
                        });
                    });
            } else {
                this._gridData.data[0].rows // all the rows
                    .filter(row => 'employee_id' in row.values)
                    .forEach((row, index) => {
                        employees.push({
                            'employee_id': row.values.employee_id[0],
                            'employee_display_name': row.values.employee_id[1],
                            'grid_row_index': index
                        });
                    });
            }
            return employees;
        },

        /**
         * Retrieve the start and end date of the currently displayed range.
         * So, start of week / month and end of week / month.
         * The data is retrieved that way to avoid problems of localization where the start of the week may be a
         * different day (Sunday or Monday or ... )
         *
         * @returns {{start: string, end: string}}
         */

        getTimeContext() {

            const startOfTheRange = this._gridData.data[0].cols[0].domain[1][2];
            const endOfTheRange = this._gridData.data[0].cols[this._gridData.data[0].cols.length - 1].domain[1][2];

            return {
                start: startOfTheRange,
                end: endOfTheRange,
            };

        },

        /**
         * Perform a rpc to get the data for the timesheet avatar widget.
         *
         * @param employeesGridData employees data gathered from the grid.
         * @param {String} start the range start data
         * @param {String} end the range end date
         * @returns {Promise<object|*>}
         */
        async fetchAllTimesheetM2OAvatarData(employeesGridData, start, end) {

            // If there is no data, we don't bother
            if (employeesGridData.length === 0) {
                return {};
            }

            const hoursData = await this._rpc({
                model: 'hr.employee',
                method: 'get_timesheet_and_working_hours_for_employees',
                args: [employeesGridData, start, end],
            });

            return hoursData;
        },

    });

    return TimesheetGridModel;
});
