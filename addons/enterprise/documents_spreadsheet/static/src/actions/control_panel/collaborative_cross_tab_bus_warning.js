/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService, useEffect } from "@web/core/utils/hooks";

const WARNING_DELAY = 5000;

/**
 * Warn the user after 5s if the spreadsheet is still saving.
 * Closing other tabs might solve the issue.
 * @param {() => boolean} isSaving
 */
export function useAutoSavingWarning(isSaving) {
    const notifications = useService("notification");
    const actions = useService("action");
    /** @type {function | undefined} */
    let close;
    useEffect(
        () => {
            if (!isSaving()) {
                close && close();
                return;
            }
            const timeoutId = browser.setTimeout(checkSavingStatus, WARNING_DELAY);

            function checkSavingStatus() {
                close = notifications.add(
                    _t("Please, close all other Odoo tabs and reload the current page."),
                    {
                        title: _t("An issue occurred while auto-saving"),
                        sticky: true,
                        type: "danger",
                        buttons: [
                            {
                                name: _t("Reload"),
                                primary: true,
                                onClick: () => actions.doAction("reload_context"),
                            },
                        ],
                    }
                );
            }
            return () => browser.clearTimeout(timeoutId);
        },
        () => [isSaving()]
    );
}
