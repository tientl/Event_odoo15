/** @odoo-module alias=planning.PlanningGanttRow **/

import HrGanttRow from 'hr_gantt.GanttRow';
import fieldUtils from 'web.field_utils';
import EmployeeWithPlannedHours from '@planning/js/widgets/employee_m2o_with_planned_hours';

const PlanningGanttRow = HrGanttRow.extend({
    template: 'PlanningGanttView.Row',

    init(parent, pillsInfo, viewInfo, options) {
        this._super(...arguments);
        const isGroupedByResource = pillsInfo.groupedByField === 'resource_id';
        const isEmptyGroup = pillsInfo.groupId === 'empty';
        this.employeeID = (pillsInfo.planningHoursInfo && pillsInfo.planningHoursInfo.employee_id) || false;
        this.showEmployeeAvatar = (isGroupedByResource && !isEmptyGroup && !!this.employeeID);
        this.planningHoursInfo = pillsInfo.planningHoursInfo;
    },

    _getEmployeeID() {
        return this.employeeID;
    },

    /**
     * Add allocated hours formatted to context
     *
     * @private
     * @override
     */
    _getPopoverContext: function () {
        const data = this._super.apply(this, arguments);
        data.allocatedHoursFormatted = fieldUtils.format.float_time(data.allocated_hours);
        data.allocatedPercentageFormatted = fieldUtils.format.float(data.allocated_percentage);
        return data;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize the avatar widget in virtual DOM.
     *
     * @private
     * @override
     * @returns {Promise}
     */
    async _preloadAvatarWidget() {
        const employee = [this._getEmployeeID(), this.name];
        this.avatarWidget = new EmployeeWithPlannedHours(this, employee, this.planningHoursInfo);
        return this.avatarWidget.appendTo(document.createDocumentFragment());
    },
});

export default PlanningGanttRow;
