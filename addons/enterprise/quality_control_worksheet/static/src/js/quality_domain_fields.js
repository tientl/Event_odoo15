odoo.define('quality_worksheet.domain_fields', function (require) {
    "use strict";

/**
 * This module creates a new domain field widget that only show domain selector
 * part.
 */

const field_registry = require('web.field_registry');
const basic_fields = require('web.basic_fields');

const FieldDomain = basic_fields.FieldDomain;

const QualityFieldDomain = FieldDomain.extend({
    /**
     * @override
     */
    _replaceContent: function () {
        return;
    },
});

field_registry.add('quality_field_domain', QualityFieldDomain);

return {
    QualityFieldDomain: QualityFieldDomain,
};

})
