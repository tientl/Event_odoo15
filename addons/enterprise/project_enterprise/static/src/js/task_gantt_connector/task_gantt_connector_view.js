/** @odoo-module **/

import viewRegistry from 'web.view_registry';
import { TaskGanttView } from '../task_gantt_view';
import TaskGanttConnectorController from "./task_gantt_connector_controller";
import TaskGanttConnectorRenderer from "./task_gantt_connector_renderer";
import TaskGanttConnectorModel from "./task_gantt_connector_model";

export const TaskGanttConnectorView = TaskGanttView.extend({
    config: Object.assign({}, TaskGanttView.prototype.config, {
        Controller: TaskGanttConnectorController,
        Renderer: TaskGanttConnectorRenderer,
        Model: TaskGanttConnectorModel,
    }),

    //--------------------------------------------------------------------------
    // Life Cycle
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        const taskDependenciesFields = ['allow_task_dependencies', 'depend_on_ids', 'display_warning_dependency_in_gantt', 'project_id'];
        this.loadParams.decorationFields.push(...taskDependenciesFields);
    }
});

viewRegistry.add('task_gantt_connector', TaskGanttConnectorView);
