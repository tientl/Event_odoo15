odoo.define('helpdesk.dashboard', function (require) {
"use strict";

/**
 * This file defines the Helpdesk Dashboard view (alongside its renderer, model
 * and controller), extending the Kanban view.
 * The Helpdesk Dashboard view is registered to the view registry.
 * A large part of this code should be extracted in an AbstractDashboard
 * widget in web, to avoid code duplication (see SalesTeamDashboard).
 */

var core = require('web.core');
var KanbanController = require('web.KanbanController');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var KanbanRecord = require('web.KanbanRecord');
var session = require('web.session');
var view_registry = require('web.view_registry');
const { format } = require('web.field_utils');

var QWeb = core.qweb;

var _t = core._t;
var _lt = core._lt;

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord() {
        const kanbanTicketElement = this.el.querySelectorAll('.o_helpdesk_ticket_btn');
        if (this.selectionMode !== true && this.modelName === 'helpdesk.team' && kanbanTicketElement.length) {
            kanbanTicketElement[0].click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

var HelpdeskDashboardRenderer = KanbanRenderer.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Notifies the controller that the target has changed.
     *
     * @private
     * @param {string} target_name the name of the changed target
     * @param {string} value the new value
     */
    _notifyTargetChange: function (target_name, value) {
        this.trigger_up('dashboard_edit_target', {
            target_name: target_name,
            target_value: value,
        });
    },

    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var helpdesk_dashboard = QWeb.render('helpdesk.HelpdeskDashboard', {
                widget: self,
                show_demo: values.show_demo,
                rating_enable: values.rating_enable,
                success_rate_enable: values.success_rate_enable,
                values: values,
                format_float: (value) => format.float(value),
                format_time: (value) => format.float_time(value),
            });
            if (!self.$el.parent('.o_kanban_view_wrapper').length) {
                self.$el.wrap('<div class="o_kanban_view_wrapper d-flex flex-column align-items-start"></div>');
            }
            self.$el.parent().find(".o_helpdesk_dashboard").remove();
            self.$el.before(helpdesk_dashboard);
            self.$el.parent().find('.o_dashboard_action')
              .on('click', self, self._onDashboardActionClicked.bind(self));
            self.$el.parent().find('.o_target_to_set')
              .on('click', self, self._onDashboardTargetClicked.bind(self));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent}
     */
    _onDashboardActionClicked: function (e) {
        var self = this;
        e.preventDefault();
        var $action = $(e.currentTarget);
        var action_ref = $action.attr('name');
        var title = $action.data('actionTitle') || $action.attr('title');
        var search_view_ref = $action.attr('search_view_ref');
        if ($action.attr('show_demo') != 'true'){
            if ($action.attr('name').includes("helpdesk.")) {
                this._rpc({
                    model: 'helpdesk.ticket',
                    method: 'create_action',
                    args: [action_ref, title, search_view_ref],
                }).then(function (result) {
                    if (result.action) {
                        self.do_action(result.action, {
                            additional_context: $action.attr('context')
                        });
                    }
                });
            }
            else {
                this.trigger_up('dashboard_open_action', {
                    action_name: $action.attr('name'),
                });
            }
        }
    },

    /**
     * @private
     * @param {MouseEvent}
     */
    _onDashboardTargetClicked: function (e) {
        var self = this;
        var $target = $(e.currentTarget);
        var target_name = $target.attr('name');
        var target_value = $target.attr('value');

        var $input = $('<input/>', {type: "text", name: target_name});
        if (target_value) {
            $input.attr('value', target_value);
        }
        $input.on('keyup input', function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                self._notifyTargetChange(target_name, $input.val());
            }
        });
        $input.on('blur', function () {
            self._notifyTargetChange(target_name, $input.val());
        });
        $input.replaceAll($target)
              .focus()
              .select();
    },
});

var HelpdeskDashboardModel = KanbanModel.extend({
    /**
     * @override
     */
    init: function () {
        this.dashboardValues = {};
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    __get: function (localID) {
        var result = this._super.apply(this, arguments);
        if (_.isObject(result)) {
            result.dashboardValues = this.dashboardValues[localID];
        }
        return result;
    },
    /**
     * @œverride
     * @returns {Promise}
     */
    __load: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },
    /**
     * @œverride
     * @returns {Promise}
     */
    __reload: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Promise} super_def a promise that resolves with a dataPoint id
     * @returns {Promise -> string} resolves to the dataPoint id
     */
    _loadDashboard: function (super_def) {
        var self = this;
        var dashboard_def = this._rpc({
            model: 'helpdesk.team',
            method: 'retrieve_dashboard',
            context: session.user_context,
        });
        return Promise.all([super_def, dashboard_def]).then(function(results) {
            const [id, dashboardValues] = results;
            self.dashboardValues[id] = dashboardValues;
            return id;
        });
    },
});

var HelpdeskDashboardController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        dashboard_open_action: '_onDashboardOpenAction',
        dashboard_edit_target: '_onDashboardEditTarget',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardEditTarget: function (e) {
        var target_name = e.data.target_name;
        var target_value = e.data.target_value;
        if (isNaN(target_value)) {
            this.displayNotification({ message: _t("Please enter an integer value"), type: 'danger' });
        } else {
            var values = {};
            values[target_name] = parseInt(target_value);
            this._rpc({
                    model: 'res.users',
                    method: 'write',
                    args: [[session.uid], values],
                })
                .then(this.reload.bind(this));
        }
    },
    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardOpenAction: function (e) {
        var self = this;
        var action_name = e.data.action_name;
        if (_.contains(['action_view_rating_today', 'action_view_rating_7days'], action_name)) {
            return this._rpc({model: this.modelName, method: action_name})
                .then(function (data) {
                    if (data) {
                        // Rename 'tree' to 'list' in the views
                        for (let view of data.views) {
                            if (view[1] === 'tree') {
                                view[1] = 'list';
                            }
                        }
                        return self.do_action(data);
                    }
                });
        }
        return this.do_action(action_name);
    },
});

var HelpdeskDashboardView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: HelpdeskDashboardModel,
        Renderer: HelpdeskDashboardRenderer,
        Controller: HelpdeskDashboardController,
    }),
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
});

view_registry.add('helpdesk_dashboard', HelpdeskDashboardView);

return {
    Model: HelpdeskDashboardModel,
    Renderer: HelpdeskDashboardRenderer,
    Controller: HelpdeskDashboardController,
};

});
