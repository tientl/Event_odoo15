/** @odoo-module */

import { _t } from "web.core";
import DomainSelector from "web.DomainSelector";
import { time_to_str } from "web.time";
import DomainComponentAdapter from "../domain_component_adapter";

export class PivotDetailsSidePanel extends owl.Component {
    constructor() {
        super(...arguments);
        this.getters = this.env.getters;
        this.DomainSelector = DomainSelector;
    }

    get pivotDefinition() {
        const pivotId = this.props.pivotId;
        return {
            model: this.getters.getPivotModel(pivotId),
            modelDisplayName: this.getters.getPivotModelDisplayName(pivotId),
            domain: this.getters.getPivotDomain(pivotId),
            dimensions: this.getters
                .getPivotRowGroupBys(pivotId)
                .concat(this.getters.getPivotColGroupBys(pivotId)),
            measures: this.getters.getPivotMeasures(pivotId),
        };
    }

    /**
     * Get the last update date, formatted
     *
     * @returns {string} date formatted
     */
    getLastUpdate() {
        const lastUpdate = this.getters.getPivotLastUpdate(this.props.pivotId);
        if (lastUpdate) {
            return time_to_str(new Date(lastUpdate));
        }
        return _t("never");
    }

    /**
     * Refresh the cache of the current pivot
     *
     */
    refresh() {
        this.env.dispatch("REFRESH_PIVOT", { id: this.props.pivotId });
    }
}
PivotDetailsSidePanel.template = "documents_spreadsheet.PivotDetailsSidePanel";
PivotDetailsSidePanel.components = { DomainComponentAdapter };
PivotDetailsSidePanel.props = {
    pivotId: {
        type: String,
        optional: true,
    },
};
