odoo.define('documents.mobile_tests', function (require) {
"use strict";

const DocumentsKanbanView = require('documents.DocumentsKanbanView');
const DocumentsListView = require('documents.DocumentsListView');
const { createDocumentsView } = require('documents.test_utils');

const { afterEach, beforeEach } = require('@mail/utils/test_utils');

const { dom, nextTick } = require('web.test_utils');

QUnit.module('documents', {}, function () {
QUnit.module('documents_kanban_mobile_tests.js', {
    beforeEach() {
        beforeEach(this);

        Object.assign(this.data, {
            'documents.document': {
                fields: {
                    available_rule_ids: {string: "Rules", type: 'many2many', relation: 'documents.workflow.rule'},
                    folder_id: {string: "Folders", type: 'many2one', relation: 'documents.folder'},
                    name: {string: "Name", type: 'char', default: ' '},
                    previous_attachment_ids: {string: "History", type: 'many2many', relation: 'ir.attachment'},
                    res_model: {string: "Model (technical)", type: 'char'},
                    tag_ids: {string: "Tags", type: 'many2many', relation: 'documents.tag'},
                    owner_id: { string: "Owner", type: "many2one", relation: 'res.users' },
                    partner_id: { string: "Related partner", type: 'many2one', relation: 'res.partner' },
                },
                records: [
                    {id: 1, available_rule_ids: [], folder_id: 1},
                    {id: 2, available_rule_ids: [], folder_id: 1},
                ],
            },
            'documents.folder': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    parent_folder_id: {string: 'Parent Workspace', type: 'many2one', relation: 'documents.folder'},
                    description: {string: 'Description', type:'text'},
                },
                records: [
                    {id: 1, name: 'Workspace1', description: '_F1-test-description_', parent_folder_id: false},
                ],
            },
            'documents.tag': {
                fields: {},
                records: [],
                get_tags: () => [],
            },
            'mail.alias': {
                fields: {
                    alias_name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 1, alias_name: 'hazard@rmcf.es'},
                ]
            },
            'documents.share': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    folder_id: {string: "Workspace", type: 'many2one', relation: 'documents.folder'},
                    alias_id: {string: "alias", type: 'many2one', relation: 'mail.alias'},
                },
                records: [
                    {id: 1, name: 'Share1', folder_id: 1, alias_id: 1},
                ],
            },
        });
    },
    afterEach() {
        afterEach(this);
    },
}, function () {
    QUnit.module('DocumentsKanbanViewMobile', function () {

    QUnit.test('basic rendering on mobile', async function (assert) {
        assert.expect(12);

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        assert.containsOnce(kanban, '.o_documents_kanban_view',
            "should have a documents kanban view");
        assert.containsOnce(kanban, '.o_documents_inspector',
            "should have a documents inspector");

        const $controlPanelButtons = $('.o_control_panel .o_cp_buttons');
        assert.containsOnce($controlPanelButtons, '> .dropdown',
            "should group ControlPanel's buttons into a dropdown");
        assert.containsNone($controlPanelButtons, '> .btn',
            "there should be no button left in the ControlPanel's left part");

        // open search panel
        await dom.click(dom.find(document.body, '.o_search_panel_current_selection'));
        // select global view
        await dom.click(dom.find(document.body, '.o_search_panel_category_value:first-child header'));
        // close search panel
        await dom.click(dom.find(document.body, '.o_mobile_search_footer'));
        assert.ok(kanban.$buttons.find('.o_documents_kanban_upload').is(':disabled'),
            "the upload button should be disabled on global view");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_url').is(':disabled'),
            "the upload url button should be disabled on global view");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_request').is(':disabled'),
            "the request button should be disabled on global view");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_share_domain').is(':disabled'),
            "the share button should be disabled on global view");

        // open search panel
        await dom.click(dom.find(document.body, '.o_search_panel_current_selection'));
        // select first folder
        await dom.click(dom.find(document.body, '.o_search_panel_category_value:nth-child(2) header'));
        // close search panel
        await dom.click(dom.find(document.body, '.o_mobile_search_footer'));
        assert.ok(kanban.$buttons.find('.o_documents_kanban_upload').not(':disabled'),
            "the upload button should be enabled when a folder is selected");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_url').not(':disabled'),
            "the upload url button should be enabled when a folder is selected");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_request').not(':disabled'),
            "the request button should be enabled when a folder is selected");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_share_domain').not(':disabled'),
            "the share button should be enabled when a folder is selected");

        kanban.destroy();
    });

    QUnit.module('DocumentsInspector');

    QUnit.test('toggle inspector based on selection', async function (assert) {
        assert.expect(13);

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        assert.isNotVisible(kanban.$('.o_documents_mobile_inspector'),
            "inspector should be hidden when selection is empty");
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2,
            "should have 2 records in the renderer");

        // select a first record
        await dom.click(kanban.$('.o_kanban_record:first .o_record_selector'));
        await nextTick();
        assert.containsOnce(kanban, '.o_kanban_record.o_record_selected:not(.o_kanban_ghost)',
            "should have 1 record selected");
        const toggleInspectorSelector = '.o_documents_mobile_inspector > .o_documents_toggle_inspector';
        assert.isVisible(kanban.$(toggleInspectorSelector),
            "toggle inspector's button should be displayed when selection is not empty");
        assert.strictEqual(kanban.$(toggleInspectorSelector).text().replace(/\s+/g, " ").trim(), '1 document selected');

        await dom.click(kanban.$(toggleInspectorSelector));
        assert.isVisible(kanban.$('.o_documents_mobile_inspector'),
            "inspector should be opened");

        await dom.click(kanban.$('.o_documents_close_inspector'));
        assert.isNotVisible(kanban.$('.o_documents_mobile_inspector'),
            "inspector should be closed");

        // select a second record
        await dom.click(kanban.$('.o_kanban_record:eq(1) .o_record_selector'));
        await nextTick();
        assert.containsN(kanban, '.o_kanban_record.o_record_selected:not(.o_kanban_ghost)', 2,
            "should have 2 records selected");
        assert.strictEqual(kanban.$(toggleInspectorSelector).text().replace(/\s+/g, " ").trim(), '2 documents selected');

        // click on the record
        await dom.click(kanban.$('.o_kanban_record:first'));
        await nextTick();
        assert.containsOnce(kanban, '.o_kanban_record.o_record_selected:not(.o_kanban_ghost)',
            "should have 1 record selected");
        assert.strictEqual(kanban.$(toggleInspectorSelector).text().replace(/\s+/g, " ").trim(), '1 document selected');
        assert.isVisible(kanban.$('.o_documents_mobile_inspector'),
            "inspector should be opened");

        // close inspector
        await dom.click(kanban.$('.o_documents_close_inspector'));
        assert.containsOnce(kanban, '.o_kanban_record.o_record_selected:not(.o_kanban_ghost)',
            "should still have 1 record selected after closing inspector");

        kanban.destroy();
    });
    });

    QUnit.module('DocumentsListViewMobile', function () {

    QUnit.test('basic rendering on mobile', async function (assert) {
        assert.expect(12);

        const list = await createDocumentsView({
            View: DocumentsListView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <tree>
                    <field name="name"/>
                </tree>
            `,
        });

        assert.containsOnce(list, '.o_documents_list_view',
            "should have a documents list view");
        assert.containsOnce(list, '.o_documents_inspector',
            "should have a documents inspector");

        const $controlPanelButtons = $('.o_control_panel .o_cp_buttons');
        assert.containsOnce($controlPanelButtons, '> .dropdown',
            "should group ControlPanel's buttons into a dropdown");
        assert.containsNone($controlPanelButtons, '> .btn',
            "there should be no button left in the ControlPanel's left part");

        // open search panel
        await dom.click(dom.find(document.body, '.o_search_panel_current_selection'));
        // select global view
        await dom.click(dom.find(document.body, '.o_search_panel_category_value:first-child header'));
        // close search panel
        await dom.click(dom.find(document.body, '.o_mobile_search_footer'));
        assert.ok(list.$buttons.find('.o_documents_kanban_upload').is(':disabled'),
            "the upload button should be disabled on global view");
        assert.ok(list.$buttons.find('.o_documents_kanban_url').is(':disabled'),
            "the upload url button should be disabled on global view");
        assert.ok(list.$buttons.find('.o_documents_kanban_request').is(':disabled'),
            "the request button should be disabled on global view");
        assert.ok(list.$buttons.find('.o_documents_kanban_share_domain').is(':disabled'),
            "the share button should be disabled on global view");

        // open search panel
        await dom.click(dom.find(document.body, '.o_search_panel_current_selection'));
        // select global view
        await dom.click(dom.find(document.body, '.o_search_panel_category_value:nth-child(2) header'));
        // close search panel
        await dom.click(dom.find(document.body, '.o_mobile_search_footer'));
        assert.ok(list.$buttons.find('.o_documents_kanban_upload').not(':disabled'),
            "the upload button should be enabled when a folder is selected");
        assert.ok(list.$buttons.find('.o_documents_kanban_url').not(':disabled'),
            "the upload url button should be enabled when a folder is selected");
        assert.ok(list.$buttons.find('.o_documents_kanban_request').not(':disabled'),
            "the request button should be enabled when a folder is selected");
        assert.ok(list.$buttons.find('.o_documents_kanban_share_domain').not(':disabled'),
            "the share button should be enabled when a folder is selected");

        list.destroy();
    });

    QUnit.module('DocumentsInspector');

    QUnit.test('toggle inspector based on selection', async function (assert) {
        assert.expect(13);

        const list = await createDocumentsView({
            View: DocumentsListView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <tree>
                    <field name="name"/>
                </tree>
            `,
        });

        assert.isNotVisible(list.$('.o_documents_mobile_inspector'),
            "inspector should be hidden when selection is empty");
        assert.containsN(list, '.o_document_list_record', 2,
            "should have 2 records in the renderer");

        // select a first record
        await dom.click(list.$('.o_document_list_record:first .o_list_record_selector input'));
        await nextTick();
        assert.containsOnce(list, '.o_document_list_record .o_list_record_selector input:checked',
        "should have 1 record selected");
        const toggleInspectorSelector = '.o_documents_mobile_inspector > .o_documents_toggle_inspector';
        assert.isVisible(list.$(toggleInspectorSelector),
        "toggle inspector's button should be displayed when selection is not empty");
        assert.strictEqual(list.$(toggleInspectorSelector).text().replace(/\s+/g, " ").trim(), '1 document selected');

        await dom.click(list.$(toggleInspectorSelector));
        assert.isVisible(list.$('.o_documents_mobile_inspector'),
            "inspector should be opened");

        await dom.click(list.$('.o_documents_close_inspector'));
        assert.isNotVisible(list.$('.o_documents_mobile_inspector'),
            "inspector should be closed");

        // select a second record
        await dom.click(list.$('.o_document_list_record:eq(1) .o_list_record_selector input'));
        await nextTick();
        assert.containsN(list, '.o_document_list_record .o_list_record_selector input:checked', 2,
            "should have 2 records selected");
        assert.strictEqual(list.$(toggleInspectorSelector).text().replace(/\s+/g, " ").trim(), '2 documents selected');

        // click on the record
        await dom.click(list.$('.o_document_list_record:first'));
        await nextTick();
        assert.containsOnce(list, '.o_document_list_record .o_list_record_selector input:checked',
            "should have 1 record selected");
        assert.strictEqual(list.$(toggleInspectorSelector).text().replace(/\s+/g, " ").trim(), '1 document selected');
        assert.isVisible(list.$('.o_documents_mobile_inspector'),
            "inspector should be opened");

        // close inspector
        await dom.click(list.$('.o_documents_close_inspector'));
        assert.containsOnce(list, '.o_document_list_record .o_list_record_selector input:checked',
            "should still have 1 record selected after closing inspector");

        list.destroy();
    });
    });

});
});

});
