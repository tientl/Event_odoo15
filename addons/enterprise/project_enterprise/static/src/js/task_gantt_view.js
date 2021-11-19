/** @odoo-module **/

import viewRegistry from 'web.view_registry';
import GanttView from 'web_gantt.GanttView';
import TaskGanttController from './task_gantt_controller';
import TaskGanttRenderer from './task_gantt_renderer';
import TaskGanttModel from './task_gantt_model';
import { ProjectControlPanel } from '@project/js/project_control_panel';

export const TaskGanttView = GanttView.extend({
    config: Object.assign({}, GanttView.prototype.config, {
        Controller: TaskGanttController,
        Renderer: TaskGanttRenderer,
        Model: TaskGanttModel,
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('task_gantt', TaskGanttView);
