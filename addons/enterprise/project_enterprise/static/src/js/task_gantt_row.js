/** @odoo-module **/

import GanttRow from 'web_gantt.GanttRow';
import { getDateFormatForScale } from "./task_gantt_utils";


const TaskGanttRow = GanttRow.extend({
    template: 'TaskGanttMilestonesView.Row',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
    */
    _prepareSlots: function () {
        this._super(...arguments);
        let dateFormat = getDateFormatForScale(this.SCALES[this.state.scale]);
        this.slots.forEach((slot) => {
            const slotKey = slot.start.format(dateFormat);
            slot.milestonesInfo = this.viewInfo.slotsMilestonesDict[slotKey];
        });
    },
});

export default TaskGanttRow;
