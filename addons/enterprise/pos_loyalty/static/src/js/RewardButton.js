odoo.define('pos_loyalty.RewardButton', function(require) {
'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class RewardButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        is_available() {
            const order = this.env.pos.get_order();
            return order ? order.get_available_rewards().length > 0 : false;
        }
        async onClick() {
            let order = this.env.pos.get_order();
            let client = this.env.pos.get('client') || this.env.pos.get_client();
            if (!client) {
                this.trigger('close-popup');
                // IMPROVEMENT: This code snippet is similar to selectClient of PaymentScreen.
                const {
                    confirmed,
                    payload: newClient,
                } = await this.showTempScreen('ClientListScreen', { client });
                if (confirmed) {
                    order.set_client(newClient);
                    order.updatePricelist(newClient);
                }
                return;
            }

            var rewards = order.get_available_rewards();
            if (rewards.length === 0) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('No Rewards Available'),
                    body: this.env._t('There are no rewards available for this customer as part of the loyalty program'),
                });
                return;
            } else if (rewards.length === 1 && this.env.pos.loyalty.rewards.length === 1) {
                order.apply_reward(rewards[0]);
                return;
            } else {
                const rewardsList = rewards.map(reward => ({
                    id: reward.id,
                    label: reward.name,
                    item: reward,
                }));

                const { confirmed, payload: selectedReward } = await this.showPopup('SelectionPopup',
                    {
                        title: this.env._t('Please select a reward'),
                        list: rewardsList,
                    }
                );

                if(confirmed)
                    order.apply_reward(selectedReward);
                return;
            }
        }
    }
    RewardButton.template = 'RewardButton';

    ProductScreen.addControlButton({
        component: RewardButton,
        condition: function() {
            return this.env.pos.config.module_pos_loyalty;
        },
    });

    Registries.Component.add(RewardButton);

    return RewardButton;
});
