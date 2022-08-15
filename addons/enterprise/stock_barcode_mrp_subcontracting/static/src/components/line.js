/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from 'web.utils';

patch(LineComponent.prototype, 'stock_barcode_mrp_subcontracting', {
    async showSubcontractingDetails() {
        const {action, options} = await this.env.model._getActionSubcontractingDetails(this.line);
        options.on_close = function (ev) {
            if (ev === undefined) {
                this._onRefreshState.call(this, {detail: {recordId: this.props.id}});
            }
        };
        await this.trigger('do-action', {action, options});
    },
});