/** @odoo-module **/

import FormView from 'web.FormView';
import KanbanView from 'web.KanbanView';
import Widget from 'web.Widget';

const ViewsWidget = Widget.extend({
    template: 'stock_barcode_views_widget',
    events: {
        'click .o_save': '_onClickSave',
        'click .o_discard': '_onClickDiscard',
        'click .o_reception_report': '_onClickReceptionReport',
    },

    init: function (clientAction, model, view, additionalContext, params, mode, view_type) {
        this._super(...arguments);
        this.model = model;
        this.view = view;
        this.params = params || {};
        this.mode = mode || 'edit';
        this.view_type = view_type || 'form';
        this.context = {};
        this.context[`${this.view_type}_view_ref`] = this.view;
        this.context = Object.assign(this.context, additionalContext);
    },

    willStart: function () {
        return this._super().then(() => {
            return this._getViewController().then(controller => {
                this.controller = controller;
            });
        });
    },

    start: function () {
        const def = this.controller.appendTo(this.el.querySelector('.o_barcode_generic_view'));
        def.then(() => { // Hack to be able to scroll if the form view is too long.
            document.querySelector('.o_action_manager').style.overflow = 'auto';
        });
        return Promise.all([def, this._super()]);
    },

    /**
     * @override
     */
    destroy: function () {
        document.querySelector('.o_action_manager').style.overflow = '';
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create a controller for a given model, view and record.
     *
     * @returns {Promise} the form view's controller
     * @private
     */
    _getViewController: async function () {
        const views = [[false, this.view_type]];
        const fieldsViews = await this.loadViews(this.model, this.context, views);
        const params = Object.assign({}, this.params, {
            context: this.context,
            modelName: this.model,
            userContext: this.getSession().user_context,
            mode: this.mode,
            withControlPanel: false,
            withSearchPanel: false,
        });
        let view;
        if (this.view_type === 'form') {
            view = new FormView(fieldsViews.form, params);
        } else if (this.view_type === 'kanban') {
            view = new KanbanView(fieldsViews.kanban, params);
        }
        return view.getController(this).then(
            controller => controller, // Success: returns the controller.
            () => { // Fail (e.g.: no controller because the record doesn't exist anymore).
                // Removes the current ID to open form for a new record instead.
                delete params.currentId;
                view = new FormView(fieldsViews.form, params);
                return view.getController(this);
            }
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the click on the `confirm button`.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSave: async function (ev) {
        ev.stopPropagation();
        await this.controller.saveRecord(this.controller.handle, {
            stayInEdit: true,
            reload: false,
        });
        const record = this.controller.model.get(this.controller.handle);
        this.trigger_up('refresh', { recordId: record.res_id });
    },

    /**
     * Handles the click on the `discard button`.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDiscard: function (ev) {
        ev.stopPropagation();
        this.trigger_up('exit');
    },

    /**
     * Handles the click on the button to see reception report.
     * This can be removed if the ability to add button via standard
     * "action button" comes back...
     *
     * @private
     * @param {MouseEvent} ev
     */
     _onClickReceptionReport: function (ev) {
        ev.stopPropagation();
        const ids = this.controller.model.get(this.controller.handle).res_ids;
        return this._rpc({
            model: this.model,
            method: 'action_view_reception_report',
            args: ids,
        }).then(res => {
            return this.do_action(res, {additional_context: {default_picking_ids: ids}});
        });
    }
});

export default ViewsWidget;
