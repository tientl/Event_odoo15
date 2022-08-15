/** @odoo-module **/

import { SearchPanel } from "@web/search/search_panel/search_panel";
import { patch } from "@web/core/utils/patch";

const { Portal } = owl.misc;

//-------------------------------------------------------------------------
// Helpers
//-------------------------------------------------------------------------

const isFilter = (s) => s.type === "filter";
const isActiveCategory = (s) => s.type === "category" && s.activeValueId;

/**
 * @param {Map<string | false, Object>} values
 * @returns {Object[]}
 */
const nameOfCheckedValues = (values) => {
    const names = [];
    for (const [, value] of values) {
        if (value.checked) {
            names.push(value.display_name);
        }
    }
    return names;
};

patch(SearchPanel.prototype, "web_enterprise.SearchPanel", {
    setup() {
        this._super(...arguments);
        this.state.showMobileSearch = false;
    },

    //-----------------------------------------------------------------
    // Protected
    //-----------------------------------------------------------------

    /**
     * Returns a formatted version of the active categories to populate
     * the selection banner of the control panel summary.
     * @returns {Object[]}
     */
    getCategorySelection() {
        const activeCategories = this.env.searchModel.getSections(isActiveCategory);
        const selection = [];
        for (const category of activeCategories) {
            const parentIds = this.getAncestorValueIds(category, category.activeValueId);
            const orderedCategoryNames = [...parentIds, category.activeValueId].map(
                (valueId) => category.values.get(valueId).display_name
            );
            selection.push({
                values: orderedCategoryNames,
                icon: category.icon,
                color: category.color,
            });
        }
        return selection;
    },

    /**
     * Returns a formatted version of the active filters to populate
     * the selection banner of the control panel summary.
     * @returns {Object[]}
     */
    getFilterSelection() {
        const filters = this.env.searchModel.getSections(isFilter);
        const selection = [];
        for (const { groups, values, icon, color } of filters) {
            let filterValues;
            if (groups) {
                filterValues = Object.keys(groups)
                    .map((groupId) => nameOfCheckedValues(groups[groupId].values))
                    .flat();
            } else if (values) {
                filterValues = nameOfCheckedValues(values);
            }
            if (filterValues.length) {
                selection.push({ values: filterValues, icon, color });
            }
        }
        return selection;
    },
});

patch(SearchPanel, "web_enterprise.SearchPanel", {
    template: "web_enterprise.SearchPanel",
    components: {
        ...SearchPanel.components,
        Portal,
    },
});
