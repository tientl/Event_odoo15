odoo.define('quality_control_worksheet.WorksheetValidationView', function (require) {
"use strict";

const FormController = require('web.FormController');
const FormView = require('web.FormView');
const BasicModel = require('web.BasicModel');
const viewRegistry = require('web.view_registry');


const WorksheetValidationController = FormController.extend({
    /**
     * @override
     */
    saveRecord: async function () {
        return this._super(...arguments).then(res => {
            const record = this.model.get(this.handle);
            this._rpc({
                method: 'action_worksheet_check',
                model: 'quality.check',
                args: [[record.data.x_quality_check_id.res_id]],
                context: this.model.loadParams.context,
            }).then(action => {
                this.do_action(action);
            });
        });
    },
    _discardChanges: async function () {
        return this._super(...arguments).then(res => {
            const record = this.model.get(this.handle);
            this._rpc({
                method: 'action_worksheet_discard',
                model: 'quality.check',
                args: [[record.data.x_quality_check_id.res_id]],
                context: this.model.loadParams.context,
            }).then(action => {
                this.do_action(action);
            });
        });
    },
});

const WorksheetValidationModel = BasicModel.extend({
    canBeAbandoned: function (id) {
        return false;
    },
});


const WorksheetValidationView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: WorksheetValidationController,
        Model: WorksheetValidationModel,
    }),
});

viewRegistry.add('worksheet_validation', WorksheetValidationView);

});
