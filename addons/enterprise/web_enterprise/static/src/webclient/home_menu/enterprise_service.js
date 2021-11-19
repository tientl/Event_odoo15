/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const enterpriseService = {
    name: "enterprise",
    dependencies: [],
    start() {
        return {
            expirationDate: session.expiration_date,
            expirationReason: session.expiration_reason,
            // Hack: we need to know if there is at least an app installed (except from App and
            // Settings). We use mail to do that, as it is a dependency of almost every addon. To
            // determine whether mail is installed or not, we check for the presence of the key
            // "notification_type" in session_info, as it is added in mail for internal users.
            isMailInstalled: "notification_type" in session,
            warning: session.warning,
        };
    },
};

registry.category("services").add("enterprise", enterpriseService);
