odoo.define('l10n_de_pos_res_cert.pos', function(require) {
    "use strict";

    const models = require('point_of_sale.models');
    const { uuidv4 } = require('l10n_de_pos_cert.utils');

    const _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        isRestaurantCountryGermanyAndFiskaly() {
            return this.isCountryGermanyAndFiskaly() && this.config.iface_floorplan;
        },
        //@Override
        disallowLineQuantityChange() {
            let result = _super_posmodel.disallowLineQuantityChange.apply(this, arguments);
            return this.isRestaurantCountryGermanyAndFiskaly() || result;
        },
        update_table_order(server_id, table_orders) {
            const order = _super_posmodel.update_table_order.apply(this,arguments);
            if (this.isRestaurantCountryGermanyAndFiskaly() && server_id.differences && order) {
                    order.createAndFinishOrderTransaction(server_id.differences)
                }
            return order
        },
        _post_remove_from_server(server_ids, data) {
            if (this.isRestaurantCountryGermanyAndFiskaly() && data.length > 0) {
                // at this point of the flow, it's impossible to retrieve the local order, only the ids were stored
                // therefore we create an "empty" order object in order to call the needed methods
                data.forEach(async elem => {
                    const order = new models.Order({}, {pos: this});
                    await order.cancelOrderTransaction(elem.differences);
                    order.destroy();
                })
            }
            return _super_posmodel._post_remove_from_server.apply(this, arguments);
        },
        //@Override
        /**
         * We first have to send the line items to Fiskaly from the orders offline queue
         */
        async _flush_orders(orders, options) {
            if (!this.isRestaurantCountryGermanyAndFiskaly()) {
                return _super_posmodel._flush_orders.apply(this, arguments);
            }
            if (!orders || !orders.length) {
                return Promise.resolve([]);
            }
            const ordersCheckDifference = orders.filter(elem => !elem.data.fiskaly_lines_sent).map(elem => elem.data);
            let differences = {};
            if (ordersCheckDifference.length > 0) {
                try {
                    differences = await this.rpc({
                        model: 'pos.order',
                        method: 'retrieve_line_difference',
                        args: [ordersCheckDifference]
                    });
                } catch (error) {
                    this.set_synch('disconnected');
                    throw error;
                }
            }

            let fiskalyError;
            if (Object.keys(differences).length > 0) {
                const ordersToUpdate = {}
                for (const orderJsonData of ordersCheckDifference) {
                    if (!fiskalyError && differences[orderJsonData.uid].length > 0) {
                        let order = new models.Order({}, {pos: this, json: orderJsonData});
                        try {
                            await order.sendLineDifference(differences[orderJsonData.uid]);
                            ordersToUpdate[orderJsonData.uid] = order.export_as_JSON();
                            order.finalize() // destroy the order so that it's not stored in the unpaid order
                        } catch (error) {
                            fiskalyError = error;
                        }
                    }
                }
                if (Object.keys(ordersToUpdate).length > 0) {
                    for (const order of orders) {
                        if (ordersToUpdate[order.data.uid]) {
                            order.data = ordersToUpdate[order.data.uid];
                        }
                    }
                    this.db.save('orders', orders);
                }
                if (fiskalyError) {
                    this.set_synch('disconnected');
                    fiskalyError.code = 'fiskaly';
                    throw fiskalyError;
                }
            }

            return _super_posmodel._flush_orders.apply(this, arguments);
        }
    });

    const _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        // @Override
        initialize() {
            _super_order.initialize.apply(this,arguments);
            if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
                this.fiskalyLinesSent = false; // this is mainly used for offline scenario
                this.save_to_db();
            }
        },
        //@Override
        export_as_JSON() {
            const json = _super_order.export_as_JSON.apply(this, arguments);
            if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
                json['fiskaly_lines_sent'] = this.fiskalyLinesSent;
            }
            return json;
        },
        //@Override
        init_from_JSON(json) {
            _super_order.init_from_JSON.apply(this, arguments);
            if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
                this.fiskalyLinesSent = json.fiskaly_lines_sent;
            }
        },
        _updateTimeStart(seconds) {
            if (!(this.pos.isRestaurantCountryGermanyAndFiskaly() && this.tssInformation.time_start.value)) {
                _super_order._updateTimeStart.apply(this, arguments);
            }
        },
        async createAndFinishOrderTransaction(lineDifference) {
            const transactionUuid = uuidv4();
            if (!this.pos.getApiToken()) {
                await this._authenticate();
            }

            lineDifference.forEach(line => {
                line.quantity = line.quantity.toString(); // Fiskaly ask this to be a string
                line.price_per_unit = this.pos.format_round_decimals_currency(line.price_per_unit);
            });
            const data = {
                'state': 'ACTIVE',
                'client_id': this.pos.getClientId()
            };
            return $.ajax({
                url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${transactionUuid}${this.pos.isUsingApiV2() ? '?tx_revision=1' : ''}`,
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${this.pos.getApiToken()}` },
                data: JSON.stringify(data),
                contentType: 'application/json',
                timeout: 5000
            }).then(() => {
                const data = {
                    'state': 'FINISHED',
                    'client_id': this.pos.getClientId(),
                    'schema': {
                        'standard_v1': {
                            'order': {
                                'line_items': lineDifference
                            }
                        }
                    }
                };
                return $.ajax({
                    url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${transactionUuid}?${this.pos.isUsingApiV2() ? 'tx_revision=2' : 'last_revision=1'}`,
                    method: 'PUT',
                    headers: {'Authorization': `Bearer ${this.pos.getApiToken()}`},
                    data: JSON.stringify(data),
                    contentType: 'application/json',
                    timeout: 5000
                });
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
                    await this._authenticate();
                    return this.createAndFinishOrderTransaction(lineDifference);
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });
        },
        exportOrderLinesAsJson() {
            const orderLines = [];
            this.orderlines.each(_.bind( function(item) {
                return orderLines.push([0, 0, item.export_as_JSON()]);
            }, this));

            return {
                server_id: this.server_id ? this.server_id : false,
                uid: this.uid,
                lines: orderLines,
            }
        },
        async retrieveAndSendLineDifference() {
            await this.pos.rpc({
                model: 'pos.order',
                method: 'retrieve_line_difference',
                args: [[this.exportOrderLinesAsJson()]]
            }).then(async data => {
                if (data[this.uid].length > 0) {
                    await this.sendLineDifference(data[this.uid])
                }
            });
        },
        async sendLineDifference(difference) {
            await this.createAndFinishOrderTransaction(difference);
            this.fiskalyLinesSent = true;
            this.trigger('change');
        },
        async cancelOrderTransaction(lineDifference) {
            if (lineDifference.length > 0) {
                await this.createAndFinishOrderTransaction(lineDifference);
            }
            await this.createTransaction();
            await this.cancelTransaction();
        }
    });
});
