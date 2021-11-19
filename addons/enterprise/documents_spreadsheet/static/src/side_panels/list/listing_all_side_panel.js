/** @odoo-module */

import { ListingDetailsSidePanel } from "./listing_details_side_panel";

export default class ListingAllSidePanel extends owl.Component {
    constructor() {
        super(...arguments);
        this.getters = this.env.getters;
    }

    selectListing(listId) {
        this.env.dispatch("SELECT_ODOO_LIST", { listId });
    }

    resetListingSelection() {
        this.env.dispatch("SELECT_ODOO_LIST");
    }
}
ListingAllSidePanel.template = "documents_spreadsheet.ListingAllSidePanel";
ListingAllSidePanel.components = { ListingDetailsSidePanel };
