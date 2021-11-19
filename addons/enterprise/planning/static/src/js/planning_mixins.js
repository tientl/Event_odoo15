/** @odoo-module */

export const PlanningModelMixin = {
    /**
     * Get the employees without work email
     *
     * This function is only useable in Model class
     * and it is also used in [PlanningGanttModel](./planning_gantt_model.js) to avoid duplicate code.
     *
     * @param {Record<string, any>} record the record of the current model
     * @returns {Promise} the response of the server
     */
    getEmployeesWithoutWorkEmail(record) {
        return this._rpc({
            model: record.model,
            method: 'get_employees_without_work_email',
            args: [record.res_id],
        });
    }
};
