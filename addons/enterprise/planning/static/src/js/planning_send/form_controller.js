/** @odoo-module **/

import FormController from 'web.FormController';
import { FormViewDialog } from 'web.view_dialogs';

/**
 * Display a dialog form view of employee model for each employee who has no work email
 *
 * This function is only useable in Controller class
 * and it is also used in [PlanningGanttController](../planning_gantt_controller.js) to avoid duplicate code.
 *
 * @param {Object} [result] result containing the employees without work email, context and relation to display the form view of the employee model.
 * @param {Array<number>} [result.res_ids] the employee ids without work email.
 * @param {Object} [result.context] context.
 * @param {string} [result.relation] the model name to display the form view.
 *
 * @returns {Promise}
 */
export function _displayDialogWhenEmployeeNoEmail(result) {
    if (!result) {
        // then we have nothing to do.
        return Promise.resolve();
    }
    return Promise.all(result.res_ids.map((employee_id) => {
        const def = new Promise((resolve, reject) => {
            const formDialog = new FormViewDialog(this, {
                title: "",
                res_model: result.relation,
                res_id: employee_id,
                readonly: false,
                context: result.context,
                on_saved: () => resolve(),
            }).open();
            formDialog.on('form_dialog_discarded', this, () => reject());
        });
        return def;
    }));
}

export default FormController.extend({
    _displayDialogWhenEmployeeNoEmail,
    async _callButtonAction (attrs, record) {
        const _super = this._super;
        try {
            if (attrs && attrs.name === 'action_send') {
                const result = await this.model.getEmployeesWithoutWorkEmail(record || this.model.get(this.handle));
                await this._displayDialogWhenEmployeeNoEmail(result);
            }
            return _super.apply(this, arguments);
        } catch (error) {
            return;
        }
    },
});
