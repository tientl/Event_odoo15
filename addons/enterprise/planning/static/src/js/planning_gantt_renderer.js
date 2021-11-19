odoo.define('planning.PlanningGanttRenderer', function (require) {
    'use strict';

    const HrGanttRenderer = require('hr_gantt.GanttRenderer');
    const PlanningGanttRow = require('planning.PlanningGanttRow');
    const fieldUtils = require('web.field_utils');

    const PlanningGanttRenderer = HrGanttRenderer.extend({
        config: Object.assign({}, HrGanttRenderer.prototype.config, {
            GanttRow: PlanningGanttRow
        }),

        sampleDataTargets: [
            '.o_gantt_row[data-from-server=true]',
        ],
        async _renderView() {
            await this._super(...arguments);
            this.el.classList.add('o_planning_gantt');
        },

        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.addClass('o_planning_gantt');
            });
        },

        _renderRows: function (rows, groupedBy) {
            const rowWidgets = this._super(rows, groupedBy);

            rowWidgets.forEach(rowWidget => {
                this._generatePillLabels(rowWidget.pills, rowWidget.state.scale);
            });

            return rowWidgets;
        },

        /**
         * This function will add a 'label' property to each
         * non-consolidated pill included in the pills list.
         * This new property is a string meant to replace
         * the text displayed on a pill.
         *
         * @private
         * @param {Object} pills
         * @param {string} scale
         */
        _generatePillLabels: function (pills, scale) {

            // as localized yearless date formats do not exists yet in momentjs,
            // this is an awful surgery adapted from SO: https://stackoverflow.com/a/29641375
            // The following regex chain will:
            //  - remove all 'Y'(ignoring case),
            //  - then remove duplicate consecutives separators,
            //  - and finally remove trailing orphaned separators left
            const dateFormat = moment.localeData().longDateFormat('l');
            const yearlessDateFormat = dateFormat.replace(/Y/gi, '').replace(/(\W)\1+/g, '$1').replace(/^\W|\W$/, '');

            pills.filter(pill => !pill.consolidated).forEach(pill => {

                const localStartDateTime = (pill.start_datetime || pill.startDate).clone().local();
                const localEndDateTime = (pill.end_datetime || pill.stopDate).clone().local();

                const spanAccrossDays = localStartDateTime.clone().startOf('day')
                    .diff(localEndDateTime.clone().startOf('day'), 'days') != 0;

                const spanAccrossWeeks = localStartDateTime.clone().startOf('week')
                    .diff(localEndDateTime.clone().startOf('week'), 'weeks') != 0;

                const spanAccrossMonths = localStartDateTime.clone().startOf('month')
                    .diff(localEndDateTime.clone().startOf('month'), 'months') != 0;

                const labelElements = [];

                // Start & End Dates
                if (scale === 'year' && !spanAccrossDays) {
                    labelElements.push(localStartDateTime.format(yearlessDateFormat));
                } else if (
                    (scale === 'day' && spanAccrossDays) ||
                    (scale === 'week' && spanAccrossWeeks) ||
                    (scale === 'month' && spanAccrossMonths) ||
                    (scale === 'year' && spanAccrossDays)
                ) {
                    labelElements.push(localStartDateTime.format(yearlessDateFormat));
                    labelElements.push(localEndDateTime.format(yearlessDateFormat));
                }

                // Start & End Times
                if (!spanAccrossDays && ['week', 'month'].includes(scale)) {
                    labelElements.push(
                        localStartDateTime.format('LT'),
                        localEndDateTime.format('LT') + ' (' + fieldUtils.format.float_time(pill.allocated_hours, {}, {noLeadingZeroHour: true}).replace(/(:00|:)/g, 'h') + ')'
                    );
                }

                // Original Display Name
                if (scale !== 'month' || spanAccrossDays) {
                    labelElements.push(pill.display_name);
                }

                pill.label = labelElements.filter(el => !!el).join(' - ');

            });

        },
        /**
         * Get pillsInfo with the planning hours info
         *
         * @param {Object} row
         * @param {*} groupLevel
         */
        _getPillsInfo: function (row, groupLevel) {
            return {
                ...this._super.apply(this, arguments),
                planningHoursInfo: row.planningHoursInfo,
            };
        },
    });

    return PlanningGanttRenderer;
});
