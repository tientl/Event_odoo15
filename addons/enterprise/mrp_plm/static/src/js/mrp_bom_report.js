odoo.define('mrp_plm.mrp_bom_report', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;

var MrpBomReport = require('@mrp/js/mrp_bom_report')[Symbol.for("default")];

MrpBomReport.include({
    events: _.extend({}, MrpBomReport.prototype.events, {
        'click .o_mrp_ecos_action': '_onClickEcos',
    }),
    _onClickEcos: function (ev) {
        ev.preventDefault();
        var product_id = $(ev.currentTarget).data('res-id');
        return this.do_action({
            name: _t('ECOs'),
            type: 'ir.actions.act_window',
            res_model: 'mrp.eco',
            domain: [['product_tmpl_id.product_variant_ids', 'in', [product_id]]],
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
        });
    }
});

});
