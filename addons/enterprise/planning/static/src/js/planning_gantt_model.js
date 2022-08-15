/** @odoo-module alias=planning.PlanningGanttModel **/

import GanttModel from 'web_gantt.GanttModel';
import { _t } from 'web.core';
import { PlanningModelMixin } from './planning_mixins';

const GROUPBY_COMBINATIONS = [
    "role_id",
    "role_id,resource_id",
    "role_id,department_id",
    "department_id",
    "department_id,role_id",
    "project_id",
    "project_id,department_id",
    "project_id,resource_id",
    "project_id,role_id",
    "project_id,task_id,resource_id",
    "project_id,task_id,role_id",
    "task_id",
    "task_id,department_id",
    "task_id,resource_id",
    "task_id,role_id",
];

const PlanningGanttModel = GanttModel.extend(PlanningModelMixin, {
    /**
     * @override
     */
    __reload(handle, params) {
        if ("context" in params && params.context.planning_groupby_role && !params.groupBy.length) {
            params.groupBy.unshift('resource_id');
            params.groupBy.unshift('role_id');
        }
        return this._super(handle, params);
    },
    _fetchData: function () {
        this.context.planning_gantt_view = true;
        return this._super(...arguments).then((result) => {
            if (!this.isSampleModel && this.ganttData.groupedBy.includes('resource_id')) {
                const employeeIds = this._getResourceResIds(this.ganttData.rows);
                if (employeeIds.length) {
                    return this._rpc({
                        model: 'resource.resource',
                        method: 'get_planning_hours_info',
                        args: [employeeIds,
                            this.convertToServerTime(this.ganttData.startDate),
                            this.convertToServerTime(this.ganttData.endDate || this.ganttData.startDate.clone().add(1, this.ganttData.scale)),
                        ],
                    }).then((planningHoursInfo) => {
                        this._addPlanningHoursInfo(this.ganttData.rows, planningHoursInfo);
                    });
                }
            }
        });
    },
    /**
     * Check if the given groupedBy includes fields for which an empty fake group will be created
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowCreateEmptyGroups(groupedBy) {
        return groupedBy.includes("resource_id");
    },
    /**
     * Check if the given groupBy is in the list that has to generate empty lines
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowedEmptyGroups(groupedBy) {
        return GROUPBY_COMBINATIONS.includes(groupedBy.join(","));
    },
    /**
     * @private
     * @override
     * @returns {Object[]}
     */
    _generateRows(params) {
        const { groupedBy, groups, parentPath } = params;
        if (!this.hide_open_shift) {
            if (parentPath.length === 0) {
                // _generateRows is a recursive function.
                // Here, we are generating top level rows.
                if (this._allowCreateEmptyGroups(groupedBy)) {
                    // The group with false values for every groupby can be absent from
                    // groups (= groups returned by read_group basically).
                    // Here we add the fake group {} in groups in any case (this simulates the group
                    // with false values mentionned above).
                    // This will force the creation of some rows with resId = false
                    // (e.g. 'Open Shifts') from top level to bottom level.
                    groups.push({});
                }
                if (this._allowedEmptyGroups(groupedBy)) {
                    params.addOpenShifts = true;
                }
            }
            if (params.addOpenShifts && groupedBy.length === 1) {
                // Here we are generating some rows on last level (assuming
                // collapseFirstLevel is false) under a common "parent"
                // (if any: first level can be last level).
                // We make sure that a row with resId = false for
                // the unique groupby in groupedBy and same "parent" will be
                // added by adding a suitable fake group to the groups (a subset
                // of the groups returned by read_group).
                const fakeGroup = Object.assign({}, ...parentPath);
                groups.push(fakeGroup);
            }
        }
        const rows = this._super(params);
        // always move an empty row to the head
        if (groupedBy && groupedBy.length && rows.length > 1 && rows[0].resId) {
            this._reorderEmptyRow(rows);
        }
        return rows;
    },
    /**
     * Rename 'Undefined Resource' and 'Undefined Department' to 'Open Shifts'.
     *
     * @private
     * @override
     */
    _getRowName(groupedByField, value) {
        if (["department_id", "resource_id"].includes(groupedByField)) {
            const resId = Array.isArray(value) ? value[0] : value;
            if (!resId) {
                return _t("Open Shifts");
            }
        }
        return this._super(...arguments);
    },
    /**
     * Find an empty row and move it at the head of the array.
     *
     * @private
     * @param {Object[]} rows
     */
    _reorderEmptyRow(rows) {
        let emptyIndex = null;
        for (let i = 0; i < rows.length; ++i) {
            if (!rows[i].resId) {
                emptyIndex = i;
                break;
            }
        }
        if (emptyIndex) {
            const emptyRow = rows.splice(emptyIndex, 1)[0];
            rows.unshift(emptyRow);
        }
    },

    /**
     * Utils
     */
    /**
     * Recursive function to get resIds of employee
     *
     * @private
     */
    _getResourceResIds(rows) {
        const resIds = [];
        for (let row of rows) {
            if (row.groupedByField === "resource_id") {
                if (row.resId !== false) {
                    resIds.push(row.resId);
                }
            } else {
                resIds.push(...this._getResourceResIds(row.rows));
            }
        }
        return [...new Set(resIds)];
    },
    /**
     * Recursive function to add planningHours to employee
     *
     * @private
     */
    _addPlanningHoursInfo(rows, planningHoursInfo) {
        for (let row of rows) {
            if (row.groupedByField === "resource_id") {
                row.planningHoursInfo = planningHoursInfo[row.resId];
            } else {
                this._addPlanningHoursInfo(row.rows, planningHoursInfo);
            }
        }
    },
});

export default PlanningGanttModel;
