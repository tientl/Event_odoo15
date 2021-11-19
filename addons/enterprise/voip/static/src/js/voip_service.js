/** @odoo-module **/

import { registry } from "@web/core/registry";

import { VoipSystrayItem } from "./voip_systray_item";
import { DialingPanelContainer } from "./dialing_panel_container";

const { EventBus } = owl.core;

const serviceRegistry = registry.category("services");
const systrayRegistry = registry.category("systray");
const mainComponentRegistry = registry.category("main_components");

/**
 * Service that conditionally enables the voip feature (if the user is an
 * employee) and exports a bus allowing voip components (systray item, dialing
 * panel) to communicate with each other.
 */
export const voipService = {
    dependencies: ["user"],
    async start(env, { user }) {
        const isEmployee = await user.hasGroup('base.group_user');
        if (isEmployee) {
            const bus = new EventBus();
            systrayRegistry.add('voip', { Component: VoipSystrayItem, props: { bus } });
            mainComponentRegistry.add('voip.DialingPanelContainer', {
                Component: DialingPanelContainer,
                props: { bus },
            });
        }
    },
};

serviceRegistry.add("voip", voipService);
