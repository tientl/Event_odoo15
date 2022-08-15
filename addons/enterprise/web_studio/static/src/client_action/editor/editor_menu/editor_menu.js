/** @odoo-module */

import { useBus, useService } from "@web/core/utils/hooks";
import { _lt } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";

const editorTabRegistry = registry.category("web_studio.editor_tabs");

export class EditorMenu extends owl.Component {
    setup() {
        this.l10n = localization;
        this.studio = useService("studio");
        this.rpc = useService("rpc");

        useBus(this.studio.bus, "UPDATE", async () => {
            await this.render();
            toggleSnackBar("off");
        });

        const toggleUndo = (display) => {
            const el = this.el.querySelector(".o_web_studio_undo");
            if (el) {
                el.classList.toggle("o_web_studio_active", display);
            }
        };
        const toggleRedo = (display) => {
            const el = this.el.querySelector(".o_web_studio_redo");
            if (el) {
                el.classList.toggle("o_web_studio_active", display);
            }
        };

        useBus(this.studio.bus, "undo_available", () => toggleUndo(true));
        useBus(this.studio.bus, "undo_not_available", () => toggleUndo(false));
        useBus(this.studio.bus, "redo_available", () => toggleRedo(true));
        useBus(this.studio.bus, "redo_not_available", () => toggleRedo(false));

        const toggleSnackBar = (type) => {
            const snackBarIcon = this.el.querySelector(".o_web_studio_snackbar_icon");
            const snackBarText = this.el.querySelector(".o_web_studio_snackbar_text");
            switch (type) {
                case "saved":
                    snackBarIcon.classList.remove("fa-circle-o-notch", "fa-spin");
                    snackBarIcon.classList.add("show", "fa", "fa-check");
                    snackBarText.textContent = this.env._t("Saved");
                    break;
                case "saving":
                    snackBarIcon.classList.add("show", "fa", "fa-circle-o-notch", "fa-spin");
                    snackBarText.textContent = this.env._t("Saving");
                    break;
                case "off":
                    snackBarIcon.classList.remove(
                        "fa-circle-o-notch",
                        "fa-spin",
                        "show",
                        "fa-check"
                    );
                    snackBarText.textContent = "";
                    break;
            }
        };

        useBus(this.studio.bus, "toggle_snack_bar", toggleSnackBar);
    }

    get breadcrumbs() {
        const { editorTab } = this.studio;
        const currentTab = this.editorTabs.find((tab) => tab.id === editorTab);
        const crumbs = [
            {
                name: currentTab.name,
                handler: () => this.openTab(currentTab.id),
            },
        ];
        if (currentTab.id === "views") {
            const { editedViewType, x2mEditorPath } = this.studio;
            if (editedViewType) {
                const currentViewType = this.constructor.viewTypes.find(
                    (vt) => vt.type === editedViewType
                );
                crumbs.push({
                    name: currentViewType.title,
                    handler: () =>
                        this.studio.setParams({
                            x2mEditorPath: [],
                        }),
                });
            }
            x2mEditorPath.forEach(({ x2mViewType }, index) => {
                const viewType = this.constructor.viewTypes.find((vt) => vt.type === x2mViewType);
                crumbs.push({
                    name: sprintf(
                        this.env._t("Subview %s"),
                        (viewType && viewType.title) || this.env._t("Other")
                    ),
                    handler: () =>
                        this.studio.setParams({
                            x2mEditorPath: x2mEditorPath.slice(0, index + 1),
                        }),
                });
            });
        } else if (currentTab.id === "reports" && this.studio.editedReport) {
            crumbs.push({
                name: this.studio.editedReport.data.name,
                handler: () => this.studio.setParams({}),
            });
        }
        return crumbs;
    }

    get activeViews() {
        const action = this.studio.editedAction;
        const viewTypes = (action._views || action.views).map(([id, type]) => type);
        return this.constructor.viewTypes.filter((vt) => viewTypes.includes(vt.type));
    }

    get editorTabs() {
        const entries = editorTabRegistry.getEntries();
        return entries.map((entry) => Object.assign({}, entry[1], { id: entry[0] }));
    }

    openTab(tab) {
        this.trigger("switch-tab", { tab });
    }
}
EditorMenu.template = "web_studio.EditorMenu";
EditorMenu.viewTypes = [
    {
        title: _lt("Form"),
        type: "form",
        faclass: "fa-address-card",
    },
    {
        title: _lt("List"),
        type: "list",
        faclass: "fa-list-ul",
    },
    {
        title: _lt("Kanban"),
        type: "kanban",
        faclass: "fa-th-large",
    },
    {
        title: _lt("Map"),
        type: "map",
        faclass: "fa-map-marker",
    },
    {
        title: _lt("Calendar"),
        type: "calendar",
        faclass: "fa-calendar-o",
    },
    {
        title: _lt("Graph"),
        type: "graph",
        faclass: "fa-bar-chart",
    },
    {
        title: _lt("Pivot"),
        type: "pivot",
        faclass: "fa-table",
    },
    {
        title: _lt("Gantt"),
        type: "gantt",
        faclass: "fa-tasks",
    },
    {
        title: _lt("Dashboard"),
        type: "dashboard",
        faclass: "fa-tachometer",
    },
    {
        title: _lt("Cohort"),
        type: "cohort",
        faclass: "fa-signal",
    },
    {
        title: _lt("Activity"),
        type: "activity",
        faclass: "fa-th",
    },
    {
        title: _lt("Search"),
        type: "search",
        faclass: "fa-search",
    },
];

editorTabRegistry
    .add("views", { name: _lt("Views"), action: "web_studio.action_editor" })
    .add("reports", { name: _lt("Reports") })
    .add("translations", { name: _lt("Translations") })
    .add("automations", { name: _lt("Automations") })
    .add("acl", { name: _lt("Access Control") })
    .add("filters", { name: _lt("Filter Rules") });
