/** @odoo-module **/

import ConnectorContainer from '../connector/connector_container';
import { device } from 'web.config';
import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';
import TaskGanttRenderer from '../task_gantt_renderer';
import TaskGanttConnectorRow from "./task_gantt_connector_row";


const TaskGanttConnectorRenderer = TaskGanttRenderer.extend(WidgetAdapterMixin, {
    config: {
        GanttRow: TaskGanttConnectorRow,
    },
    custom_events: Object.assign({ }, TaskGanttRenderer.prototype.custom_events || { }, {
        connector_creation_abort: '_onConnectorCreationAbort',
        connector_creation_done: '_onConnectorCreationDone',
        connector_creation_start: '_onConnectorCreationStart',
        connector_mouseout: '_onConnectorMouseOut',
        connector_mouseover: '_onConnectorMouseOver',
        connector_remove_button_click: '_onConnectorRemoveButtonClick',
        connector_reschedule_later_button_click: 'onConnectorRescheduleLaterButtonClick',
        connector_reschedule_sooner_button_click: 'onConnectorRescheduleSoonerButtonClick',
    }),
    events: Object.assign({ }, TaskGanttRenderer.prototype.events || { }, {
        'mouseenter .o_gantt_pill, .o_connector_creator_wrapper': '_onPillMouseEnter',
        'mouseleave .o_gantt_pill, .o_connector_creator_wrapper': '_onPillMouseLeave',
    }),

    //--------------------------------------------------------------------------
    // Life Cycle
    //--------------------------------------------------------------------------

    /**
     * @override
    */
    init() {
        this._super(...arguments);
        this._connectors = { };
        this._preventHoverEffect = false;
        this._connectorsStrokeColors = this._getStrokeColors();
        this._connectorsStrokeWarningColors = this._getStrokeWarningColors();
        this._connectorsStrokeErrorColors = this._getStrokeErrorColors();
        this._connectorsOutlineStrokeColor = this._getOutlineStrokeColors();
        this._connectorsCssSelectors = {
            bullet: '.o_connector_creator_bullet',
            pill: '.o_gantt_pill',
            pillWrapper: '.o_gantt_pill_wrapper',
            wrapper: '.o_connector_creator_wrapper',
            groupByNoGroup: '.o_gantt_row_nogroup',
        };
    },
    /**
     * @override
    */
    destroy() {
        this._super(...arguments);
        window.removeEventListener('resize', this._throttledReRender);
    },
    /**
     * @override
    */
    on_attach_callback() {
        this._super(...arguments);
        // As we needs the source and target of the connectors to be part of the dom,
        // we need to use the on_attach_callback in order to have the first rendering successful.
        this._mountConnectorContainer();
        window.addEventListener('resize', this._throttledReRender);
    },
    /**
     * @override
    */
    async start() {
        await this._super(...arguments);
        this._connectorContainerComponent = new ComponentWrapper(this, ConnectorContainer, this._getConnectorContainerProps());
        this._throttledReRender = _.throttle(async () => {
            if (this._shouldRenderConnectors()) {
                await this._connectorContainerComponent.update(this._generateAndGetConnectorContainerProps());
            }
        }, 100);
    },
    /**
      * Make sure the connectorManager Component is updated each time the view is updated.
      *
      * @override
      */
    async update() {
        if (this._shouldRenderConnectors()) {
            await this._connectorContainerComponent.update(this._generateAndGetConnectorContainerProps());
        }
        await this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the connectors state in regards to the records state and returns the props.
     *
     * @return {Object} the props to pass to the ConnectorContainer
     * @private
     */
    _generateAndGetConnectorContainerProps() {
        this._preventHoverEffect = false;
        this._generateConnectors();
        return this._getConnectorContainerProps();
    },
    /**
     * Updates the connectors state in regards to the records state.
     *
     * @private
     */
    _generateConnectors() {
        /*
            First we need to build a dictionary in order to be able to manage the cases when a task is present
            multiple times in the gantt view, in order to draw the connectors accordingly.
            Structure of dict:
            {
                records : {
                    #ID_RECORD_1: {
                        record: STATE_RECORD,
                        rowsInfo: {
                            #ID_ROW_1: {
                                pillElement: HTMLElementPill1,
                            },
                            ...
                        }
                    },
                    ...
                },
                rows: {
                    #ID_ROW_1: {
                        records: {
                            #ID_RECORD_1: {
                                pillElement: HTMLElementPill1,
                                record: STATE_RECORD
                            },
                            ...
                        }
                    },
                    ...
                },
            }
        */
        this._rowsAndRecordsDict = {
            records: { },
            rows: { },
        };
        for (const row of this.state.rows) {
            // We need to escape '"' & '\' from the row.id before calling the querySelector
            const rowElementSelector = `${this._connectorsCssSelectors.groupByNoGroup}[data-row-id="${row.id.replace(/["\\]/g, '\\$&')}"]`;
            const rowElement = this.el.querySelector(rowElementSelector);
            this._rowsAndRecordsDict.rows[row.id] = {
                records: { }
            };
            for (const record of row.records) {
                const recordElementSelector = `${this._connectorsCssSelectors.pill}[data-id="${record.id}"]`;
                const pillElement = rowElement.querySelector(recordElementSelector);
                this._rowsAndRecordsDict.rows[row.id].records[record.id] = {
                    pillElement: pillElement,
                    record: record,
                };
                if (!(record.id in this._rowsAndRecordsDict.records)) {
                    this._rowsAndRecordsDict.records[record.id] = {
                        record: record,
                        rowsInfo: { },
                    };
                }
                this._rowsAndRecordsDict.records[record.id].rowsInfo[row.id] = {
                    pillElement: pillElement,
                };
            }
        }

        // Then we go over the rows and records one by one in order to create the connectors
        const connector_id_generator = {
            _value: 1,
            getNext() {
                return this._value++;
            }
        };
        this._connectors = { };
        for (const record of this.state.records) {
            const taskConnectors = this._generateConnectorsForTask(record, connector_id_generator);
            Object.assign(this._connectors, taskConnectors);
        }
    },
    /**
     * Generates the connectors (from depend_on_ids tasks to the task) for the provided task.
     *
     * @param {Object} task task record.
     * @param {{ getNext(): Number }} connector_id_generator a connector_id generator.
     * @private
     */
    _generateConnectorsForTask(task, connector_id_generator) {
        const result = {};
        for (const masterTaskId of task.depend_on_ids) {
            if (masterTaskId in this._rowsAndRecordsDict.records) {
                let connectors = [];
                for (const taskRowId in this._rowsAndRecordsDict.records[task.id].rowsInfo) {
                    for (const masterTaskRowId in this._rowsAndRecordsDict.records[masterTaskId].rowsInfo) {
                        /**
                         *   Having:
                         *      * B dependent on A
                         *      * C dependent on B
                         *      * D dependent on C
                         *   Prevent:
                         *      * Connectors between B & C that are not in the same group if B is in same group than C:
                         *          G1        B --- C                  B --- C
                         *                  /   \ /   \              /         \
                         *          G2    A             D    =>    A             D
                         *                  \   / \   /              \         /
                         *          G3        B --- C                  B --- C
                         *      * Connectors between A & B if A has already a link to B in the same group:
                         *          G1        --------- B              --------- B
                         *                  /       /                /
                         *          G2    A      /           =>    A
                         *                    /
                         *          G3    A ----------- B          A ----------- B
                         *   Allow:
                         *      * Connectors between C & B when A & B are always present in the same groups
                         *          G1    A ------ B          A ------ B
                         *                                           /
                         *          G2    A               =>  A ====
                         *                                           \
                         *          G3    A ------ B          A ------ B
                         */
                        if (masterTaskRowId === taskRowId
                            || !(
                                task.id in this._rowsAndRecordsDict.rows[masterTaskRowId].records
                                || masterTaskId in this._rowsAndRecordsDict.rows[taskRowId].records
                            )
                            || Object.keys(this._rowsAndRecordsDict.records[task.id].rowsInfo).every(
                                (rowId) => (masterTaskRowId !== rowId && masterTaskId in this._rowsAndRecordsDict.rows[rowId].records)
                            )
                            || Object.keys(this._rowsAndRecordsDict.records[masterTaskId].rowsInfo).every(
                                (rowId) => (taskRowId !== rowId && task.id in this._rowsAndRecordsDict.rows[rowId].records)
                            )
                        ) {
                            connectors.push(
                                this._generateConnector(
                                    masterTaskRowId,
                                    this._rowsAndRecordsDict.records[masterTaskId].record,
                                    taskRowId,
                                    task,
                                    connector_id_generator)
                            );
                        }
                    }
                }
                for (const connector of connectors) {
                    result[connector.id] = connector;
                }
            }
        }
        return result;
    },
    /**
     *
     * @param masterTaskRowId the row id of the masterTask (in order to handle m2m grouping)
     * @param masterTask a task record corresponding to the depend_on_id.
     * @param taskRowId the row id of the task (in order to handle m2m grouping)
     * @param task a task record.
     * @param {{ getNext(): Number }} connector_id_generator a connector_id generator.
     * @return {Object} a connector for the provided parameters.
     * @private
     */
    _generateConnector(masterTaskRowId, masterTask, taskRowId, task, connector_id_generator) {
        const masterTaskPill = this._rowsAndRecordsDict.rows[masterTaskRowId].records[masterTask.id].pillElement;
        const taskPill = this._rowsAndRecordsDict.rows[taskRowId].records[task.id].pillElement;
        let source = this._connectorContainerComponent.componentRef.comp.getAnchorsPositions(masterTaskPill);
        let target = this._connectorContainerComponent.componentRef.comp.getAnchorsPositions(taskPill);

        let connector = {
            id: connector_id_generator.getNext(),
            source: source.right,
            canBeRemoved: true,
            data: {
                taskId: task.id,
                taskRowId: taskRowId,
                masterTaskId: masterTask.id,
                masterTaskRowId: masterTaskRowId,
            },
            target: target.left,
        };

        let specialColors;
        if (masterTask.display_warning_dependency_in_gantt &&
            task.display_warning_dependency_in_gantt &&
            task.planned_date_begin.isBefore(masterTask.planned_date_end)) {
            specialColors = this._connectorsStrokeWarningColors;
            if (task.planned_date_begin.isBefore(masterTask.planned_date_begin)) {
                specialColors = this._connectorsStrokeErrorColors;
            }
        }
        if (specialColors) {
            connector['style'] = {
                stroke: {
                    color: specialColors.stroke,
                    hoveredColor: specialColors.hoveredStroke,
                }
            };
        }

        return connector;
    },
    /**
     * Gets the connector creator info for the provided element.
     *
     * @param {HTMLElement} element HTMLElement with a class of either o_connector_creator_bullet,
     *                              o_connector_creator_wrapper, o_gantt_pill or o_gantt_pill_wrapper.
     * @returns {{pillWrapper: HTMLElement, pill: HTMLElement, connectorCreators: Array<HTMLElement>}}
     * @private
     */
    _getConnectorCreatorInfo(element) {
        let connectorCreators = [];
        let pill = null;
        if (element.matches(this._connectorsCssSelectors.pillWrapper)) {
            element = element.querySelector(this._connectorsCssSelectors.pill);
        }
        if (element.matches(this._connectorsCssSelectors.bullet)) {
            element = element.closest(this._connectorsCssSelectors.wrapper);
        }
        if (element.matches(this._connectorsCssSelectors.pill)) {
            pill = element;
            connectorCreators = Array.from(element.parentElement.querySelectorAll(this._connectorsCssSelectors.wrapper));
        } else if (element.matches(this._connectorsCssSelectors.wrapper)) {
            connectorCreators = [element];
            pill = element.parentElement.querySelector(this._connectorsCssSelectors.pill);
        }
        return {
            pill: pill,
            pillWrapper: pill.parentElement,
            connectorCreators: connectorCreators,
        };
    },
    /**
     * Returns the props according to the current connectors state
     *
     * @returns {Object} the props to pass to the ConnectorContainer.
     * @private
     */
    _getConnectorContainerProps() {
        return {
            connectors: this._connectors,
            defaultStyle: {
                slackness: 0.9,
                stroke: {
                    color: this._connectorsStrokeColors.stroke,
                    hoveredColor: this._connectorsStrokeColors.hoveredStroke,
                    width: 2,
                },
                outlineStroke: {
                    color: this._connectorsOutlineStrokeColor.stroke,
                    hoveredColor: this._connectorsOutlineStrokeColor.hoveredStroke,
                    width: 1,
                }
            },
            hoverEaseWidth: 10,
            preventHoverEffect: this._preventHoverEffect,
            sourceQuerySelector: this._connectorsCssSelectors.bullet,
            targetQuerySelector: this._connectorsCssSelectors.pillWrapper,
        };
    },
    /**
     * Gets the rgba css string corresponding to the provided parameters.
     *
     * @param {number} r - [0, 255]
     * @param {number} g - [0, 255]
     * @param {number} b - [0, 255]
     * @param {number} [a = 1] - [0, 1]
     * @return {string} the css color.
     * @private
     */
    _getCssRGBAColor(r, g, b, a) {
        return `rgba(${ r }, ${ g }, ${ b }, ${ a || 1 })`;
    },
    /**
     * Gets the outline stroke's rgba css strings for both the stroke and its hovered state in error state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getOutlineStrokeColors() {
        return this._getStrokeAndHoveredStrokeColor(255, 255, 255);
    },
    /**
     * Returns the HTMLElement wrapped set for the provided taskId.
     *
     * @param {number} taskId
     * @returns {HTMLElement}
     * @private
     */
    _getPillForTaskId(taskId) {
        return this.el.querySelector(`${this._connectorsCssSelectors.pill}[data-id="${taskId}"]`);
    },
    /**
     * Returns the record corresponding to the taskId.
     *
     * @param taskId
     * @returns {Object}
     * @private
     */
    _getRecordForTaskId(taskId) {
        return this._rowsAndRecordsDict.records[taskId];
    },
    /**
     * Gets the stroke's rgba css string corresponding to the provided parameters for both the stroke and its
     * hovered state.
     *
     * @param {number} r - [0, 255]
     * @param {number} g - [0, 255]
     * @param {number} b - [0, 255]
     * @return {{ stroke: {string}, hoveredStroke: {string} }} the css colors.
     * @private
     */
    _getStrokeAndHoveredStrokeColor(r, g, b) {
        return {
            stroke: this._getCssRGBAColor(r, g, b, 0.5),
            hoveredStroke: this._getCssRGBAColor(r, g, b, 1),
        };
    },
    /**
     * Gets the stroke's rgba css strings for both the stroke and its hovered state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getStrokeColors() {
        return this._getStrokeAndHoveredStrokeColor(143, 143, 143);
    },
    /**
     * Gets the stroke's rgba css strings for both the stroke and its hovered state in error state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getStrokeErrorColors() {
        return this._getStrokeAndHoveredStrokeColor(211, 65, 59);
    },
    /**
     * Gets the stroke's rgba css strings for both the stroke and its hovered state in warning state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getStrokeWarningColors() {
        return this._getStrokeAndHoveredStrokeColor(236, 151, 31);
    },
    /**
     * Gets whether the provided connector creator is the source element of the currently dragged connector.
     *
     * @param {{pill: HTMLElement, connectorCreators: Array<HTMLElement>}} connectorCreatorInfo
     * @returns {boolean}
     * @private
     */
    _isConnectorCreatorDragged(connectorCreatorInfo) {
        return this._connectorInCreation && this._connectorInCreation.data.sourceElement.dataset.id === connectorCreatorInfo.pill.dataset.id;
    },
    /**
     * @override
     * @private
     */
    async _render() {
        await this._super(...arguments);
        if (this._isInDom) {
            // If the renderer is not yet part of the dom (during first rendering), then
            // the call will be performed in the on_attach_callback.
            await this._mountConnectorContainer();
        }
    },
    async _mountConnectorContainer() {
        if (this._shouldRenderConnectors()) {
            this.el.classList.toggle('position-relative', true);
            await this._connectorContainerComponent.mount(this.el);
            await this._connectorContainerComponent.update(this._generateAndGetConnectorContainerProps());
        }
    },
    /**
     * Returns whether should be rendered or not.
     * The connectors won't be rendered on sampleData as we can't be sure that data are coherent.
     * The connectors won't be rendered on mobile as the usability is not guarantied.
     * The connectors won't be rendered on multiple groupBy as we would need to manage groups folding which seems
     *     overkill at this stage.
     *
     * @return {boolean}
     * @private
     */
    _shouldRenderConnectors() {
        return this._isInDom && !this.state.isSample && !device.isMobile && this.state.groupedBy.length <= 1;
    },
    /**
     * Toggles popover visibility.
     *
     * @param visible
     * @private
     */
    _togglePopoverVisibility(visible) {
        const $pills = this.$(this._connectorsCssSelectors.pill);
        if (visible) {
            $pills.popover('enable').popover('dispose');
        } else {
            $pills.popover('hide').popover('disable');
        }
    },
    /**
     * Triggers the on_connector_highlight at the Controller.
     *
     * @param {ConnectorContainer.Connector.props} connector
     * @param {boolean} highlighted
     * @private
     */
    _triggerConnectorHighlighting(connector, highlighted) {
        this.trigger_up(
            'on_connector_highlight',
            {
                connector: connector,
                highlighted: highlighted,
            });
    },
    /**
     * Triggers the on_pill_highlight at the Controller.
     *
     * @param {HTMLElement} element
     * @param {boolean} highlighted
     * @private
     */
    _triggerPillHighlighting(element, highlighted) {
        this.trigger_up(
            'on_pill_highlight',
            {
                element: element,
                highlighted: highlighted,
            });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Sets the class on the gantt_view corresponding to the mode.
     * This class is used to prevent the magnifier and + buttons during connection creation.
     *
     * @param {boolean} in_creation
     */
    set_connector_creation_mode(in_creation) {
        this.el.classList.toggle('o_grabbing', in_creation);
    },
    /**
     * Toggles the highlighting of the connector.
     *
     * @param {ConnectorContainer.Connector.props} connector
     * @param {boolean} highlighted
     */
    toggleConnectorHighlighting(connector, highlighted) {
        const masterTaskPill = this._rowsAndRecordsDict.rows[connector.data.masterTaskRowId].records[connector.data.masterTaskId].pillElement;
        const taskPill = this._rowsAndRecordsDict.rows[connector.data.taskRowId].records[connector.data.taskId].pillElement;
        const sourceConnectorCreatorInfo = this._getConnectorCreatorInfo(masterTaskPill);
        const targetConnectorCreatorInfo = this._getConnectorCreatorInfo(taskPill);
        if (!this._isConnectorCreatorDragged(sourceConnectorCreatorInfo)) {
            sourceConnectorCreatorInfo.pill.classList.toggle('highlight', highlighted);
        }
        if (!this._isConnectorCreatorDragged(targetConnectorCreatorInfo)) {
            targetConnectorCreatorInfo.pill.classList.toggle('highlight', highlighted);
        }
    },
    /**
     * Toggles the preventConnectorsHover props of the connector container.
     *
     * @param {boolean} prevent
     */
    togglePreventConnectorsHoverEffect(prevent){
        this._preventHoverEffect = prevent;
        this._connectorContainerComponent.update(this._getConnectorContainerProps());
    },
    /**
     * Toggles the highlighting of the pill and connector creator of the provided element.
     *
     * @param {HTMLElement} element
     * @param {boolean} highlighted
     */
    async togglePillHighlighting(element, highlighted) {
        const connectorCreatorInfo = this._getConnectorCreatorInfo(element);
        if (connectorCreatorInfo.pill.dataset.id != 0) {
            const connectedConnectors = Object.values(this._connectors)
                                              .filter((connector) => {
                                                  const ids = [connector.data.taskId, connector.data.masterTaskId];
                                                  return ids.includes(
                                                      parseInt(connectorCreatorInfo.pill.dataset.id)
                                                  );
                                              });
            if (connectedConnectors.length) {
                connectedConnectors.forEach((connector) => {
                    connector.hovered = highlighted;
                    connector.canBeRemoved = !highlighted;
                });
                await this._connectorContainerComponent.update(this._getConnectorContainerProps());
            }
            for (const pill of Object.values(this._rowsAndRecordsDict.records[connectorCreatorInfo.pill.dataset.id].rowsInfo).map((rowInfo) => rowInfo.pillElement)) {
                const tempConnectorCreatorInfo = this._getConnectorCreatorInfo(pill);
                if (highlighted || !this._isConnectorCreatorDragged(tempConnectorCreatorInfo)) {
                    tempConnectorCreatorInfo.pill.classList.toggle('highlight', highlighted);
                    if (connectorCreatorInfo.pill === tempConnectorCreatorInfo.pill) {
                        for (let connectorCreator of tempConnectorCreatorInfo.connectorCreators) {
                            connectorCreator.classList.toggle('invisible', !highlighted);
                        }
                    }
                }
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler for Connector connector-creation-abort event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onConnectorCreationAbort(ev) {
        ev.stopPropagation();
        this._connectorInCreation = null;
        const connectorCreatorInfo = this._getConnectorCreatorInfo(ev.data.data.sourceElement);
        this._triggerPillHighlighting(connectorCreatorInfo.pill, false);
        this.trigger_up('on_connector_end_drag');
        this._togglePopoverVisibility(true);
    },
    /**
     * Handler for Connector connector-creation-done event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onConnectorCreationDone(ev) {
        ev.stopPropagation();
        this._connectorInCreation = null;
        const connectorSourceCreatorInfo = this._getConnectorCreatorInfo(ev.data.data.sourceElement);
        const connectorTargetCreatorInfo = this._getConnectorCreatorInfo(ev.data.data.targetElement);
        this.trigger_up('on_connector_end_drag');
        this.trigger_up(
            'on_create_connector',
            {
                masterTaskId: parseInt(connectorSourceCreatorInfo.pill.dataset.id),
                slaveTaskId: parseInt(connectorTargetCreatorInfo.pill.dataset.id),
            });
        this._togglePopoverVisibility(true);
    },
    /**
     * Handler for Connector connector-creation-start event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onConnectorCreationStart(ev) {
        ev.stopPropagation();
        this._connectorInCreation = ev.data;
        this._togglePopoverVisibility(false);
        const connectorCreatorInfo = this._getConnectorCreatorInfo(ev.data.data.sourceElement);
        this._triggerPillHighlighting(connectorCreatorInfo.pill, false);
        this.trigger_up('on_connector_start_drag');
    },
    /**
     * Handler for Connector connector-mouseout event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onConnectorMouseOut(ev) {
        ev.stopPropagation();
        this._triggerConnectorHighlighting(ev.data, false);
    },
    /**
     * Handler for Connector connector-mouseover event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onConnectorMouseOver(ev) {
        ev.stopPropagation();
        this._triggerConnectorHighlighting(ev.data, true);
    },
    /**
     * Handler for Connector connector-remove-button-click event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onConnectorRemoveButtonClick(ev) {
        ev.stopPropagation();
        const payload = ev.data;
        this.trigger_up(
        'on_remove_connector',
        {
            masterTaskId: payload.data.masterTaskId,
            slaveTaskId: payload.data.taskId,
        });
    },
    /**
     * Handler for Connector connector_reschedule_later_button_click event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    onConnectorRescheduleLaterButtonClick(ev) {
        ev.stopPropagation();
        const payload = ev.data;
        this.trigger_up(
        'on_reschedule_task',
        {
            direction: 'forward',
            masterTaskId: payload.data.masterTaskId,
            slaveTaskId: payload.data.taskId,
        });
    },
    /**
     * Handler for Connector connector_reschedule_sooner_button_click event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    onConnectorRescheduleSoonerButtonClick(ev) {
        ev.stopPropagation();
        const payload = ev.data;
        this.trigger_up(
        'on_reschedule_task',
        {
            direction: 'backward',
            masterTaskId: payload.data.masterTaskId,
            slaveTaskId: payload.data.taskId,
        });
    },
    /**
     * Handler for Pill connector-mouseenter event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onPillMouseEnter(ev) {
        ev.stopPropagation();
        this._triggerPillHighlighting(ev.currentTarget, true);
    },
    /**
     * Handler for Pill connector-mouseleave event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onPillMouseLeave(ev) {
        ev.stopPropagation();
        this._triggerPillHighlighting(ev.currentTarget, false);
    },
    /**
     * @override
     * @private
     * @param {OdooEvent} event
     */
    async _onStartDragging(event) {
        this._super(...arguments);
        this._triggerPillHighlighting(this.$draggedPill.get(0), false);
    }
});

export default TaskGanttConnectorRenderer;
