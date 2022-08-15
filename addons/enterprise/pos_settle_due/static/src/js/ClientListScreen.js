odoo.define('pos_settle_due.ClientListScreen', function (require) {
    'use strict';

    const ClientListScreen = require('point_of_sale.ClientListScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    const POSSettleDueClientListScreen = (ClientListScreen) =>
        class extends ClientListScreen {
            constructor() {
                super(...arguments);
                // trigger to close this screen (from being shown as tempScreen)
                useListener('discard', this.back);
            }
            async refreshTotalDue() {
                const partnersWithUpdatedFields = await this.rpc({
                    model: 'res.partner',
                    method: 'search_read',
                    args: [[['id', 'in', this.env.pos.db.partner_sorted]], ['total_due']],
                });
                this.env.pos.db.update_partners(partnersWithUpdatedFields);
                this.render();
            }
        };

    Registries.Component.extend(ClientListScreen, POSSettleDueClientListScreen);

    return ClientListScreen;
});
