/** @odoo-module alias=documents_spreadsheet.spreadsheet_extended */

import "./registries/autofill";
import "./registries/filter_component";
import "./registries/menu_item_registry";
import "./registries/pivot_functions";
import "./registries/list_functions";
import "./../collaborative/operational_transform";

import { _t } from "web.core";
import spreadsheet from "./o_spreadsheet_loader";

/** Core */
import PivotPlugin from "./plugins/core/pivot_plugin";
import ListPlugin from "./plugins/core/list_plugin";
import FiltersPlugin from "./plugins/core/filters_plugin";

/** UI */
import PivotStructurePlugin from "./plugins/ui/pivot_structure_plugin";
import PivotTemplatePlugin from "documents_spreadsheet.PivotTemplatePlugin";
import PivotAutofillPlugin from "./plugins/ui/pivot_autofill_plugin";
import ListStructurePlugin from "./plugins/ui/list_structure_plugin";
import IrMenuPlugin from "./plugins/ui/ir_ui_menu_plugin";


/** Side panels */
import PivotSidePanel from "../../side_panels/pivot/pivot_list_side_panel";
import ListingAllSidePanel from "../../side_panels/list/listing_all_side_panel";
import ListAutofillPlugin from "./plugins/ui/list_autofill_plugin";
import FiltersEvaluationPlugin from "./plugins/ui/filters_evaluation_plugin";

const { coreTypes, invalidateEvaluationCommands, readonlyAllowedCommands } = spreadsheet;
const { corePluginRegistry, uiPluginRegistry, sidePanelRegistry } = spreadsheet.registries;

corePluginRegistry.add("odooPivotPlugin", PivotPlugin);
corePluginRegistry.add("odooListPlugin", ListPlugin);
corePluginRegistry.add("odooFiltersPlugin", FiltersPlugin);

uiPluginRegistry.add("odooPivotStructurePlugin", PivotStructurePlugin);
uiPluginRegistry.add("odooListStructurePlugin", ListStructurePlugin);
uiPluginRegistry.add("odooPivotAutofillPlugin", PivotAutofillPlugin);
uiPluginRegistry.add("odooListAutofillPlugin", ListAutofillPlugin);
uiPluginRegistry.add("odooPivotTemplatePlugin", PivotTemplatePlugin);
uiPluginRegistry.add("odooFiltersEvaluationPlugin", FiltersEvaluationPlugin);
uiPluginRegistry.add("odooIrMenuPlugin", IrMenuPlugin);

coreTypes.add("ADD_PIVOT");
coreTypes.add("ADD_PIVOT_FORMULA");
coreTypes.add("ADD_GLOBAL_FILTER");
coreTypes.add("EDIT_GLOBAL_FILTER");
coreTypes.add("REMOVE_GLOBAL_FILTER");
coreTypes.add("ADD_ODOO_LIST");
coreTypes.add("ADD_ODOO_LIST_FORMULA");

invalidateEvaluationCommands.add("ADD_GLOBAL_FILTER");
invalidateEvaluationCommands.add("EDIT_GLOBAL_FILTER");
invalidateEvaluationCommands.add("REMOVE_GLOBAL_FILTER");
invalidateEvaluationCommands.add("SET_GLOBAL_FILTER_VALUE");

readonlyAllowedCommands.add("SET_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("ADD_PIVOT_DOMAIN");
readonlyAllowedCommands.add("ADD_LIST_DOMAIN");

sidePanelRegistry.add("PIVOT_PROPERTIES_PANEL", {
    title: () => _t("Pivot properties"),
    Body: PivotSidePanel,
});
sidePanelRegistry.add("LIST_PROPERTIES_PANEL", {
    title: () => _t("List properties"),
    Body: ListingAllSidePanel,
});

export default spreadsheet;
