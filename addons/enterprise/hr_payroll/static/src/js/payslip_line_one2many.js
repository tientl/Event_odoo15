odoo.define('hr_payslip.payslip_line_one2many', function (require) {
"use strict";

const fieldRegistry = require('web.field_registry');
var view_registry = require('web.view_registry');
const FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var FormView = require('web.FormView');
var FormController = require('web.FormController');


const PayslipLineOne2Many = FieldOne2Many.extend({
    _onFieldChanged: function (ev) {
        this._super.apply(this, arguments);
        var self = this;
        var line_handle;
        if (ev.data.changes && ev.data.changes.line_ids && ev.data.changes.line_ids.operation === "CREATE") {
            return;
        }
        if (ev.data.changes && (ev.data.changes.hasOwnProperty('amount') || ev.data.changes.hasOwnProperty('quantity'))) {
            line_handle = ev.data.dataPointID;
        }
        // Sequence changes are a PITA, as one call is made for each line. Don't manage this use case
        if (line_handle) {
            this.trigger_up('payslip_line_updated', {
                res_id: this.res_id,
                line_handle: line_handle,
            });
        }
    },
});

fieldRegistry.add('payslip_line_one2many', PayslipLineOne2Many);

const WorkedDaysLineOne2Many = FieldOne2Many.extend({
    _onFieldChanged: function (ev) {
        this._super.apply(this, arguments);
        var self = this;
        var line_handle;
        if (ev.data.changes && ev.data.changes.line_ids && ev.data.changes.line_ids.operation === "CREATE") {
            return;
        }
        if (ev.data.changes && ev.data.changes.hasOwnProperty('amount')) {
            line_handle = ev.data.dataPointID;
        }
        if (line_handle) {
            this.trigger_up('worked_days_line_updated', {
                res_id: this.res_id,
                line_handle: line_handle,
            });
        }
    },
});

fieldRegistry.add('worked_days_line_one2many', WorkedDaysLineOne2Many);

var PayslipEditLinesFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        payslip_line_updated: '_onPayslipLineUpdated',
        worked_days_line_updated: '_onWorkedDaysLineUpdated',
    }),

    _onPayslipLineUpdated: function(infos) {
        var self = this;
        self.infos = infos;
        this.saveRecord(this.handle, {
            stayInEdit: true,
        }).then(function() {
            var line_handle = self.infos.data.line_handle;
            var line_id = self.model.localData[line_handle].data.id;
            var recordID = self.model.localData[self.handle].data.id;
            self._rpc({
                model: 'hr.payroll.edit.payslip.lines.wizard',
                method: 'recompute_following_lines',
                args: [recordID, line_id],
            }).then(function(action) {
                self.do_action(action);
            });
        });
    },

    _onWorkedDaysLineUpdated: function(infos) {
        var self = this;
        self.infos = infos;
        this.saveRecord(this.handle, {
            stayInEdit: true,
        }).then(function() {
            var recordID = self.model.localData[self.handle].data.id;
            self._rpc({
                model: 'hr.payroll.edit.payslip.lines.wizard',
                method: 'recompute_worked_days_lines',
                args: [recordID],
            }).then(function(action) {
                self.do_action(action);
            });
        });
    },
});

var PayslipEditLinesFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: PayslipEditLinesFormController,
    }),
});

view_registry.add('payslip_edit_lines_form', PayslipEditLinesFormView);

});
