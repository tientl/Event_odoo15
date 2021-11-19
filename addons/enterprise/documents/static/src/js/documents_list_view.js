odoo.define('documents.DocumentsListView', function (require) {
"use strict";

/**
 * This file defines the DocumentsListView, a JS extension of the ListView to
 * deal with documents.
 *
 * Warning: there is no groupby menu in this view as it doesn't support the
 * grouped case. Its elements assume that the data isn't grouped.
 */

const DocumentsListController = require('documents.DocumentsListController');
const DocumentsListModel = require('documents.DocumentsListModel');
const DocumentsListRenderer = require('documents.DocumentsListRenderer');
const DocumentsSearchPanel = require('documents.DocumentsSearchPanel');
const DocumentsView = require('documents.viewMixin');

const ListView = require('web.ListView');
const viewRegistry = require('web.view_registry');

const DocumentsListView = ListView.extend(DocumentsView, {
    config: Object.assign({}, ListView.prototype.config, {
        Controller: DocumentsListController,
        Model: DocumentsListModel,
        Renderer: DocumentsListRenderer,
        SearchPanel: DocumentsSearchPanel,
    }),
    searchMenuTypes: ['filter', 'favorite'],
});

viewRegistry.add('documents_list', DocumentsListView);

return DocumentsListView;

});
