odoo.define('pos_settle_due.ClientLine', function (require) {
    'use strict';

    const ClientLine = require('point_of_sale.ClientLine');
    const Registries = require('point_of_sale.Registries');

    const POSSettleDueClientLine = (ClientLine) =>
        class extends ClientLine {
            getPartnerLink() {
                return `/web#model=res.partner&id=${this.props.partner.id}`;
            }
            async settleCustomerDue(event) {
                if (this.props.selectedClient == this.props.partner) {
                    event.stopPropagation();
                }
                const totalDue = this.props.partner.total_due;
                const paymentMethods = this.env.pos.payment_methods.filter(
                    (method) => this.env.pos.config.payment_method_ids.includes(method.id) && method.type != 'pay_later'
                );
                const selectionList = paymentMethods.map((paymentMethod) => ({
                    id: paymentMethod.id,
                    label: paymentMethod.name,
                    item: paymentMethod,
                }));
                const { confirmed, payload: selectedPaymentMethod } = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select the payment method to settle the due'),
                    list: selectionList,
                });
                if (!confirmed) return;
                this.trigger('discard'); // make sure the ClientListScreen resolves and properly closed.
                const newOrder = this.env.pos.add_new_order();
                const payment = newOrder.add_paymentline(selectedPaymentMethod);
                payment.set_amount(totalDue);
                newOrder.set_client(this.props.partner);
                this.showScreen('PaymentScreen');
            }
        };

    Registries.Component.extend(ClientLine, POSSettleDueClientLine);

    return ClientLine;
});
