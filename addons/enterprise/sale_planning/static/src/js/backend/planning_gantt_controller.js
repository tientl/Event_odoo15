/** @odoo-module **/

import PlanningGanttController from '@planning/js/planning_gantt_controller';
import { _t } from 'web.core';

PlanningGanttController.include({
    events: Object.assign({}, PlanningGanttController.prototype.events, {
        'click .o_gantt_button_plan_so': '_onPlanSOClicked',
    }),
    buttonTemplateName: 'SalePlanningGanttView.buttons',

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------
    /**
     * Add and returns gantt view context keys to context in order to give info
     * about what is actually rendered client-side to server.
     *
     * @param {Object} context
     */
    _addGanttContextValues: function (context) {
        const state = this.model.get();
        return Object.assign(context, {
            scale: state.scale,
            focus_date: this.model.convertToServerTime(state.focusDate),
            start_date: this.model.convertToServerTime(state.startDate),
            stop_date: this.model.convertToServerTime(state.stopDate),
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     * @override
     * @param {Object} context
     */
    _openPlanDialog: function (context) {
        this.openPlanDialogCallback = (result) => {
            if (!result) {
                let notificationOptions = {
                    type: 'danger',
                    message: _t('This resource is not available for this shift during the selected period.'),
                };
                this.displayNotification(notificationOptions);
            }
        };
        Object.assign(context, {
            search_default_group_by_resource: false,
            search_default_group_by_role: false,
            planning_slots_to_schedule: true,
            search_default_sale_order_id: this.model.context.planning_gantt_active_sale_order_id || null,
        });
        this._addGanttContextValues(this.model.context);
        this._super.apply(this, arguments);
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPlanSOClicked: function (ev) {
        ev.preventDefault();
        const self = this;
        this._rpc({
            model: this.modelName,
            method: 'action_plan_sale_order',
            args: [
                this.model._getDomain(),
            ],
            context: this._addGanttContextValues(this.context),
        }).then(function (result) {
            let notificationOptions;
            if (result) {
                notificationOptions = {
                    type: 'success',
                    message: _t("The sales orders have successfully been assigned."),
                };
            } else {
                notificationOptions = {
                    type: 'danger',
                    message: _t('There are no sales orders to assign or no employees are available.'),
                };
            }
            self.displayNotification(notificationOptions);
            self.reload();
        });
    },
});
