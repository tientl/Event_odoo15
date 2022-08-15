/** @odoo-module alias=planning.Calendar **/

import { qweb as QWeb } from 'web.core';

import CalendarPopover from 'web.CalendarPopover';
import CalendarRenderer from 'web.CalendarRenderer';
import CalendarView from 'web.CalendarView';
import fieldUtils from 'web.field_utils';
import view_registry from 'web.view_registry';

    var PlanningCalendarPopover = CalendarPopover.extend({
        template: 'Planning.event.popover',

        init () {
            this._super(...arguments);
            this.allocated_hours = fieldUtils.format.float_time(this.event.extendedProps.record.allocated_hours);
            this.allocated_percentage = fieldUtils.format.float(this.event.extendedProps.record.allocated_percentage);
        },

        willStart: function() {
            const self = this;
            const check_group = this.getSession().user_has_group('planning.group_planning_manager').then(function(has_group) {
                self.is_manager = has_group;
            });
            return Promise.all([this._super.apply(this, arguments), check_group]);
        },

        renderElement: function () {
            let render = $(QWeb.render(this.template, { widget: this }));
            if(!this.is_manager) {
                render.find('.card-footer').remove();
            }

            this._replaceElement(render);
        },

        /**
         * Hide empty fields from the calendar popover
         * @override
         */
        _processFields: function () {
            var self = this;

            if (!CalendarPopover.prototype.origDisplayFields) {
                CalendarPopover.prototype.origDisplayFields = _.extend({}, this.displayFields);
            } else {
                this.displayFields = _.extend({}, CalendarPopover.prototype.origDisplayFields);
            }

            _.each(this.displayFields, function(def, field) {
                if (self.event.extendedProps && self.event.extendedProps.record && !self.event.extendedProps.record[field]) {
                    delete self.displayFields[field];
                } 
            });

            return this._super.apply(this, arguments);
        }
    });

    var PlanningCalendarRenderer = CalendarRenderer.extend({
        config: _.extend({}, CalendarRenderer.prototype.config, {
            CalendarPopover: PlanningCalendarPopover,
        }),
    });

    var PlanningCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Renderer: PlanningCalendarRenderer,
        }),
    });

    view_registry.add('planning_calendar', PlanningCalendarView);
