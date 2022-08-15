odoo.define('pos_l10n_se.NumpadWidget', function(require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');

    const PosSwedenNumpadWidget = NumpadWidget => class extends NumpadWidget {
        get hasPriceControlRights() {
            if (this.env.pos.useBlackBoxSweden())
                return false;
            return super.hasPriceControlRights;
        }
    };

    Registries.Component.extend(NumpadWidget, PosSwedenNumpadWidget);

    return PosSwedenNumpadWidget;
 });
