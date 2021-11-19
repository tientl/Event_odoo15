/** @odoo-module **/

import StandaloneM2OAvatarEmployee from '@hr/js/standalone_m2o_avatar_employee';
import { qweb, _t } from 'web.core';
import fieldUtils from 'web.field_utils';

const EmployeeWithPlannedHours = StandaloneM2OAvatarEmployee.extend({
    hoursTemplate: 'planning.Many2OneAvatarPlannedHours',

    init(parent, value, planningHoursInfo) {
        this._super(...arguments);
        this.hasAllTheRequiredData = true;
        if (planningHoursInfo) {
            this.cacheWorkHours = planningHoursInfo['work_hours'];
            this.cachePlannedHours = planningHoursInfo['planned_hours'];
        } else {
            this.hasAllTheRequiredData = false;
        }
    },

    start() {
        if (this.hasAllTheRequiredData) {
            this._updateTemplateFromCacheData();
            this.$el.append(this.$templateHtml);
            this.$el.addClass('o_planning_gantt_employee_progress');
        }
        return this._super(...arguments).then(() => {
            this._muteJobTitle(this.$el.find(".o_m2o_avatar span:first"));
        });
    },

    _muteJobTitle(span) {
        const text = span.text();
        const jobTitleRegexp = /^(.*)(\(.*\))$/;
        const jobTitleMatch = text.match(jobTitleRegexp);
        if (jobTitleMatch) {
            span.empty();
            span.append(document.createTextNode(jobTitleMatch[1]));
            const textMuted = document.createElement('span');
            textMuted.className = 'text-muted';
            textMuted.appendChild(document.createTextNode(jobTitleMatch[2]));
            span.append(textMuted);
        }
    },

    /**
     * Generate (qweb render) the template from the attribute values.
     */
    _updateTemplateFromCacheData() {
        const plannedHours = fieldUtils.format.float(this.cachePlannedHours, {'digits': [false, 0]});
        this.$templateHtml = $(qweb._render(this.hoursTemplate, {
            'width': Math.min(this.cachePlannedHours / (this.cacheWorkHours || this.cachePlannedHours || 1) * 100, 100), // avoid NaN
            'is_overplanned': this.cachePlannedHours > this.cacheWorkHours,
            'planned_hours': plannedHours,
            'work_hours': fieldUtils.format.float(this.cacheWorkHours, {'digits': [false, 0]}),
            'expected_to_work': this.cacheWorkHours > 0,
            'no_work_hours_title': _.str.sprintf(
                _t("This employee isn't expected to work during this period. Planned hours : %s hours"),
                plannedHours
            )
        }));
    },
});

export default EmployeeWithPlannedHours;
