/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";

patch(ProjectControlPanel, "project_enterprise.ProjectControlPanel", {
    template: "project_enterprise.ProjectControlPanel",
});
