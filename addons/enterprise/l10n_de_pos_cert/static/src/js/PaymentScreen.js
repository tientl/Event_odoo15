odoo.define('l10n_de_pos_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const PosDePaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        constructor() {
            super(...arguments);
            if (this.env.pos.isCountryGermanyAndFiskaly()) {
                const _super_handlePushOrderError = this._handlePushOrderError.bind(this);
                this._handlePushOrderError = async (error) => {
                    if (error.code === 'fiskaly') {
                        const message = {
                            'noInternet': this.env._t('Cannot sync the orders with Fiskaly !'),
                            'unknown': this.env._t('An unknown error has occurred ! Please contact Odoo for more information.')
                        };
                        this.trigger('fiskaly-error', {error, message});
                    } else {
                        _super_handlePushOrderError(error);
                    }
                }
                this.validateOrderFree = true;
            }
        }
        // Almost the same as in the basic module but we don't finalize if the api call has failed
        async validateOrder(isForceValidate) {
            if (this.env.pos.isCountryGermanyAndFiskaly()) {
                if (!this.validateOrderFree) {
                    return;
                }
                this.validateOrderFree = false;
                if (await this._isOrderValid(isForceValidate)) {
                    // remove pending payments before finalizing the validation
                    for (let line of this.paymentLines) {
                        if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                    }
                    if (this.currentOrder.isTransactionInactive()) {
                        await this.currentOrder.createTransaction().catch(async (error) => {
                            if (error.status === 0) {
                                this.trigger('fiskaly-no-internet-confirm-popup', this._finalizeValidation.bind(this));
                            } else {
                                const message = {'unknown': this.env._t('An unknown error has occurred ! Please, contact Odoo.')};
                                this.trigger('fiskaly-error', {error, message});
                            }
                        })
                    }
                    if (this.currentOrder.isTransactionStarted()) {
                        await this.currentOrder.finishShortTransaction().then(async () => {
                            await this._finalizeValidation();
                        }).catch(async (error) => {
                            if (error.status === 0) {
                                this.trigger('fiskaly-no-internet-confirm-popup', this._finalizeValidation.bind(this));
                            } else {
                                const message = {'unknown': this.env._t('An unknown error has occurred ! Please, contact Odoo.')};
                                this.trigger('fiskaly-error', {error, message});
                            }
                        });
                    }
                }
                this.validateOrderFree = true;
            } else {
                await super.validateOrder(...arguments);
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosDePaymentScreen);

    return PaymentScreen;
});
