odoo.define("web_dashboard/static/src/js/dashboard_model_extension.js", function (require) {
    "use strict";

    const ActionModel = require("web.ActionModel");

    const DASHBOARD_FACET_ID = "dashboard";

    class DashboardModelExtension extends ActionModel.Extension {

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * @override
         */
        prepareState() {
            this.state.domain = null;
            this.state.facets = null;
        }

        /**
         * @override
         * @returns {any}
         */
        get(property) {
            switch (property) {
                case "domain": return this.getDomain();
                case "facets": return this.getFacets();
            }
        }

        //---------------------------------------------------------------------
        // Actions / Getters
        //---------------------------------------------------------------------

        /**
         * Removes the dashboard group facet if the right ID is given.
         * @param {number | string} groupId
         */
        deactivateGroup(groupId) {
            if (groupId === DASHBOARD_FACET_ID) {
                this.state.domain = null;
                this.state.facets = null;
            }
        }

        /**
         * Returns the current dashboard domain.
         * @returns {Array[] | null}
         */
        getDomain() {
            return this.state.domain;
        }

        /**
         * Returns the current dashboard facet.
         * @returns {Object | null}
         */
        getFacets() {
            return this.state.facets;
        }

        /**
         * Updates the current dashboard domain and creates a facet based on
         * the given label.
         * @param {Object} params
         * @param {Array[]} params.domain
         * @param {string} params.label
         */
        updateDashboardDomain({ domain, label }) {
            this.state.domain = domain || null;
            if (domain) {
                const facet = {
                    groupId: DASHBOARD_FACET_ID,
                    type: "filter",
                    values: [label],
                };
                this.state.facets = [facet];
            } else {
                this.state.facets = null;
            }
        }
    }

    ActionModel.registry.add("Dashboard", DashboardModelExtension, 50);
});
