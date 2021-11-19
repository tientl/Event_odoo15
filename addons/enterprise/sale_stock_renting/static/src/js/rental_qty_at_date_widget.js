odoo.define('sale_stock_renting.QtyAtDateWidget', function (require) {
"use strict";

const core = require('web.core');
const QWeb = core.qweb;

const Context = require('web.Context');
const data_manager = require('web.data_manager');
const time = require('web.time');

const QtyAtDateWidget = require('sale_stock.QtyAtDateWidget');

QtyAtDateWidget.include({

    /**
     * Redirect to the product gantt view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onRentalGanttView(ev) {
        ev.stopPropagation();
        const action = await data_manager.load_action('sale_renting.action_rental_order_schedule');
        const additional_context = {restrict_renting_products: true};
        action.context = new Context(action.context, additional_context);
        action.domain = [
            ['product_id', '=', this.data.product_id.data.id]
        ];
        return this.do_action(action);
    },

    _getContent() {
        if (!this.data.is_rental) {
            return this._super();
        }
        this.data.end_date = this.data.return_date.clone().add(this.getSession().getTZOffset(this.data.return_date), 'minutes').format(time.getLangDateFormat());
        this.data.start_date = this.data.pickup_date.clone().add(this.getSession().getTZOffset(this.data.pickup_date), 'minutes').format(time.getLangDateFormat());
        const $content = $(QWeb.render('sale_stock_renting.QtyDetailPopOver', {
            data: this.data,
        }));
        $content.on('click', '.action_open_renting', this._onRentalGanttView.bind(this));

        return $content;
    },

});

});
