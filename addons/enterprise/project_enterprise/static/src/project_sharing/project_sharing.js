/** @odoo-module **/

import { hasTouch } from '@web/core/browser/feature_detection';
import { ProjectSharingWebClient } from '@project/project_sharing/project_sharing';

const { hooks } = owl;

export class ProjectSharingWebClientEnterprise extends ProjectSharingWebClient {
    setup() {
        super.setup();
        hooks.onMounted(() => {
            this.el.classList.toggle('o_touch_device', hasTouch());
        });
    }
}

ProjectSharingWebClientEnterprise.components = { ...ProjectSharingWebClient.components };
