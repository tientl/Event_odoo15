odoo.define('documents.DocumentsKanbanView', function (require) {
'use strict';

/**
 * This file defines the DocumentsKanbanView, a JS extension of the KanbanView
 * to deal with documents.
 *
 * Warning: there is no groupby menu in this view as it doesn't support the
 * grouped case. Its elements assume that the data isn't grouped.
 */

const DocumentsKanbanController = require('documents.DocumentsKanbanController');
const DocumentsKanbanModel = require('documents.DocumentsKanbanModel');
const DocumentsKanbanRenderer = require('documents.DocumentsKanbanRenderer');
const DocumentsSearchPanel = require('documents.DocumentsSearchPanel');
const DocumentsViewMixin = require('documents.viewMixin');

const KanbanView = require('web.KanbanView');
const viewRegistry = require('web.view_registry');

const { _lt } = require('web.core');

const DocumentsKanbanView = KanbanView.extend(DocumentsViewMixin, {
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: DocumentsKanbanController,
        Model: DocumentsKanbanModel,
        Renderer: DocumentsKanbanRenderer,
        SearchPanel: DocumentsSearchPanel,
    }),
    display_name: _lt('Attachments Kanban'),
    searchMenuTypes: ['filter', 'favorite'],
});

viewRegistry.add('documents_kanban', DocumentsKanbanView);

return DocumentsKanbanView;

});
