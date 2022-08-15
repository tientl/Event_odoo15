odoo.define('hr_appraisal.appraisal_kanban', function (require) {
'use strict';

const viewRegistry = require('web.view_registry');
const KanbanController = require('web.KanbanController');
const KanbanView = require('web.KanbanView');
const KanbanRenderer = require('web.KanbanRenderer');
const KanbanRecord = require('web.KanbanRecord');

const { Component } = owl;

const AppraisalKanbanRecord = KanbanRecord.extend({
    _render: async function () {
        const self = this;
        await this._super.apply(this, arguments);
        _.each(this.$el.find('.o_appraisal_manager'), employee => {
            $(employee).on('click', self._onOpenChat.bind(self));
        });
    },

    async _onOpenChat(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const messaging = await Component.env.services.messaging.get();
        messaging.openChat({ employeeId: $(ev.target).data('id') });
    },
});

const AppraisalKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanRecord: AppraisalKanbanRecord,
    }),
});

const AppraisalKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: KanbanController,
        Renderer: AppraisalKanbanRenderer,
    }),
});

viewRegistry.add('appraisal_kanban', AppraisalKanbanView);
return {
    AppraisalKanbanView: AppraisalKanbanView,
    AppraisalKanbanRecord: AppraisalKanbanRecord,
    AppraisalKanbanRenderer: AppraisalKanbanRenderer,
};
});
