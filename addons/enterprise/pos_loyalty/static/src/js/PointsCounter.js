odoo.define('pos_loyalty.PointsCounter', function(require) {
'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const utils = require('web.utils');

    const round_pr = utils.round_precision;

    class PointsCounter extends PosComponent {
        get_points_won() {
            return round_pr(this.env.pos.get_order().get_won_points(), this.env.pos.loyalty.rounding);
        }
        get_points_spent() {
            return round_pr(this.env.pos.get_order().get_spent_points(), this.env.pos.loyalty.rounding);
        }
        get_points_total() {
            return round_pr(this.env.pos.get_order().get_new_total_points(), this.env.pos.loyalty.rounding);
        }
        get order() {
            return this.env.pos.get_order();
        }
    }
    PointsCounter.template = 'PointsCounter';

    Registries.Component.add(PointsCounter);

    return PointsCounter;
});
