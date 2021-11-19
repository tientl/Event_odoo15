/** @odoo-module **/

import { DashboardView } from "@web_dashboard/dashboard_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

/**
 * This file defines the WebsiteSaleDashboard view and adds it to the view registry.
 * The only difference with Dashboard View is that it has a control panel with a
 * "Go to website" button.
 */
export class WebsiteSaleDashboardView extends DashboardView {}
WebsiteSaleDashboardView.template = "website_sale_dashboard.WebsiteSaleDashboardView";

viewRegistry.add('website_sale_dashboard', WebsiteSaleDashboardView);
