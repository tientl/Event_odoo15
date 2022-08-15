/** @odoo-module **/

import TaskGanttController from '../task_gantt_controller';


const TaskGanttConnectorController = TaskGanttController.extend({
    custom_events: Object.assign(
        { },
        TaskGanttController.prototype.custom_events,
        {
            display_milestone_popover: '_onDisplayMilestonePopover',
            on_remove_connector: '_onRemoveConnector',
            on_reschedule_task: '_onRescheduleTask',
            on_create_connector: '_onCreateConnector',
            on_pill_highlight: '_onPillHighlight',
            on_connector_highlight: '_onConnectorHighlight',
            on_connector_start_drag: '_onConnectorStartDrag',
            on_connector_end_drag: '_onConnectorEndDrag',
        }),

    //--------------------------------------------------------------------------
    // Life Cycle
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function () {
        this._super(...arguments);
        this._draggingConnector = false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {OdooEvent} ev
     * @private
     */
    _onDisplayMilestonePopover: function (ev) {
        Object.assign(
            ev.data.popoverData,
            {
                display_project_name: !!this.context.search_default_my_tasks,
            });
        this.renderer.display_milestone_popover(ev.data.popoverData, ev.data.targetElement);
    },
    /**
     * @override
     * @param {OdooEvent} ev
     * @private
     */
    _onPillUpdatingStarted: function (ev) {
        this._super(...arguments);
        this.renderer.togglePreventConnectorsHoverEffect(true);
    },
    /**
     * @override
     * @param {OdooEvent} ev
     * @private
     */
    _onPillUpdatingStopped: function (ev) {
        this._super(...arguments);
        this.renderer.togglePreventConnectorsHoverEffect(false);
    },
    /**
     * Handler for renderer on-connector-end-drag event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onConnectorEndDrag(ev) {
        ev.stopPropagation();
        this._draggingConnector = false;
        this.renderer.set_connector_creation_mode(this._draggingConnector);
    },
    /**
     * Handler for renderer on-connector-highlight event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onConnectorHighlight(ev) {
        ev.stopPropagation();
        if (!this._updating && !this._draggingConnector) {
            this.renderer.toggleConnectorHighlighting(ev.data.connector, ev.data.highlighted);
        }
    },
    /**
     * Handler for renderer on-connector-start-drag event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onConnectorStartDrag(ev) {
        ev.stopPropagation();
        this._draggingConnector = true;
        this.renderer.set_connector_creation_mode(this._draggingConnector);
    },
    /**
     * Handler for renderer on-create-connector event.
     *
     * @param {OdooEvent} ev
     * @returns {Promise<*>}
     * @private
     */
    async _onCreateConnector(ev) {
        ev.stopPropagation();
        await this.model.createDependency(ev.data.masterTaskId, ev.data.slaveTaskId);
        await this.reload();
    },
    /**
     * Handler for renderer on-connector-end-drag event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onPillHighlight(ev) {
        ev.stopPropagation();
        if (!this._updating || !ev.data.highlighted) {
            await this.renderer.togglePillHighlighting(ev.data.element, ev.data.highlighted);
        }
    },
    /**
     * Handler for renderer on-remove-connector event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onRemoveConnector(ev) {
        ev.stopPropagation();
        await this.model.removeDependency(ev.data.masterTaskId, ev.data.slaveTaskId);
        await this.reload();
    },
    /**
     * Handler for renderer on-reschedule-task event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onRescheduleTask(ev) {
        ev.stopPropagation();
        const result = await this.model.rescheduleTask(ev.data.direction, ev.data.masterTaskId, ev.data.slaveTaskId);
        if (result.type !== 'ir.actions.client') {
            await this.reload();
        } else {
            this.do_action(result);
        }
    },
});

export default TaskGanttConnectorController;
