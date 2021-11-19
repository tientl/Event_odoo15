/** @odoo-module **/

import config from 'web.config';
import { patch } from 'web.utils';
import { RightPanelControllerMixin } from '@project/js/right_panel/project_right_panel_mixin';
import ProjectRightPanel from '@project/js/right_panel/project_right_panel';
const { useState } = owl.hooks;

if (config.device.isMobile) {
    patch(RightPanelControllerMixin, 'project_enterprise.project_right_panel_mixin', {
        rightPanelPosition: 'first-child',
    });

    patch(ProjectRightPanel.prototype, 'project_enterprise.ProjectRightPanel', {
        setup() {
            this._super(...arguments);
            this.section = useState({
                sold: {
                    closed: true,
                },
                total_sold: {
                    closed: true,
                },
                milestone: {
                    closed: true,
                }
            });
        },
        _onClickSection(event) {
            const sectionName = $(event.target).closest(".o_rightpanel_section").attr("name");
            this.section[sectionName].closed = !this.section[sectionName].closed;
        },
    });

    patch(ProjectRightPanel, 'project_enterprise.ProjectRightPanel', {
        template: 'project_enterprise.ProjectRightPanel',
    });
}
