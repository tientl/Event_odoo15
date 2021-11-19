odoo.define('pos_loyalty.pos_loyalty', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var utils = require('web.utils');

var round_pr = utils.round_precision;

var _t = core._t;

models.load_fields('res.partner','loyalty_points');

models.load_models([
    {
        model: 'loyalty.program',
        condition: function(self){ return !!self.config.loyalty_id[0]; },
        fields: ['name','points'],
        domain: function(self){ return [['id','=',self.config.loyalty_id[0]]]; },
        loaded: function(self,loyalties){
            self.loyalty = loyalties[0];
            self.loyalty.rules = [];
            self.loyalty.rewards = [];
        },
    },{
        model: 'loyalty.rule',
        condition: function(self){ return self.loyalty; },
        fields: ['name','valid_product_ids','points_quantity','points_currency','loyalty_program_id'],
        domain: function(self){ return [['loyalty_program_id','=',self.loyalty.id]]; },
        loaded: function(self,rules){
            rules.forEach(function(rule) {
                self.loyalty.rules.push(rule);
            });
        },
    },{
        model: 'loyalty.reward',
        condition: function(self){ return self.loyalty; },
        fields: ['name','reward_type','minimum_points','gift_product_id','point_cost','discount_product_id',
                'discount_percentage', 'discount_fixed_amount', 'discount_apply_on', 'discount_type', 'discount_apply_on',
                'discount_specific_product_ids', 'discount_max_amount', 'minimum_amount', 'loyalty_program_id'],
        domain: function(self){ return [['loyalty_program_id','=',self.loyalty.id]]; },
        loaded: function(self,rewards){
            rewards.forEach(function(reward) {
                self.loyalty.rewards.push(reward);
            });
        },
    },
],{'after': 'product.product'});

var _super_orderline = models.Orderline;
models.Orderline = models.Orderline.extend({
    get_reward: function(){
        var reward_id = this.reward_id;
        return this.pos.loyalty.rewards.find(function(reward){return reward.id === reward_id;});
    },
    set_reward: function(reward){
        this.reward_id = reward.id;
    },
    export_as_JSON: function(){
        var json = _super_orderline.prototype.export_as_JSON.apply(this,arguments);
        json.reward_id = this.reward_id;
        return json;
    },
    init_from_JSON: function(json){
        _super_orderline.prototype.init_from_JSON.apply(this,arguments);
        this.reward_id = json.reward_id;
    },
});

var _super = models.Order;
models.Order = models.Order.extend({

    /* The total of points won, excluding the points spent on rewards */
    get_won_points: function(){
        if (!this.pos.loyalty || !this.get_client()) {
            return 0;
        }
        var total_points = 0;
        for (var line of this.get_orderlines()){
            if (line.get_reward()) {  // Reward products are ignored
                continue;
            }

            var line_points = 0;
            this.pos.loyalty.rules.forEach(function(rule) {
                var rule_points = 0
                if(rule.valid_product_ids.find(function(product_id) {return product_id === line.get_product().id})) {
                    rule_points += rule.points_quantity * line.get_quantity();
                    rule_points += rule.points_currency * line.get_price_with_tax();
                }
                if(Math.abs(rule_points) > Math.abs(line_points))
                    line_points = rule_points;
            });

            total_points += line_points;
        }
        total_points += this.get_total_with_tax() * this.pos.loyalty.points;
        return round_pr(total_points, 1);
    },

    /* The total number of points spent on rewards */
    get_spent_points: function() {
        if (!this.pos.loyalty || !this.get_client()) {
            return 0;
        } else {
            var points   = 0;

            for (var line of this.get_orderlines()){
                var reward = line.get_reward();
                if(reward) {
                    points += round_pr(line.get_quantity() * reward.point_cost, 1);
                }
            }
            return points;
        }
    },

    /* The total number of points lost or won after the order is validated */
    get_new_points: function() {
        if (!this.pos.loyalty || !this.get_client()) {
            return 0;
        } else {
            return round_pr(this.get_won_points() - this.get_spent_points(), 1);
        }
    },

    /* The total number of points that the customer will have after this order is validated */
    get_new_total_points: function() {
        if (!this.pos.loyalty || !this.get_client()) {
            return 0;
        } else {
            if(this.state != 'paid'){
                return round_pr(this.get_client().loyalty_points + this.get_new_points(), 1);
            }
            else{
                return round_pr(this.get_client().loyalty_points, 1);
            }
        }
    },

    /* The number of loyalty points currently owned by the customer */
    get_current_points: function(){
        return this.get_client() ? this.get_client().loyalty_points : 0;
    },

    /* The total number of points spendable on rewards */
    get_spendable_points: function(){
        if (!this.pos.loyalty || !this.get_client()) {
            return 0;
        } else {
            return round_pr(this.get_client().loyalty_points - this.get_spent_points(), 1);
        }
    },

    /* The list of rewards that the current customer can get */
    get_available_rewards: function(){
        var client = this.get_client();
        if (!client) {
            return [];
        }

        var self = this;
        var rewards = [];
        for (var i = 0; i < this.pos.loyalty.rewards.length; i++) {
            var reward = this.pos.loyalty.rewards[i];
            if (reward.minimum_points > self.get_spendable_points()) {
                continue;
            } else if(reward.reward_type === 'discount' && reward.point_cost > self.get_spendable_points()) {
                continue;
            } else if(reward.reward_type === 'gift' && reward.point_cost > self.get_spendable_points()) {
                continue;
            } else if(reward.reward_type === 'discount' && reward.discount_apply_on === 'specific_products' ) {
                var found = false;
                self.get_orderlines().forEach(function(line) {
                    found |= reward.discount_specific_product_ids.find(function(product_id){return product_id === line.get_product().id;});
                });
                if(!found)
                    continue;
            } else if(reward.reward_type === 'discount' && reward.discount_type === 'fixed_amount' && self.get_total_with_tax() < reward.minimum_amount) {
                continue;
            }
            rewards.push(reward);
        }
        return rewards;
    },

    apply_reward: function(reward){
        var client = this.get_client();
        var product, product_price, order_total, spendable;
        var crounding;

        if (!client) {
            return;
        } else if (reward.reward_type === 'gift') {
            product = this.pos.db.get_product_by_id(reward.gift_product_id[0]);

            if (!product) {
                return;
            }

            this.add_product(product, {
                price: 0,
                quantity: 1,
                merge: false,
                extras: { reward_id: reward.id },
            });

        } else if (reward.reward_type === 'discount') {

            crounding = this.pos.currency.rounding;
            spendable = this.get_spendable_points();
            order_total = this.get_total_with_tax();
            var discount = 0;

            product = this.pos.db.get_product_by_id(reward.discount_product_id[0]);

            if (!product) {
                return;
            }

            if(reward.discount_type === "percentage") {
                if(reward.discount_apply_on === "on_order"){
                    discount += round_pr(order_total * (reward.discount_percentage / 100), crounding);
                }

                if(reward.discount_apply_on === "specific_products") {
                    for (var prod of reward.discount_specific_product_ids){
                        var specific_products = this.pos.db.get_product_by_id(prod);

                        if (!specific_products)
                            return;

                        for (var line of this.get_orderlines()){
                            if(line.product.id === specific_products.id)
                                discount += round_pr(line.get_price_with_tax() * (reward.discount_percentage / 100), crounding);
                        }
                    }
                }

                if(reward.discount_apply_on === "cheapest_product") {
                    var price;
                    for (var line of this.get_orderlines()){
                        if((!price || price > line.get_unit_price()) && line.product.id !== product.id) {
                            discount = round_pr(line.get_price_with_tax() * (reward.discount_percentage / 100), crounding);
                            price = line.get_unit_price();
                        }
                    }
                }
                if(reward.discount_max_amount !== 0 && discount > reward.discount_max_amount)
                    discount = reward.discount_max_amount;

                this.add_product(product, {
                    price: -discount,
                    quantity: 1,
                    merge: false,
                    extras: { reward_id: reward.id },
                });
            }
            if (reward.discount_type == "fixed_amount") {
                let discount_fixed_amount = reward.discount_fixed_amount;
                let point_cost = reward.point_cost;
                let quantity_to_apply = Math.floor(spendable/point_cost);
                let amount_discounted = discount_fixed_amount * quantity_to_apply;

                if (amount_discounted > order_total) {
                    quantity_to_apply = Math.floor(order_total / discount_fixed_amount);
                }

                this.add_product(product, {
                    price: - discount_fixed_amount,
                    quantity: quantity_to_apply,
                    merge: false,
                    extras: { reward_id: reward.id },
                });

            }
        }
    },

    finalize: function(){
        var client = this.get_client();
        if ( client ) {
            client.loyalty_points = this.get_new_total_points();
        }
        _super.prototype.finalize.apply(this,arguments);
    },

    export_for_printing: function(){
        var json = _super.prototype.export_for_printing.apply(this,arguments);
        if (this.pos.loyalty && this.get_client()) {
            json.loyalty = {
                name:         this.pos.loyalty.name,
                client:       this.get_client().name,
                points_won  : this.get_won_points(),
                points_spent: this.get_spent_points(),
                points_total: this.get_new_total_points(),
            };
        }
        return json;
    },

    export_as_JSON: function(){
        var json = _super.prototype.export_as_JSON.apply(this,arguments);
        json.loyalty_points = this.get_new_points();
        return json;
    },
});

});
