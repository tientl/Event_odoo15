/** @odoo-module **/

/**
 * This file can be removed as soon as voip code will be converted to owl.
 */

import { browser } from "@web/core/browser/browser";
import { ComponentAdapter } from "web.OwlCompatibility";
import core from "web.core";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";

const serviceRegistry = registry.category("services");

const { Component } = owl;
const { EventBus } = owl.core;

/**
 * Specialization of a ComponentAdapter for the DialingPanel. Uses the voip
 * service to toggle the legacy DialingPanel.
 */
export class DialingPanelAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.voipLegacy = useService('voip_legacy');

        this.env = Component.env;

        this.props.bus.on('TOGGLE_DIALING_PANEL', this, () => {
            core.bus.trigger('voip_onToggleDisplay');
        });

        this.voipLegacy.bus.on('VOIP-CALL', this, (data) => {
            this.widget.callFromPhoneWidget(data);
        });
        this.voipLegacy.bus.on('VOIP-ACTIVITY-CALL', this, (data) => {
            this.widget.callFromActivityWidget(data);
        });
        this.voipLegacy.bus.on('GET-PBX-CONFIGURATION', this, (callback) => {
            callback({
                pbxConfiguration: this.widget.getPbxConfiguration(),
            });
        });
    }
}

/**
 * Service that redirects events triggered up by e.g. the FieldPhone to the
 * DialingPanel.
 */
export const voipLegacyCompatibilityService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const bus = new EventBus();

        browser.addEventListener("voip-call", (ev) => {
            notification.add(sprintf(env._t("Calling %s"), ev.detail.number));
            bus.trigger('VOIP-CALL', ev.detail);
        });
        browser.addEventListener("voip-activity-call", (ev) => {
            bus.trigger('VOIP-ACTIVITY-CALL', ev.detail);
        });
        browser.addEventListener("get-pbx-configuration", (ev) => {
            bus.trigger('GET-PBX-CONFIGURATION', ev.detail.callback);
        });

        return { bus };
    },
};
serviceRegistry.add("voip_legacy", voipLegacyCompatibilityService);
