/** @odoo-module **/

// -----------------------------------------------------------------------------
// Mock Services
// -----------------------------------------------------------------------------

export function makeFakeEnterpriseService(params = {}) {
    return {
        name: "enterprise",
        dependencies: [],
        start() {
            return {
                warning: "warning" in params ? params.warning : false,
                expirationDate: "expirationDate" in params ? params.expirationDate : false,
                expirationReason: "expirationReason" in params ? params.expirationReason : false,
                isMailInstalled: "isMailInstalled" in params ? params.isMailInstalled : false,
            };
        },
    };
}
