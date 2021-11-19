odoo.define('timesheet_grid.GridRenderer', function (require) {
    "use strict";

    const { ComponentAdapter } = require('web.OwlCompatibility');
    const GridRenderer = require('web_grid.GridRenderer');
    const TimesheetM2OAvatarEmployee = require('timesheet_grid.TimesheetM2OAvatarEmployee');

    class TimesheetM2OAvatarEmployeeAdapter extends ComponentAdapter {

        /**
         * @override
         */
        async updateWidget(nextProps) {
            await this.widget.update(nextProps);
        }

        /**
         * @override
         */
        get widgetArgs() {
            return [this.props.value, this.props.rowIndex, this.props.rangeContext, this.props.timeBoundariesContext, this.props.workingHoursData];
        }

    }

    class TimesheetGridRenderer extends GridRenderer {
        constructor(parent, props) {
            super(...arguments);
            this.widgetComponents = {
                TimesheetM2OAvatarEmployee: TimesheetM2OAvatarEmployee
            };
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------
        /**
         * @returns {boolean} true if we need to display an employee avatar
         */
        get showEmployeeAvatar() {
            const empIdGroupIndex = this.props.groupBy.indexOf('employee_id');

            if (empIdGroupIndex < 0) {
                // Not grouped by employee_id = no avatar to show
                return false;
            }

            if (this.props.isGrouped) {
                // For grouped grid
                const isGroupLabel = this.rowlabel_index === undefined;
                const isGroupLabelAnEmployee = isGroupLabel && empIdGroupIndex === 0;
                const isLabelAnEmployee = !isGroupLabel && empIdGroupIndex === this.label_index + 1;
                return isGroupLabelAnEmployee || isLabelAnEmployee;
            }

            // For ungrouped grid, show if current label is an employee
            return empIdGroupIndex === this.label_index;
        }
    }

    TimesheetGridRenderer.components = {
        TimesheetM2OAvatarEmployeeAdapter
    };

    TimesheetGridRenderer.props = Object.assign({}, GridRenderer.props, {
        workingHoursData: Object,
        timeBoundariesContext: {
            type: Object,
            shape: {
                start: String,
                end: String,
            },
        },
    });

    return TimesheetGridRenderer;
});
