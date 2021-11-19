odoo.define('pos_loyalty.ClientDetailsEdit', function(require) {

    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');
    const Registries = require('point_of_sale.Registries');
    const session = require('web.session');

    const LoyaltyClientDetailsEdit = ClientDetailsEdit => class extends ClientDetailsEdit {
        get isNotManager() {
            return this.env.pos.user.role !== "manager";
        }
    };

    Registries.Component.extend(ClientDetailsEdit, LoyaltyClientDetailsEdit);

    return ClientDetailsEdit;
});
