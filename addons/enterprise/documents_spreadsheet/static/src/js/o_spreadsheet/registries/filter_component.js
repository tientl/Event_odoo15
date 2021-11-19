/** @odoo-module alias=documents_spreadsheet.filter_component **/

import spreadsheet from "../o_spreadsheet_loader";

const { Component } = owl;
const { Menu } = spreadsheet;
const { topbarComponentRegistry } = spreadsheet.registries;

class FilterComponent extends Component {
    get activeFilter() {
        return this.env.getters.getActiveFilterCount();
    }

    toggleDropdown() {
        this.env.toggleSidePanel("GLOBAL_FILTERS_SIDE_PANEL");
    }
}

FilterComponent.template = "documents_spreadsheet.FilterComponent";

FilterComponent.components = { Menu };

topbarComponentRegistry.add("filter_component", {
    component: FilterComponent,
    isVisible: (env) => {
        return (!env.getters.isReadonly() && (env.getters.getPivotIds().length + env.getters.getListIds().length)) ||
        (env.getters.isReadonly() && env.getters.getGlobalFilters().length)
    },
});
