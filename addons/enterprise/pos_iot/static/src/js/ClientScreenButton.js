odoo.define('pos_restaurant.ClientScreenButton', function(require) {
    'use strict';

    const ClientScreenButton = require('point_of_sale.ClientScreenButton');
    const Registries = require('point_of_sale.Registries');

    const PosIotClientScreenButton = ClientScreenButton =>
        class extends ClientScreenButton {
            async onClickProxy() {
                const renderedHtml = await this.env.pos.render_html_for_customer_facing_display();
                this.env.pos.proxy.take_ownership_over_client_screen(renderedHtml);
            }
            _start() {
                if (this.env.pos.iot_device_proxies.display) {
                    this.env.pos.iot_device_proxies.display.add_listener(this._checkOwner.bind(this));
                    setTimeout(() => {
                        this.env.pos.iot_device_proxies.display.action({action: 'get_owner'});
                    }, 1500);
                }
            }
            _checkOwner(data) {
                if (data.error) {
                    this.state.status = 'not_found';
                } else if (
                    data.owner === this.env.services.iot_longpolling._session_id
                ) {
                    this.state.status = 'success';
                } else {
                    this.state.status = 'warning';
                }
            }
        };

    Registries.Component.extend(ClientScreenButton, PosIotClientScreenButton);

    return ClientScreenButton;
});
