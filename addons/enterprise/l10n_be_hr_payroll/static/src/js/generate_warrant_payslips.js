odoo.define('hr_payroll.generate.warrant.payslips', function (require) {
"use strict";
    var core = require('web.core');
    var download = require('web.download');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var QWeb = core.qweb;

    var GenerateCommissionPayslipsFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            commission_file_uploaded: '_onCommissionFileUploaded',
        }),

        /**
         * Extends the renderButtons function of FormView by adding a button
         * to export a csv file and download it automatically.
         *
         * @override
         */
        renderButtons: function () {
            var self = this;
            this._super.apply(this, arguments);
            if ($(this.$buttons[0]).find('footer').length) {
                $(this.$buttons[0]).find('footer .o_generate').after(
                    $(QWeb.render("GenerateCommissionPayslipsFormView.export", this)));
                this.$buttons.on('click', '.o_button_export', function (ev) {
                    self.saveRecord(self.handle, {
                        stayInEdit: true,
                    }).then(function() {
                        var recordID = self.model.localData[self.handle].data.id;
                        self._rpc({
                            model: 'hr.payroll.generate.warrant.payslips',
                            method: 'export_employee_file',
                            args: [recordID],
                        }).then(function(content){
                            var blob = new Blob([content], {'type': 'text/csv'});
                            download(blob, 'exported_employees.csv', 'text/csv');
                            self.do_action({
                                type: 'ir.actions.act_window',
                                res_model: 'hr.payroll.generate.warrant.payslips',
                                view_mode: 'form',
                                res_id: recordID,
                                views: [[false, 'form']],
                                target: 'new',
                            });
                        });
                    });
                });
            }
        },

        _onCommissionFileUploaded: function () {
            var self = this;
            this.saveRecord(this.handle, {
                stayInEdit: true,
            }).then(function() {
                var recordID = self.model.localData[self.handle].data.id;
                self._rpc({
                    model: 'hr.payroll.generate.warrant.payslips',
                    method: 'import_employee_file',
                    args: [recordID],
                }).then(function(action) {
                    self.do_action(action);
                });
            });
        },
    });

    var GenerateCommissionPayslipsFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: GenerateCommissionPayslipsFormController,
        }),
    });

    viewRegistry.add('generate_warrant_payslips', GenerateCommissionPayslipsFormView);
});
