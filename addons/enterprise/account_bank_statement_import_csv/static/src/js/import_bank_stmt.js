odoo.define('bank_stmt_import_csv.import', function (require) {
"use strict";

var core = require('web.core');
var BaseImport = require('base_import.import')

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;

var DataImportStmt = BaseImport.DataImport.extend({
    init: function (parent, action) {
        this._super.apply(this, arguments);
        action.display_name = _t('Import Bank Statement'); // Displayed in the breadcrumbs
        this.filename = action.params.filename || {};
        this.first_load = true;
    },
    start: function () {
        var self = this;
        return this._super().then(function (res) {
            self.id = self.parent_context.wizard_id;
            self.$('input[name=import_id]').val(self.id);
            self['loaded_file']();
        });
    },
    create_model: function() {
        return Promise.resolve();
    },
    import_options: function () {
        var options = this._super();
        options['bank_stmt_import'] = true;
        return options;
    },
    onfile_loaded: function () {
        var self = this;
        if (this.first_load) {
            this.$('.oe_import_file_show').val(this.filename);
            this.$('.oe_import_file_reload').hide();
            this.first_load = false;
            self['settings_changed']();
        }
        else {
            this.$('.oe_import_file_reload').show();
            this._super();
        }
    },
    call_import: function(kwargs) {
        var self = this;
        var superProm = self._super.apply(this, arguments);
        superProm.then(function (message) {
            if(message.ids){
                self.statement_line_ids = message.ids
            }
            if(message.messages && message.messages.length > 0) {
                self.statement_id = message.messages[0].statement_id
            }
        });
        return superProm;
    },
    exit: function () {
        if (!this.statement_id) return;
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'account.bank.statement',
            res_id: this.statement_id,
            views: [[false, 'form']],
            target: 'current',
        });
    },

});
core.action_registry.add('import_bank_stmt', DataImportStmt);

return {
    DataImportStmt: DataImportStmt,
};
});
