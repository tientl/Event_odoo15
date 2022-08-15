/** @odoo-module **/

import config from "web.config";
import PivotRenderer from "@web/legacy/js/views/pivot/pivot_renderer";
import { PivotGroupByMenu } from "@web/legacy/js/views/pivot/pivot_renderer";
import { patch } from "web.utils";

if (config.device.isMobile) {
    patch(PivotRenderer.prototype, "pivot_mobile", {
        /**
         * Do not compute the tooltip on mobile
         * @override
         */
        _updateTooltip() {},

        /**
         * @override
         */
        _getPadding(cell) {
            return 5 + cell.indent * 5;
        },
    });

    patch(PivotGroupByMenu.prototype, "pivot_mobile", {
        /**
         * @override
         */
        _onClickMenuGroupBy(fieldName, interval, ev) {
            if (!ev.currentTarget.classList.contains("o_pivot_field_selection")) {
                this._super(...arguments);
            } else {
                ev.stopPropagation();
            }
        },
    });
}
