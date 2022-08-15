/** @odoo-module **/

import MainComponent from '@stock_barcode/components/main';
import { patch } from 'web.utils';

patch(MainComponent.prototype, 'stock_barcode_quality_control', {
    get hasQualityChecksTodo() {
        return this.env.model.record && this.env.model.record.quality_check_todo;
    },

    async checkQuality(ev) {
        ev.stopPropagation();
        await this.env.model.save();
        const res = await this.orm.call(
            this.props.model,
            this.env.model.openQualityChecksMethod,
            [[this.props.id]]
        );
        if (typeof res === 'object' && res !== null) {
            return this.trigger('do-action', {
                action: res,
                options: {
                    on_close: this._onRefreshState.bind(this, {detail : {recordId: this.props.id}}),
                },
            });
        } else {
            this._onNotification({
                message: this.env._t("All the quality checks have been done"),
            });
        }
    },
});
