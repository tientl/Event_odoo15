odoo.define('l10n_be_hr_payroll.import_file', function (require) {
"use strict";

var widget_registry = require('web.widget_registry');
const basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');

var FieldBinaryFileCommissionImport = basicFields.FieldBinaryFile.extend({
    on_file_uploaded_and_valid: function (size, name, content_type, file_base64) {
        this._super.apply(this, arguments);
        this.trigger_up('commission_file_uploaded');
    },
});

fieldRegistry.add('binary_commission', FieldBinaryFileCommissionImport);

});
