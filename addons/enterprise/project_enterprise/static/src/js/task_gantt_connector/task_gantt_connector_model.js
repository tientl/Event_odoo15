/** @odoo-module **/

import { Commands } from '@web/core/orm_service';
import TaskGanttModel from '../task_gantt_model';


const TaskGanttConnectorModel = TaskGanttModel.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds a task dependency between masterTaskId and slaveTaskId (slaveTaskId depends
     * on masterTaskId).
     *
     * @param masterTaskId
     * @param slaveTaskId
     * @returns {Promise<*>}
     */
    async createDependency(masterTaskId, slaveTaskId) {
        return this.mutex.exec(() => {
            return this._rpc({
                model: 'project.task',
                method: 'write',
                args: [[slaveTaskId], {depend_on_ids: [Commands.linkTo(masterTaskId)]}],
            });
        });
    },
    /**
     * Removes the task dependency between masterTaskId and slaveTaskId (slaveTaskId is no
     * more dependent on masterTaskId).
     *
     * @param masterTaskId
     * @param slaveTaskId
     * @returns {Promise<*>}
     */
    async removeDependency(masterTaskId, slaveTaskId) {
        return this.mutex.exec(() => {
            return this._rpc({
                model: 'project.task',
                method: 'write',
                args: [[slaveTaskId], {depend_on_ids: [Commands.forget(masterTaskId)]}],
            });
        });
    },
    async rescheduleTask(direction, masterTaskId, slaveTaskId) {
        return this.mutex.exec(() => {
            return this._rpc({
                model: 'project.task',
                method: 'action_reschedule',
                args: [direction, masterTaskId, slaveTaskId],
            });
        });
    }
});

export default TaskGanttConnectorModel;
