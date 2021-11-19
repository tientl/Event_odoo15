/** @odoo-module **/

import MapView from 'web_map.MapView';
import { ProjectControlPanel } from '@project/js/project_control_panel';
import viewRegistry from 'web.view_registry';

export const ProjectMapView = MapView.extend({
    config: Object.assign({}, MapView.prototype.config, {
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('project_map', ProjectMapView);
