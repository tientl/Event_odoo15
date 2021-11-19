/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';
import '@crm/js/systray_activity_menu';

ActivityMenu.include({
    //--------------------------------------------------
    // Private
    //--------------------------------------------------
    /**
     * @override
     */
    _getViewsList(model) {
        if (model === "crm.lead") {
            return [[false, 'list'], [false, 'kanban'],
                    [false, 'form'],[false, 'calendar'],
                    [false, 'pivot'], [false, 'graph'],
                    [false, 'cohort'], [false, 'dashboard'],
                    [false, 'map'], [false, 'activity']
                ];
        }
        return this._super(...arguments);
    },
});
