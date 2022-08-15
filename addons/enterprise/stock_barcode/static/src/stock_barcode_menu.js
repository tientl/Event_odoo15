/** @odoo-module **/

import AbstractAction from 'web.AbstractAction';
import core from 'web.core';
import Dialog from 'web.Dialog';
import Session from 'web.session';
import * as BarcodeScanner from '@web_enterprise/webclient/barcode/barcode_scanner';

const _t = core._t;

const MainMenu = AbstractAction.extend({
    contentTemplate: 'main_menu',

    events: {
        "click .button_operations": function () {
            this.do_action('stock_barcode.stock_picking_type_action_kanban');
        },
        "click .button_inventory": function () {
            this._rpc({
                'model': 'stock.quant',
                'method': 'action_client_action',
                'args': [[]],
            }).then(result => {
                this.do_action(result);
            });
        },
        "click .o_stock_barcode_menu": function () {
            this.trigger_up('toggle_fullscreen');
            this.trigger_up('show_home_menu');
        },
        "click .o_stock_mobile_barcode": async function() {
            const barcode = await BarcodeScanner.scanBarcode();
            if (barcode){
                this._onBarcodeScanned(barcode);
                if ('vibrate' in window.navigator) {
                    window.navigator.vibrate(100);
                }
            } else {
                this.displayNotification({
                    type: 'warning',
                    message:_t("Please, Scan again !"),
                });
            }
        }
    },

    init: function (parent, action) {
        this._super(...arguments);
        this.message_demo_barcodes = action.params.message_demo_barcodes;
        this.mobileScanner = BarcodeScanner.isBarcodeScannerSupported();
    },

    willStart: async function () {
        await this._super(...arguments);
        this.group_stock_multi_location = await Session.user_has_group('stock.group_stock_multi_locations');
    },

    start: function() {
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        return this._super().then(() => {
            if (this.message_demo_barcodes) {
                this.setup_message_demo_barcodes();
            }
        });
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._super();
    },

    setup_message_demo_barcodes: function () {
        // Upon closing the message (a bootstrap alert), propose to remove it once and for all
        this.$(".message_demo_barcodes").on('close.bs.alert', () => {
            const message = _t("Do you want to permanently remove this message ?\
                It won't appear anymore, so make sure you don't need the barcodes sheet or you have a copy.");
            const options = {
                title: _t("Don't show this message again"),
                size: 'medium',
                buttons: [
                    {
                        text: _t("Remove it"),
                        close: true,
                        classes: 'btn-primary',
                        click: function () {
                            Session.rpc('/stock_barcode/rid_of_message_demo_barcodes');
                        },
                    },
                    { text: _t("Leave it"), close: true }
                ],
            };
            Dialog.confirm(this, message, options);
        });
    },

    _onBarcodeScanned: function (barcode) {
        if (!$.contains(document, this.el)) {
            return;
        }
        Session.rpc('/stock_barcode/scan_from_main_menu', { barcode }).then(result => {
            if (result.action) {
                this.do_action(result.action);
            } else if (result.warning) {
                this.displayNotification({ title: result.warning, type: 'danger' });
            }
        });
    },
});

core.action_registry.add('stock_barcode_main_menu', MainMenu);

export default MainMenu;
