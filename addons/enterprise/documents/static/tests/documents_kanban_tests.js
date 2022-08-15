odoo.define('documents.documents_kanban_tests', function (require) {
"use strict";

const AbstractStorageService = require('web.AbstractStorageService');
const DocumentsKanbanController = require('documents.DocumentsKanbanController');
const DocumentsKanbanView = require('documents.DocumentsKanbanView');
const DocumentsListView = require('documents.DocumentsListView');
const { createDocumentsView } = require('documents.test_utils');

const {
    afterEach,
    afterNextRender,
    beforeEach,
} = require('@mail/utils/test_utils');

const {
    toggleFilterMenu,
    toggleMenuItem,
} = require("@web/../tests/search/helpers");

const Bus = require('web.Bus');
const concurrency = require('web.concurrency');
const KanbanView = require('web.KanbanView');
const RamStorage = require('web.RamStorage');
const relationalFields = require('web.relational_fields');
const testUtils = require('web.test_utils');
const { str_to_datetime } = require('web.time');

const createView = testUtils.createView;

function autocompleteLength() {
    var $el = $('.ui-autocomplete');
    if ($el.length === 0) {
        throw new Error('Autocomplete not found');
    }
    return $el.find('li').length;
}

function searchValue(el, value) {
    var matches = typeof el === 'string' ? $(el) : el;
    if (matches.length !== 1) {
        throw new Error(`Found ${matches.length} elements instead of 1`);
    }
    matches.val(value).trigger('keydown');
}

QUnit.module('documents', {}, function () {
QUnit.module('documents_kanban_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.ORIGINAL_CREATE_XHR = DocumentsKanbanController.prototype._createXHR;
        this.patchDocumentXHR = (mockedXHRs, customSend) => {
            DocumentsKanbanController.prototype._createXhr = () => {
                const xhr = {
                    upload: new window.EventTarget(),
                    open() {},
                    send(data) { customSend && customSend(data); },
                };
                mockedXHRs.push(xhr);
                return xhr;
            };
        };
        Object.assign(this.data, {
            'documents.document': {
                fields: {
                    active: {string: "Active", type: 'boolean', default: true},
                    available_rule_ids: {string: "Rules", type: 'many2many', relation: 'documents.workflow.rule'},
                    file_size: {string: "Size", type: 'integer'},
                    folder_id: {string: "Workspaces", type: 'many2one', relation: 'documents.folder'},
                    lock_uid: { string: "Locked by", type: "many2one", relation: 'res.users' },
                    message_follower_ids: {string: "Followers", type: 'one2many', relation: 'mail.followers'},
                    message_ids: {string: "Messages", type: 'one2many', relation: 'mail.message'},
                    mimetype: {string: "Mimetype", type: 'char', default: ''},
                    name: {string: "Name", type: 'char', default: ' '},
                    owner_id: { string: "Owner", type: "many2one", relation: 'res.users' },
                    partner_id: { string: "Related partner", type: 'many2one', relation: 'res.partner' },
                    previous_attachment_ids: {string: "History", type: 'many2many', relation: 'ir.attachment'},
                    public: {string: "Is public", type: 'boolean'},
                    res_id: {string: "Resource id", type: 'integer'},
                    res_model: {string: "Model (technical)", type: 'char'},
                    res_model_name: {string: "Resource model", type: 'char'},
                    res_name: {string: "Resource name", type: 'char'},
                    share_ids: {string: "Shares", type: "many2many", relation: 'documents.share'},
                    tag_ids: {string: "Tags", type: 'many2many', relation: 'documents.tag'},
                    type: {string: "Type", type: 'selection', selection: [['url', "URL"], ['binary', "File"]], default: 1},
                    url: {string: "Url", type: 'char'},
                    activity_ids: {string: 'Activities', type: 'one2many', relation: 'mail.activity',
                        relation_field: 'res_id'},
                    activity_state: {string: 'State', type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']]},
                    is_editable_attachment: {string: "Is Editable Attachment", type: 'boolean'},
                },
                records: [
                    {id: 1, name: 'yop', file_size: 30000, owner_id: 11, partner_id: 12,
                        public: true, res_id: 1, res_model: 'task', res_model_name: 'Task', activity_ids: [1],
                        activity_state: 'today', res_name: 'Write specs', tag_ids: [1, 2], share_ids: [], folder_id: 1,
                        available_rule_ids: [1, 2, 4], is_editable_attachment: true},
                    {id: 2, name: 'blip', file_size: 20000, owner_id: 12, partner_id: 12,
                        public: false, res_id: 2, mimetype: 'application/pdf', res_model: 'task', res_model_name: 'Task',
                        res_name: 'Write tests', tag_ids: [2], share_ids: [], folder_id: 1, available_rule_ids: [1],
                        is_editable_attachment: false},
                    {id: 3, name: 'gnap', file_size: 15000, lock_uid: 13, owner_id: 12, partner_id: 11,
                        public: false, res_id: 2, res_model: 'documents.document', res_model_name: 'Task',
                        res_name: 'Write doc', tag_ids: [1, 2, 5], share_ids: [], folder_id: 1, available_rule_ids: [1, 2, 3, 4],
                        is_editable_attachment: false},
                    {id: 4, name: 'burp', file_size: 10000, mimetype: 'image/png', owner_id: 11, partner_id: 13,
                        public: true, res_id: 1, res_model: 'order', res_model_name: 'Sale Order',
                        res_name: 'SO 0001', tag_ids: [], share_ids: [], folder_id: 1, available_rule_ids: [],
                        is_editable_attachment: false},
                    {id: 5, name: 'zip', file_size: 40000, lock_uid: 11, owner_id: 12, partner_id: 12,
                        public: false, res_id: 3, res_model: false, res_model_name: false,
                        res_name: false, tag_ids: [1, 2, 5], share_ids: [], folder_id: 1, available_rule_ids: [1, 2, 4],
                        is_editable_attachment: false},
                    {id: 6, name: 'pom', file_size: 70000, partner_id: 13,
                        public: true, res_id: 1, res_model: 'documents.document', res_model_name: 'Document',
                        res_name: 'SO 0003', tag_ids: [], share_ids: [], folder_id: 2, available_rule_ids: [],
                        is_editable_attachment: false},
                    {id: 8, active: false, name: 'wip', file_size: 70000, owner_id: 13, partner_id: 13,
                        public: true, res_id: 1, res_model: 'order', res_model_name: 'Sale Order',
                        res_name: 'SO 0003', tag_ids: [], share_ids: [], folder_id: 1, available_rule_ids: [],
                        is_editable_attachment: false},
                    {id: 9, active: false, name: 'zorro', file_size: 20000, mimetype: 'image/png',
                        owner_id: 13, partner_id: 13, public: true, res_id: false, res_model: false,
                        res_model_name: false, res_name: false, tag_ids: [], share_ids: [], folder_id: 1,
                        available_rule_ids: [], is_editable_attachment: false},
                ],
            },
            'task': {
                fields: {},
                get_formview_id: function () {
                    return Promise.resolve();
                },
            },
            'documents.folder': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    parent_folder_id: {string: 'Parent Workspace', type: 'many2one', relation: 'documents.folder'},
                    description: {string: 'Description', type:'text'},
                },
                records: [
                        {id: 1, name: 'Workspace1', description: '_F1-test-description_', parent_folder_id: false},
                        {id: 2, name: 'Workspace2', parent_folder_id: false},
                        {id: 3, name: 'Workspace3', parent_folder_id: 1},
                ],
            },
            'documents.tag': {
                fields: {},
                records: [{id: 1}, {id: 2}, {id: 3}, {id: 4}, {id: 5}],
                get_tags: function () {
                    return [{
                      group_id: 2,
                      group_name: 'Priority',
                      group_sequence: 10,
                      group_tooltip: 'A priority tooltip',
                      group_hex_color: '#F06050',
                      id: 5,
                      display_name: 'No stress',
                      sequence: 10,
                      __count: 0,
                    }, {
                      group_id: 1,
                      group_name: 'Status',
                      group_sequence: 11,
                      group_tooltip: 'A Status tooltip',
                      group_hex_color: '#6CC1ED',
                      id: 2,
                      display_name: 'Draft',
                      sequence: 10,
                      __count: 0,
                    }, {
                      group_id: 1,
                      group_name: 'Status',
                      group_sequence: 11,
                      group_tooltip: 'A Status tooltip',
                      group_hex_color: '#F7CD1F',
                      id: 1,
                      display_name: 'New',
                      sequence: 11,
                      __count: 0,
                    }];
                },
            },
            'mail.alias': {
                fields: {
                    alias_name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 1, alias_name: 'hazard@rmcf.es'},
                    {id: 2, alias_name: 'lukaku@im.it'},
                    {id: 3, alias_name: 'debruyne@mc.uk'},
                ]
            },
            'documents.share': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    folder_id: {string: "Workspaces", type: 'many2one', relation: 'documents.folder'},
                    alias_id: {string: "alias", type: 'many2one', relation: 'mail.alias'},
                },
                records: [
                    {id: 1, name: 'Share1', folder_id: 1, alias_id: 1},
                    {id: 2, name: 'Share2', folder_id: 1, alias_id: 2},
                    {id: 3, name: 'Share3', folder_id: 2, alias_id: 3},
                ],
                open_share_popup: function () {
                    return Promise.resolve();
                },
            },
            'documents.workflow.rule': {
                fields: {
                    display_name: {string: 'Name', type: 'char'},
                    note: {string: 'Tooltip', type: 'char'},
                    limited_to_single_record: {string: 'Single Record', type: 'boolean'},
                },
                records: [
                    {id: 1, display_name: 'Convincing AI not to turn evil', note: 'Racing for AI Supremacy', limited_to_single_record: false},
                    {id: 2, display_name: 'Follow the white rabbit', limited_to_single_record: false},
                    {id: 3, display_name: 'Entangling superstrings', limited_to_single_record: false},
                    {id: 4, display_name: 'One record rule', limited_to_single_record: true},
                ],
            },
        });

        this.data['res.partner'].records.push(
            { id: 11, display_name: 'Hazard' },
            { id: 12, display_name: 'Lukaku' },
            { id: 13, display_name: 'De Bruyne' }
        );
        this.data['res.users'].records.push(
            { id: 11, display_name: 'Hazard', partner_id: 11 },
            { id: 12, display_name: 'Lukaku', partner_id: 12 },
            { id: 13, display_name: 'De Bruyne', partner_id: 13 }
        );
        this.data['mail.activity.type'].records.push(
            { id: 11, name: "Type 1" },
            { id: 12, name: "Type 2" }
        );
    },
    afterEach() {
        DocumentsKanbanController.prototype._createXHR = this.ORIGINAL_CREATE_XHR;
        afterEach(this);
    },
}, function () {
    QUnit.test('kanban basic rendering', async function (assert) {
        assert.expect(25);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        assert.strictEqual(kanban.$('header.active > label > span').text().trim(), 'Workspace1',
            "the first selected record should be the first folder");
        assert.strictEqual(kanban.$('header.active > span').text().trim(), '5',
            "the first folder should have 5 as counter");
        assert.containsOnce(kanban, '.o_search_panel_category_value:contains(All) header',
            "Should only have a single all selector");

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(0)'));

        assert.ok(kanban.$buttons.find('.o_documents_kanban_upload').is(':disabled'),
            "the upload button should be disabled on global view");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_url').is(':disabled'),
            "the upload url button should be disabled on global view");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_request').is(':disabled'),
            "the request button should be disabled on global view");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_share_domain').is(':disabled'),
            "the share button should be disabled on global view");

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 6,
            "should have 6 records in the renderer");
        assert.containsNone(kanban, '.o_documents_selector_tags',
            "should not display the tag navigation because no workspace is selected by default");

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));

        // check view layout
        assert.containsN(kanban, '.o_content > div', 3,
            "should have 3 columns");
        assert.containsOnce(kanban.$('.o_content'), '> div.o_search_panel',
            "should have a 'documents selector' column");
        assert.containsOnce(kanban, '.o_content > .o_kanban_view',
            "should have a 'classical kanban view' column");
        assert.hasClass(kanban.$('.o_kanban_view'), 'o_documents_kanban_view',
            "should have classname 'o_documents_kanban_view'");
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 5,
            "should have 5 records in the renderer");
        assert.containsOnce(kanban, '.o_kanban_record:first .o_record_selector',
            "should have a 'selected' button");
        assert.containsOnce(kanban, '.o_content > .o_documents_inspector',
            "should have a 'document inspector' column");

        // check control panel buttons
        assert.containsOnce(kanban, '.o_cp_buttons .btn-primary');
        assert.strictEqual(kanban.$('.o_cp_buttons .btn-primary').text().trim(), 'Upload',
            "should have a primary 'Upload' button");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_upload').not(':disabled'),
            "the upload button should be enabled when a folder is selected");
        assert.containsOnce(kanban, '.o_cp_buttons button.o_documents_kanban_url',
            "should allow to save a URL");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_url').not(':disabled'),
            "the upload url button should be enabled when a folder is selected");
        assert.strictEqual(kanban.$('.o_cp_buttons button.o_documents_kanban_request').text().trim(), 'Request',
            "should have a primary 'request' button");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_request').not(':disabled'),
            "the request button should be enabled when a folder is selected");
        assert.strictEqual(kanban.$('.o_cp_buttons button.btn-secondary.o_documents_kanban_share_domain').text().trim(), 'Share',
            "should have a secondary 'Share' button");
        assert.ok(kanban.$buttons.find('.o_documents_kanban_share_domain').not(':disabled'),
            "the share button should be enabled when a folder is selected");

        kanban.destroy();
    });

    QUnit.test('can select records by clicking on the select icon', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        var $firstRecord = kanban.$('.o_kanban_record:first');
        assert.doesNotHaveClass($firstRecord, 'o_record_selected',
            "first record should not be selected");
        await testUtils.dom.click($firstRecord.find('.o_record_selector'));
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should be selected");

        var $thirdRecord = kanban.$('.o_kanban_record:nth(2)');
        assert.doesNotHaveClass($thirdRecord, 'o_record_selected',
            "third record should not be selected");
        await testUtils.dom.click($thirdRecord.find('.o_record_selector'));
        assert.hasClass($thirdRecord, 'o_record_selected',
            "third record should be selected");

        await testUtils.dom.click($firstRecord.find('.o_record_selector'));
        assert.doesNotHaveClass($firstRecord, 'o_record_selected',
            "first record should not be selected");
        assert.hasClass($thirdRecord, 'o_record_selected',
            "third record should be selected");

        kanban.destroy();
    });

    QUnit.test('can select records by clicking on them', async function (assert) {
        assert.expect(5);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.containsNone(kanban, '.o_kanban_record.o_record_selected',
            "no record should be selected");

        var $firstRecord = kanban.$('.o_kanban_record:first');
        await testUtils.dom.click($firstRecord);
        assert.containsOnce(kanban, '.o_kanban_record.o_record_selected',
            "one record should be selected");
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should be selected");

        var $thirdRecord = kanban.$('.o_kanban_record:nth(2)');
        await testUtils.dom.click($thirdRecord);
        assert.containsOnce(kanban, '.o_kanban_record.o_record_selected',
            "one record should be selected");
        assert.hasClass($thirdRecord, 'o_record_selected',
            "third record should be selected");

        kanban.destroy();
    });

    QUnit.test('can unselect a record', async function (assert) {
        assert.expect(3);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.containsNone(kanban, '.o_kanban_record.o_record_selected');

        var $firstRecord = kanban.$('.o_kanban_record:first');
        await testUtils.dom.click($firstRecord);
        assert.hasClass($firstRecord, 'o_record_selected');

        await testUtils.dom.click($firstRecord);
        assert.containsNone(kanban, '.o_kanban_record.o_record_selected');

        kanban.destroy();
    });

    QUnit.test('can select records with keyboard navigation', async function (assert) {
        assert.expect(4);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                        '<button name="some_method" type="object"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            intercepts: {
                execute_action: function () {
                    assert.ok(false, "should not trigger an 'execute_action' event");
                },
            },
        });

        var $firstRecord = kanban.$('.o_kanban_record:first');
        assert.doesNotHaveClass($firstRecord, 'o_record_selected',
            "first record should not be selected");
        $firstRecord.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should be selected");

        var $thirdRecord = kanban.$('.o_kanban_record:nth(2)');
        $thirdRecord.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();
        assert.hasClass($thirdRecord, 'o_record_selected',
            "third record should be selected");
        assert.doesNotHaveClass($firstRecord, 'o_record_selected',
            "first record should no longer be selected");

        kanban.destroy();
    });

    QUnit.test('can multi select records with shift and ctrl', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                        '<button name="some_method" type="object"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        var $firstRecord = kanban.$('.o_kanban_record:first');
        assert.doesNotHaveClass($firstRecord, 'o_record_selected',
            "first record should not be selected");
        $firstRecord.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should be selected");

        var $thirdRecord = kanban.$('.o_kanban_record:nth(2)');
        $thirdRecord.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
            shiftKey: true,
        }));
        await testUtils.nextTick();
        assert.hasClass($thirdRecord, 'o_record_selected',
            "third record should be selected (shift)");
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should still be selected (shift)");

        $firstRecord.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
            ctrlKey: true,
        }));
        await testUtils.nextTick();

        assert.hasClass($thirdRecord, 'o_record_selected',
            "third record should still be selected (ctrl)");
        assert.doesNotHaveClass($firstRecord, 'o_record_selected',
            "first record should no longer be selected (ctrl)");

        kanban.destroy();
    });

    QUnit.test('only visible selected records are kept after a reload', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                        '<button name="some_method" type="object"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            archs: {
                "documents.document,false,search": `
                    <search>
                        <filter name="owo" string="OwO" domain="[['name', '=', 'burp']]"/>
                    </search>`
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(burp) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 3,
            "should have 3 selected records");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 3,
            "should show 3 document previews in the DocumentsInspector");

        await toggleFilterMenu(kanban.el);
        await toggleMenuItem(kanban.el, "OwO");

        assert.containsOnce(kanban, '.o_record_selected',
            "should have 1 selected record");
        assert.containsOnce(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show 1 document preview in the DocumentsInspector");

        await toggleMenuItem(kanban.el, "OwO");

        assert.containsOnce(kanban, '.o_record_selected',
            "should have 1 selected records");
        assert.containsOnce(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show 1 document previews in the DocumentsInspector");

        kanban.destroy();
    });

    QUnit.test('selected records are kept when a button is clicked', async function (assert) {
        assert.expect(7);

        var self = this;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                        '<button name="some_method" type="object"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'read' && args.model === 'documents.document') {
                    assert.deepEqual(args.args[0], [1],
                        "should read the clicked record");
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (ev) {
                    assert.strictEqual(ev.data.action_data.name, 'some_method',
                        "should call the correct method");
                    self.data['documents.document'].records[0].name = 'yop changed';
                    ev.data.on_closed();
                },
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(burp) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 3,
            "should have 3 selected records");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 3,
            "should show 3 document previews in the DocumentsInspector");

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) button'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_record_selected:contains(yop changed)').length, 1,
            "should have re-rendered the updated record");
        assert.containsN(kanban, '.o_record_selected', 3,
            "should still have 3 selected records");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 3,
            "should still show 3 document previews in the DocumentsInspector");

        kanban.destroy();
    });

    QUnit.test('can share current domain', async function (assert) {
        assert.expect(2);

        const domain = ['owner_id', '=', 12];
        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            domain: [domain],
            mockRPC: function (route, args) {
                if (args.method === 'open_share_popup') {
                    assert.deepEqual(args.args, [{
                        document_ids: false,
                        domain: [
                            "&",
                                domain,
                            "&",
                                ["folder_id", "child_of", 1],
                                ["res_model", "in", ["task"]]
                        ],
                        folder_id: 1,
                        tag_ids: [[6, 0, []]],
                        type: 'domain',
                    }]);
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_category_value header', 1)
        );
        // filter on 'task' in the DocumentsSelector
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Task")
        );

        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1,
            "should have 2 records in the renderer");

        await testUtils.dom.click(kanban.$buttons.find('.o_documents_kanban_share_domain'));

        kanban.destroy();
    });

    QUnit.test('can upload from URL', async function (assert) {
        assert.expect(1);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action, "documents.action_url_form", "should open the URL form");
                },
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$buttons.find('button.o_documents_kanban_url'));

        kanban.destroy();
    });

    QUnit.test('can Request a file', async function (assert) {
        assert.expect(1);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action, "documents.action_request_form", "should open the Request form");
                },
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$buttons.find('button.o_documents_kanban_request'));

        kanban.destroy();
    });

    QUnit.module('DocumentsInspector');

    QUnit.test('document inspector with no document selected', async function (assert) {
        assert.expect(3);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        assert.strictEqual(kanban.$('.o_documents_inspector_preview').text().replace(/\s+/g, ''),
            '_F1-test-description_', "should display the current workspace description");
        assert.strictEqual(kanban.$('.o_documents_inspector_info .o_inspector_value:first').text().trim(),
            '5', "should display the correct number of documents");
        assert.strictEqual(kanban.$('.o_documents_inspector_info .o_inspector_value:nth(1)').text().trim(),
            '0.12 MB', "should display the correct size");

        kanban.destroy();
    });

    QUnit.test('document inspector with selected documents', async function (assert) {
        assert.expect(5);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        // select a first document
        await testUtils.dom.click(kanban.$('.o_kanban_record:first .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_documents_inspector_info .o_selection_size',
            "should not display the number of selected documents (because only 1)");
        assert.containsOnce(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show a preview of the selected document");
        assert.hasClass(kanban.$('.o_documents_inspector_preview .o_document_preview'), 'o_documents_single_preview',
            "should have the 'o_documents_single_preview' className");

        // select a second document
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(2) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_documents_inspector_preview .o_selection_size').text().trim(),
            '2 documents selected', "should display the correct number of selected documents");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 2,
            "should show a preview of the selected documents");

        kanban.destroy();
    });

    QUnit.test('document inspector limits preview to 4 documents', async function (assert) {
        assert.expect(2);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        // select five documents
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(0) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(1) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(2) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(3) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(4) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_documents_inspector_preview .o_selection_size').text().trim(),
            '5 documents selected', "should display the correct number of selected documents");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 4,
            "should only show a preview of 4 selected documents");

        kanban.destroy();
    });

    QUnit.test('document inspector shows selected records of the current page', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban limit="2"><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsOnce(kanban, '.o_record_selected',
            "should have 1 selected record");
        assert.containsOnce(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show 1 document preview in the DocumentsInspector");

        await testUtils.controlPanel.pagerNext(kanban);
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show no document preview in the DocumentsInspector");

        await testUtils.controlPanel.pagerPrevious(kanban);
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show no document preview in the DocumentsInspector");

        kanban.destroy();
    });

    QUnit.test('document inspector: document preview', async function (assert) {
        assert.expect(9);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            mockRPC: function (route) {
                if (route === '/web/static/lib/pdfjs/web/viewer.html?file=/web/content/2?model%3Ddocuments.document%26filename%3Dblip') {
                    assert.step('pdf route');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_document_preview img',
            "should not have a clickable image");

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(burp)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_viewer_content',
            "should not have a document preview");
        assert.containsOnce(kanban, '.o_document_preview img',
            "should have a clickable image");

        await testUtils.dom.click(kanban.$('.o_document_preview img'));

        assert.containsOnce(kanban, '.o_viewer_content',
            "should have a document preview");
        assert.containsOnce(kanban, '.o_close_btn',
            "should have a close button");

        await testUtils.dom.click(kanban.$('.o_close_btn'));

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_preview_available'));

        assert.containsOnce(kanban, '.o_documents_split_pdf_area', "should have a pdf splitter");

        await testUtils.dom.click(kanban.$('.o_close_btn'));

        assert.containsNone(kanban, '.o_viewer_content',
            "should not have a document preview after pdf exit");

        assert.verifySteps(['pdf route']);

        kanban.destroy();
    });

    QUnit.test('document inspector: open preview while modifying document', async function (assert) {
        assert.expect(2);
        var def = testUtils.makeTestPromise();

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    return def;
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(burp)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        kanban.$('input[name=name]').val("foo").trigger('input');

        await testUtils.dom.click(kanban.$('.o_document_preview img'));
        await testUtils.nextTick();
        assert.containsNone(kanban, '.o_viewer_content',
            "document preview should have been canceled");

        def.resolve();
        await testUtils.nextTick();
        await testUtils.dom.click(kanban.$('.o_document_preview img'));
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_viewer_content',
                "should have a document preview");
        await testUtils.dom.click(kanban.$('.o_close_btn'));
        kanban.destroy();
    });

    QUnit.test('document inspector: can delete records', async function (assert) {
        assert.expect(5);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            domain: [['active', '=', false]],
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'unlink') {
                    assert.deepEqual(args.args[0], [8, 9],
                        "should unlink the selected records");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(wip) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(zorro) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 2,
            "should show 2 document previews in the DocumentsInspector");

        await testUtils.dom.click(kanban.$('.o_documents_inspector_info .o_inspector_delete'));
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show 0 document preview in the DocumentsInspector");

        kanban.destroy();
    });

    QUnit.test('document inspector: can archive records', async function (assert) {
        assert.expect(5);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/documents.document/toggle_active") {
                    var documentIDS = args.args[0];
                    var records = this.data['documents.document'].records;
                    documentIDS.forEach((documentID) => {
                        records.find((record) => record.id === documentID).active = false;
                    });
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(burp) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsN(kanban, '.o_documents_inspector_preview .o_document_preview', 2,
            "should show 2 document previews in the DocumentsInspector");

        await testUtils.dom.click(kanban.$('.o_documents_inspector_info .o_inspector_archive'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(kanban, '.o_documents_inspector_preview .o_document_preview',
            "should show no document preview in the DocumentsInspector");

        await kanban.reload({active: false});

        assert.containsNone(kanban, '.o_kanban_view .o_record_selected',
            "should have no selected archived record");

        kanban.destroy();
    });

    QUnit.test('document inspector: can share records', async function (assert) {
        assert.expect(2);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'open_share_popup') {
                    assert.deepEqual(args.args, [{
                        document_ids: [[6, 0, [1, 2]]],
                        folder_id: 1,
                        type: 'ids',
                    }]);
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 2,
            "should have 2 selected records");

        await testUtils.dom.click(kanban.$('.o_documents_inspector_info .o_inspector_share'));

        kanban.destroy();
    });

    QUnit.test('document inspector: locked records', async function (assert) {
        assert.expect(6);

        this.data.currentUserId = 11;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            session: {
                uid: this.data.currentUserId,
            },
        });

        // select a record that is locked by ourself
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(zip)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.hasClass(kanban.$('.o_inspector_lock'), 'o_locked',
            "this attachment should be locked");
        assert.notOk(kanban.$('.o_inspector_lock').is(':disabled'),
            "lock button should not be disabled");
        assert.notOk(kanban.$('.o_inspector_replace').is(':disabled'),
            "replace button should not be disabled");

        // select a record that is locked by someone else
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(gnap)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.hasClass(kanban.$('.o_inspector_lock'), 'o_locked',
            "this attachment should be locked as well");
        assert.ok(kanban.$('.o_inspector_replace').is(':disabled'),
            "replace button should be disabled");
        assert.ok(kanban.$('.o_inspector_archive').is(':disabled'),
            "archive button should be disabled");

        kanban.destroy();
    });

    QUnit.test('document inspector: can (un)lock records', async function (assert) {
        assert.expect(5);

        var self = this;
        this.data.currentUserId = 11;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            session: {
                uid: this.data.currentUserId,
            },
            mockRPC: function (route, args) {
                if (args.method === 'toggle_lock') {
                    assert.deepEqual(args.args, [1], "should call method for the correct record");
                    var record = self.data['documents.document'].records.find((d) => d.id === 1);
                    record.lock_uid = record.lock_uid ? false : 11;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.doesNotHaveClass(kanban.$('.o_inspector_lock'), 'o_locked',
            "this attachment should not be locked");

        // lock the record
        await testUtils.dom.click(kanban.$('.o_inspector_lock'));
        await testUtils.nextTick();

        assert.hasClass(kanban.$('.o_inspector_lock'), 'o_locked',
            "this attachment should be locked");


        // unlock the record
        await testUtils.dom.click(kanban.$('.o_inspector_lock'));
        await testUtils.nextTick();

        assert.doesNotHaveClass(kanban.$('.o_inspector_lock'), 'o_locked',
            "this attachment should not be locked anymore");

        kanban.destroy();
    });

    QUnit.test('document inspector: document info with one document selected', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_field_widget[name=name]').val(),
            'yop', "should correctly display the name");
        assert.strictEqual(kanban.$('.o_field_widget[name=owner_id] input').val(),
            'Hazard', "should correctly display the owner");
        assert.strictEqual(kanban.$('.o_field_widget[name=partner_id] input').val(),
            'Lukaku', "should correctly display the related partner");
        assert.containsNone(kanban, '.o_field_many2one .o_external_button:visible',
            "should not display the external button in many2ones");
        assert.strictEqual(kanban.$('.o_inspector_model_name').text(),
            ' Task', "should correctly display the resource model");
        assert.strictEqual(kanban.$('.o_inspector_object_name').text(),
            'Write specs', "should correctly display the resource name");

        kanban.destroy();
    });

    QUnit.test('document inspector: update document info with one document selected', async function (assert) {
        assert.expect(7);
        var count = 0;

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                        '<field name="owner_id"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    count++;
                    switch (count) {
                        case 1:
                            assert.deepEqual(args.args, [[1], {owner_id: 13}],
                                "should save the change directly");
                            break;
                        case 2:
                            assert.deepEqual(args.args, [[1], {owner_id: false}],
                                "should save false value");
                            break;
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        var $firstRecord = kanban.$('.o_kanban_record:first');
        assert.strictEqual($firstRecord.text(), 'yopHazard',
            "should display the correct owner");

        await testUtils.dom.click($firstRecord);
        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.hasClass($firstRecord, 'o_record_selected');

        // change m2o value
        await testUtils.fields.many2one.searchAndClickItem('owner_id', {search: 'De Bruyne'});
        await testUtils.nextTick();

        $firstRecord = kanban.$('.o_kanban_record:first');
        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual($firstRecord.text(), 'yopDe Bruyne',
            "should have updated the owner");
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should still be selected");
        assert.strictEqual(kanban.$('.o_field_many2one[name=owner_id] input').val(), 'De Bruyne',
            "should display the new value in the many2one");

        kanban.$('.o_field_many2one[name=owner_id] input').val('').trigger('keyup').trigger('focusout');
        await testUtils.nextTick();
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        kanban.destroy();
    });

    QUnit.test('document inspector: document info with several documents selected', async function (assert) {
        assert.expect(7);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        // select two records with same m2o value
        var $blip = kanban.$('.o_kanban_record:contains(blip)');
        var $gnap = kanban.$('.o_kanban_record:contains(gnap)');
        await testUtils.dom.click($blip);
        await testUtils.dom.click($gnap.find('.o_record_selector'));
        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.hasClass($blip, 'o_record_selected',
            "blip record should be selected");
        assert.hasClass($gnap, 'o_record_selected',
            "gnap record should be selected");

        assert.strictEqual(kanban.$('.o_field_many2one[name=owner_id] input').val(),
            'Lukaku', "should display the correct m2o value");
        assert.containsNone(kanban, '.o_field_many2one .o_external_button:visible',
            "should not display the external button in many2one");

        // select a third record with another m2o value
        var $yop = kanban.$('.o_kanban_record:contains(yop)');
        await testUtils.dom.click($yop.find('.o_record_selector'));
        assert.hasClass($yop, 'o_record_selected',
            "yop record should be selected");

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_field_many2one[name=owner_id] input').val(),
            'Multiple values', "should display 'Multiple values'");
        assert.containsNone(kanban, '.o_field_many2one .o_external_button:visible',
            "should not display the external button in many2one");

        kanban.destroy();
    });

    QUnit.test('document inspector: update document info with several documents selected', async function (assert) {
        assert.expect(10);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                        '<field name="owner_id"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], {owner_id: 13}],
                        "should save the change directly");
                }
                return this._super.apply(this, arguments);
            },
        });

        var $firstRecord = kanban.$('.o_kanban_record:first');
        assert.strictEqual($firstRecord.text(), 'yopHazard',
            "should display the correct owner (record 1)");
        var $secondRecord = kanban.$('.o_kanban_record:nth(1)');
        assert.strictEqual($secondRecord.text(), 'blipLukaku',
            "should display the correct owner (record 2)");

        await testUtils.dom.click($firstRecord);
        await testUtils.dom.click($secondRecord.find('.o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should be selected");
        assert.hasClass($secondRecord, 'o_record_selected',
            "second record should be selected");

        // change m2o value for both records
        await testUtils.fields.many2one.searchAndClickItem('owner_id', {search: 'De Bruyne'});
        await testUtils.nextTick();

        $firstRecord = kanban.$('.o_kanban_record:first');
        assert.strictEqual($firstRecord.text(), 'yopDe Bruyne',
            "should have updated the owner of first record");
        $secondRecord = kanban.$('.o_kanban_record:nth(1)');
        assert.strictEqual($secondRecord.text(), 'blipDe Bruyne',
            "should have updated the owner of second record");
        assert.hasClass($firstRecord, 'o_record_selected',
            "first record should still be selected");
        assert.hasClass($secondRecord, 'o_record_selected',
            "second record should still be selected");
        assert.strictEqual(kanban.$('.o_field_many2one[name=owner_id] input').val(), 'De Bruyne',
            "should display the new value in the many2one");

        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        kanban.destroy();
    });

    QUnit.test('document inspector: update info: handle concurrent updates', async function (assert) {
        assert.expect(11);

        var def = testUtils.makeTestPromise();
        var nbWrite = 0;
        var value;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'write') {
                    assert.step('write');
                    nbWrite++;
                    assert.deepEqual(args.args, [[1], {name: value}],
                        "should correctly save the changes");
                    if (nbWrite === 1) {
                        return def.then(() => result);
                    }
                }
                return result;
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_record:first').text(), 'yop',
            "should display the correct filename");
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        // change filename value of selected record (but block RPC)
        value = 'temp name';
        await testUtils.fields.editInput(kanban.$('.o_field_char[name=name]'), value);

        assert.strictEqual(kanban.$('.o_kanban_record:first').text(), 'yop',
            "should still display the old filename");

        // change filename value again (this RPC isn't blocked but must wait for
        // the first one to return)
        value = 'new name';
        await testUtils.fields.editInput(kanban.$('.o_field_char[name=name]'), value);

        assert.strictEqual(kanban.$('.o_kanban_record:first').text(), 'yop',
            "should still display the old filename");

        assert.step('resolve');
        def.resolve();
        await testUtils.nextTick();
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_kanban_record:first').text(), 'new name',
            "should still display the new filename in the record");
        assert.strictEqual(kanban.$('.o_field_char[name=name]').val(), 'new name',
            "should still display the new filename in the document inspector");

        assert.verifySteps(['write', 'resolve', 'write']);

        kanban.destroy();
    });

    QUnit.test('document inspector: open resource', async function (assert) {
        assert.expect(1);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action, {
                        res_id: 1,
                        res_model: 'task',
                        type: 'ir.actions.act_window',
                        views: [[false, 'form']],
                    }, "should open the resource in a form view");
                },
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_object_name'));

        kanban.destroy();
    });

    QUnit.test('document inspector: display tags of selected documents', async function (assert) {
        assert.expect(4);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:eq(1) header'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_tag', 2,
            "should display the tags of the selected document");

        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(1) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsOnce(kanban, '.o_inspector_tag',
            "should display the common tags between the two selected documents");
        assert.strictEqual(kanban.$('.o_inspector_tag').text().replace(/\s/g, ""), 'Status>Draft×',
            "should correctly display the content of the tag");

        kanban.destroy();
    });

    QUnit.test('document inspector: input to add tags is hidden if no tag to add', async function (assert) {
        assert.expect(2);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(gnap)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_tag', 3,
            "should have 3 tags");
        assert.containsNone(kanban, '.o_inspector_tags .o_inspector_tag_add',
            "should not have an input to add tags");

        kanban.destroy();
    });

    QUnit.test('document inspector: remove tag', async function (assert) {
        assert.expect(4);

        this.data.currentUserId = 11;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[0], [1, 5],
                        "should write on the selected records");
                    assert.deepEqual(args.args[1], {
                        tag_ids: [[3, 2]],
                    }, "should write the correct value");
                }
                return this._super.apply(this, arguments);
            },
            session: {
                uid: this.data.currentUserId,
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(4) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_tag', 2,
            "should display two tags");

        await testUtils.dom.click(kanban.$('.o_inspector_tag:first .o_inspector_tag_remove'));

        assert.containsOnce(kanban, '.o_inspector_tag',
            "should display one tag");

        kanban.destroy();
    });

    QUnit.test('document inspector: add a tag', async function (assert) {
        assert.expect(7);
        var done = assert.async();

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[0], [1, 2],
                        "should write on the selected records");
                    assert.deepEqual(args.args[1], {
                        tag_ids: [[4, 5]],
                    }, "should write the correct value");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(1) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.notOk($('.o_inspector_tag_add').is(':focus'), "the tag input should not be focused");

        assert.containsOnce(kanban, '.o_inspector_tag');

        searchValue('.o_inspector_tag_add', 'stress');
        concurrency.delay(0).then(async function () {
            assert.strictEqual(autocompleteLength(), 1,
                "should have an entry in the autocomplete dropdown");
            var $autocomplete = kanban.$('.o_inspector_tag_add').autocomplete('widget');
            // TO DO understand problem with autocomplete
            await testUtils.dom.click($autocomplete.find('li > a:first'));

            assert.containsN(kanban, '.o_inspector_tag', 2,
                "should display two tags");
            assert.strictEqual($('.o_inspector_tag_add')[0], document.activeElement, "the tag input should be focused");
            kanban.destroy();
            done();
        });
    });

    QUnit.test('document inspector: do not suggest already linked tags', async function (assert) {
        assert.expect(2);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_tag', 2,
            "should display two tags");

        searchValue('.o_inspector_tag_add', 'new');
        assert.strictEqual(autocompleteLength(), 0,
            "should have no entry in the autocomplete drodown");

        kanban.destroy();
    });

    QUnit.test('document inspector: tags: trigger a search on input clicked', async function (assert) {
        assert.expect(1);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_inspector_tag_add'));
        var $autocomplete = kanban.$('.o_inspector_tag_add').autocomplete('widget');
        assert.strictEqual(autocompleteLength(), 1,
            "should have an entry in the autocomplete dropdown");
        await testUtils.dom.click($autocomplete.find('li > a:first'));

        kanban.destroy();
    });

    QUnit.test('document inspector: unknown tags are hidden', async function (assert) {
        assert.expect(1);

        this.data['documents.document'].records[0].tag_ids = [1, 2, 78];

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_tag', 2,
            "should not display the unknown tag");

        kanban.destroy();
    });

    QUnit.test('document inspector: display rules of selected documents', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_rule', 3,
            "should display the rules of the selected document");

        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(1) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsOnce(kanban, '.o_inspector_rule',
            "should display the common rules between the two selected documents");
        assert.containsOnce(kanban, '.o_inspector_rule .o_inspector_trigger_rule',
            "should display the button for the common rule");
        assert.strictEqual(kanban.$('.o_inspector_rule').text().trim(), 'Convincing AI not to turn evil',
            "should correctly display the content of the rule");
        assert.hasAttrValue(kanban.$('.o_inspector_rule span'), 'title', "Racing for AI Supremacy",
            "should correctly display the tooltip of the rule");

        kanban.destroy();
    });

    QUnit.test('document inspector: displays the right amount of single record rules', async function (assert) {
        assert.expect(2);

        this.data.currentUserId = 11;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            session: {
                uid: this.data.currentUserId,
            },
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(0)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_rule', 3,
            "should display the rules of the selected document (2 multi record, 1 single record)");

        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(4) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_rule', 2,
            "should display the rules in common except the single record rule");

        kanban.destroy();
    });

    QUnit.test('document inspector: locked by another user', async function (assert) {
        assert.expect(4);

        this.data['documents.document'].records.push({
            id: 54,
            name: 'lockedByAnother',
            folder_id: 1,
            lock_uid: 13,
            available_rule_ids: [1, 2, 4]
        });
        this.data.currentUserId = 12;
        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            session: {
                uid: this.data.currentUserId,
            },
            arch: `
                <kanban><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(lockedByAnother)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_inspector_rule', "should not display any rule");

        assert.ok(kanban.$('.o_inspector_lock').prop('disabled'), "the lock button should be disabled");
        assert.ok(kanban.$('.o_inspector_replace').prop('disabled'), "the replace button should be disabled");
        assert.ok(kanban.$('.o_inspector_archive').prop('disabled'), "the archive button should be disabled");

        kanban.destroy();
    });

    QUnit.test('document inspector: display rules of reloaded record', async function (assert) {
        assert.expect(7);

        var self = this;
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                        '<button name="some_method" type="object"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            intercepts: {
                execute_action: function (ev) {
                    assert.strictEqual(ev.data.action_data.name, 'some_method',
                        "should call the correct method");
                    self.data['documents.document'].records[0].name = 'yop changed';
                    ev.data.on_closed();
                },
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_inspector_rule span', 3,
            "should display the rules of the selected document");

        assert.strictEqual(kanban.$('.o_inspector_rule span:eq(0)').text(), 'Convincing AI not to turn evil',
            "should display the right rule");

        assert.strictEqual(kanban.$('.o_inspector_rule span:eq(1)').text(), 'Follow the white rabbit',
            "should display the right rule");

        assert.strictEqual(kanban.$('.o_inspector_rule span:eq(2)').text(), 'One record rule',
            "should display the right rule");

        // click on the button to reload the record
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) button'));

        assert.strictEqual(kanban.$('.o_record_selected:contains(yop changed)').length, 1,
            "should have reloaded the updated record");

        // unselect and re-select it (the record has been reloaded, so we want
        // to make sure its rules have been reloaded correctly as well)
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop changed)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop changed)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_inspector_rule span').text(),
            'Convincing AI not to turn evilFollow the white rabbitOne record rule',
            "should correctly display the rules of the selected document");

        kanban.destroy();
    });

    QUnit.test('document inspector: trigger rule actions on selected documents', async function (assert) {
        assert.expect(3);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (args.model === 'documents.workflow.rule' && args.method === 'apply_actions') {
                    assert.deepEqual(args.args[0], [1],
                        "should execute actions on clicked rule");
                    assert.deepEqual(args.args[1], [1, 2],
                        "should execute actions on the selected records");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(1) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsOnce(kanban, '.o_inspector_rule',
            "should display the common rules between the two selected documents");
        await testUtils.dom.click(kanban.$('.o_inspector_rule .o_inspector_trigger_rule'));

        kanban.destroy();
    });

    QUnit.test('document inspector: checks the buttons deleting/editing a link between a document and a record', async function (assert) {
        // Check the display of the edit and delete buttons of a link between a document and its record.
        // Check the operation of the delete link button.
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `<kanban><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                        <field name="is_editable_attachment" invisible="1"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (args.method === 'check_access_rights') {
                    return Promise.resolve(true);
                } else if (args.model === 'documents.workflow.rule' && args.method === 'unlink_record') {
                    this.data['documents.document'].records = this.data['documents.document'].records.map(r => {
                        if (r.id === args.args[0]) {
                            r.res_model = 'documents.document';
                            r.res_id = false;
                            r.is_editable_attachment = false;
                        }
                        return r;
                    });
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        // Document with an editable link.
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));
        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_inspector_model_button.o_inspector_model_edit',
            "should display the edit button of the link between the document and the record on the inspector.");
        assert.containsOnce(kanban, '.o_inspector_model_button.o_inspector_model_delete',
            "should display the delete button of the link between the document and the record on the inspector.");

        // Delete the link
        await testUtils.dom.click(kanban.$('.o_inspector_model_delete'));
        await testUtils.dom.click($('.modal-footer .btn-primary'));
        assert.containsNone(kanban, 'o_inspector_custom_field .o_model_container',
            "should display no records link to the document");

        // Document with a non-editable link
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(1) .o_record_selector'));
        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();
        assert.containsNone(kanban, 'o_inspector_custom_field .o_model_container',
            "should display a record link to the document");
        assert.containsNone(kanban, '.o_inspector_model_button.o_inspector_model_edit',
            "should not display the edit button of the link between the document and the record on the inspector.");
        assert.containsNone(kanban, '.o_inspector_model_button.o_inspector_model_delete',
            "should not display the delete button of the link between the document and the record on the inspector.");

        kanban.destroy();
    });

    QUnit.test('document inspector: quick create not enabled in dropdown', async function (assert) {
        assert.expect(2);

       var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        await testUtils.dom.click(kanban.$('.o_kanban_record:first'));
        await testUtils.nextTick();
        await testUtils.fields.many2one.clickOpenDropdown('partner_id');
        await testUtils.fields.editInput(kanban.$('.o_field_widget[name=partner_id] input'), "Dupont");
        assert.strictEqual($('.ui-autocomplete .o_m2o_dropdown_option').length, 1,
            "Dropdown should be opened and have only one item");
        assert.notEqual(
            $('.ui-autocomplete .o_m2o_dropdown_option')[0].textContent,
            'Create "Dupont"',
            'there should not be a quick create in dropdown'
        );
        kanban.destroy();
    });

    QUnit.module('DocumentChatter');

    QUnit.test('document chatter: open and close chatter', async function (assert) {
        assert.expect(7);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.containsNone(kanban, '.o_Chatter',
            "should not display any chatter");

        // select a record
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_Chatter',
            "should still not display any chatter");

        // open the chatter
        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_Chatter',
            "should display the chatter");
        assert.containsOnce(kanban, '.o_search_panel:visible',
            "documents selector should still be visible");
        assert.containsOnce(kanban, '.o_kanban_view:visible',
            "kanban view should still be visible");
        assert.containsOnce(kanban, '.o_documents_inspector:visible',
            "document inspector should still be visible");

        // close the chatter
        await testUtils.dom.click(kanban.$('.o_ChatterTopbar_buttonClose'));
        assert.containsNone(kanban, '.o_document_chatter_container .o_Chatter',
            "should no longer display the chatter");

        kanban.destroy();
    });

    QUnit.test('document chatter: fetch and display chatter messages', async function (assert) {
        assert.expect(2);

        this.data['documents.document'].records[0].message_ids = [101, 102];
        this.data['mail.message'].records.push(
            { body: "Message 1", id: 101, model: 'documents.document', res_id: 1 },
            { body: "Message 2", id: 102, model: 'documents.document', res_id: 1 }
        );

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await afterNextRender(() =>
            testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'))
        );
        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsN(kanban, '.o_document_chatter_container .o_Chatter .o_Message', 2,
            "should display two messages in the chatter");

        kanban.destroy();
    });

    QUnit.test('document chatter: fetch and display followers', async function (assert) {
        assert.expect(3);

        this.data['documents.document'].records[0].message_follower_ids = [301, 302];

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route) {
                if (route === '/mail/read_followers') {
                    return Promise.resolve({
                        followers: [{
                            email: 'raoul@grosbedon.fr',
                            id: 301,
                            name: 'Raoul Grosbedon',
                            partner_id: 31,
                        }, {
                            email: 'raoulette@grosbedon.fr',
                            id: 302,
                            name: 'Raoulette Grosbedon',
                            partner_id: 32,
                        }],
                        subtypes: [],
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(
            kanban,
            '.o_document_chatter_container .o_Chatter',
            "should display the chatter"
        );
        assert.containsOnce(kanban,
            '.o_document_chatter_container .o_FollowerListMenu',
            "should display the follower widget"
        );
        assert.strictEqual(
            document.querySelector('.o_FollowerListMenu_buttonFollowersCount').textContent,
            "2",
            "should have two followers"
        );

        kanban.destroy();
    });

    QUnit.test('document chatter: render the activity button', async function (assert) {
        assert.expect(3);

        const bus = new Bus();
        bus.on('do-action', null, payload => {
            assert.deepEqual(payload.action, {
                context: {
                    default_res_id: 1,
                    default_res_model: 'documents.document'
                },
                name: "Schedule Activity",
                res_id: false,
                res_model: 'mail.activity',
                target: 'new',
                type: 'ir.actions.act_window',
                view_mode: 'form',
                views: [[false, 'form']]
                },
                "the activity button should trigger do_action with the correct args"
            );
        });

        var kanban = await createDocumentsView({
            env: { bus },
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        var $activityButton = kanban.$('.o_document_chatter_container .o_ChatterTopbar_buttonScheduleActivity');
        assert.strictEqual($activityButton.length, 1,
            "should display the activity button");
        await testUtils.dom.click($activityButton);

        kanban.destroy();
    });

    QUnit.test('document chatter: render the activity button 2', async function (assert) {
        assert.expect(8);

        this.data['mail.activity'].records.push({
            id: 1,
            display_name: "An activity",
            date_deadline: moment().format("YYYY-MM-DD"),
            state: "today",
            user_id: 2,
            create_uid: 2,
            can_write: true,
            activity_type_id: 1,
        });
        this.data.partner = {
            fields: {
                display_name: { string: "Displayed name", type: "char" },
                message_ids: {
                    string: "messages",
                    type: "one2many",
                    relation: 'mail.message',
                    relation_field: "res_id",
                },
                activity_ids: {
                    string: 'Activities',
                    type: 'one2many',
                    relation: 'mail.activity',
                    relation_field: 'res_id',
                },
            },
            records: [{
                id: 2,
                display_name: "first partner",
                message_ids: [],
                activity_ids: [],
            }]
        };

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        assert.containsOnce(kanban, '.o_ActivityBox',
            "should display the activity area");
        assert.containsOnce(kanban, '.o_Activity',
            "should display an activity");
        assert.strictEqual(kanban.$('.o_Activity_markDoneButton').length, 1,
            "should display the activity mark done button");
        assert.containsOnce(kanban, '.o_Activity_editButton',
            "should display the activity Edit button");
        assert.containsOnce(kanban, '.o_Activity_cancelButton',
            "should display the activity Cancel button");

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsNone(kanban, '.o_Activity',
            "should not display an activity");

        kanban.destroy();
    });

    QUnit.test('document chatter: can write messages in the chatter', async function (assert) {
        assert.expect(7);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            async mockRPC(route, args) {
                if (route === '/mail/get_suggested_recipients') {
                    return { 1: [] };
                }
                if (route === '/mail/message/post') {
                    assert.deepEqual(args.thread_id, 1,
                        "should post message on correct record");
                    assert.strictEqual(args.post_data.body, 'Some message',
                        "should post correct message");
                    return this._super(...arguments);
                }
                return this._super.apply(this, arguments);
            },
        });

        // select a record and open the chatter
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsNone(kanban, '.o_document_chatter_container .o_Composer',
            "chatter composer should not be open");

        // open the composer
        await testUtils.dom.click(kanban.$('.o_document_chatter_container .o_ChatterTopbar_buttonSendMessage'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Composer',
            "chatter composer should be open");

        // write and send a message (need to wait the Send button to be enabled)
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        await afterNextRender(() => {
            document.execCommand('insertText', false, "Some message");
        });
        await testUtils.dom.click(kanban.$('.o_Composer_buttonSend'));
        assert.containsOnce(kanban, '.o_Message',
            "a message should have been created"
        );
        assert.strictEqual(
            document.querySelector('.o_Message_content').textContent,
            "Some message",
            "the created message should have the right body"
        );
        kanban.destroy();
    });

    QUnit.test('document chatter: keep chatter open when switching between records', async function (assert) {
        assert.expect(6);

        this.data['documents.document'].records[0].message_ids = [101, 102];
        this.data['mail.message'].records.push(
            { body: "Message on 'yop'", id: 101, model: 'documents.document', res_id: 1 },
            { body: "Message on 'blip'", id: 102, model: 'documents.document', res_id: 2 }
        );

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        // select a record and open the chatter
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await afterNextRender(() =>
            testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'))
        );
        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsOnce(kanban, '.o_document_chatter_container .o_Message',
            "should display one message in the chatter");
        assert.strictEqual(kanban.$('.o_Message .o_Message_content').text().trim(),
            "Message on 'yop'", "should display the correct message");

        // select another record
        await afterNextRender(() =>
            testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip)'))
        );
        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should still display the chatter");
        assert.containsOnce(kanban, '.o_document_chatter_container .o_Message',
            "should display one message in the chatter");
        assert.strictEqual(kanban.$('.o_Message .o_Message_content').text().trim(),
            "Message on 'blip'", "should display the correct message");

        kanban.destroy();
    });

    QUnit.test('document chatter: keep chatter open after a reload', async function (assert) {
        assert.expect(3);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            archs: {
                "documents.document,false,search": `
                    <search>
                        <filter name="owo" string="OwO" domain="[['id', '&lt;', 4]]"/>
                    </search>`
            },
        });

        // select a record and open the chatter
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        // reload with a domain
        await toggleFilterMenu(kanban.el);
        await toggleMenuItem(kanban.el, "OwO");

        assert.containsOnce(kanban, '.o_record_selected',
            "record should still be selected");
        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should still display the chatter");

        kanban.destroy();
    });

    QUnit.test('document chatter: close chatter when more than one record selected', async function (assert) {
        assert.expect(2);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        // select a record and open the chatter
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        // select another record alongside the first one
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();
        await testUtils.nextTick(); // need to wait a little longer to be sure chatter component is unmounted

        assert.containsNone(kanban, '.o_document_chatter_container .o_Chatter',
            "should have closed the chatter");

        kanban.destroy();
    });

    QUnit.test('document chatter: close chatter when no more selected record', async function (assert) {
        assert.expect(3);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            archs: {
                "documents.document,false,search": `
                    <search>
                        <filter name="owo" string="OwO" domain="[['id', '&gt;', 4]]"/>
                    </search>`
            },
        });

        // select a record and open the chatter
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(kanban, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        // reload with a domain
        await toggleFilterMenu(kanban.el);
        await toggleMenuItem(kanban.el, "OwO");

        assert.containsNone(kanban, '.o_record_selected',
            "no more record should be selected");
        assert.containsNone(kanban, '.o_document_chatter_container .o_Chatter',
            "should have closed the chatter");

        kanban.destroy();
    });

    QUnit.module('DocumentsSelector');

    QUnit.test('document selector: basic rendering', async function (assert) {
        assert.expect(18);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_section .o_search_panel_section_header').eq(0).text().trim(),
            'Workspace', "should have a 'Workspace' section");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_category_value', 3,
            "three of them should be visible");
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:eq(1) header'));
        assert.strictEqual(kanban.$('.o_documents_inspector_preview').text().replace(/\s+/g, ''),
            '_F1-test-description_', "should display the first workspace");

        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_section .o_search_panel_section_header').eq(1).text().trim(),
            'Tags', "should have a 'tags' section");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_filter_group', 2,
            "should have 2 facets");

        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:first label:first > span').text().replace(/\s/g, ''),
            '●Priority', "the first facet should be 'Priority'");
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:first label:first').attr('title').trim(),
            'A priority tooltip', "the first facet have a tooltip");
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:last label:first > span').text().replace(/\s/g, ''),
            '●Status', "the last facet should be 'Status'");
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:last label:first').attr('title').trim(),
            'A Status tooltip', "the last facet should be 'Status'");

        assert.containsN(kanban, '.o_search_panel .o_search_panel_filter_group:last .o_search_panel_filter_value', 2,
            "should have 2 tags in the last facet");

        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:last .o_search_panel_filter_value:first label').text().trim(),
            'Draft', "the first tag in the last facet should be 'Draft'");
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:last .o_search_panel_filter_value:first label').attr('title').trim(),
            'A Status tooltip', "the first tag in the last facet have a tooltip");
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:last .o_search_panel_filter_value:last label').text().trim(),
            'New', "the last tag in the last facet should be 'New'");
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_filter_group:last .o_search_panel_filter_value:last label').attr('title').trim(),
            'A Status tooltip', "the last tag in the last facet have a tooltip");

        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_section:nth-child(3) .o_search_panel_section_header').text().trim(),
            'Attached To', "should have an 'attached to' section");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_section:nth-child(3) .o_search_panel_filter_value', 4,
            "should have 4 types of models");
        assert.ok(testUtils.dom.find(kanban, '.o_search_panel_filter_value', "Task\n2"), "should display the correct number of records");
        assert.containsOnce(kanban.$('.o_search_panel'), '.o_search_panel_section:nth-child(3) .o_search_panel_filter_value:contains("Not attached")', "should at least have a no-model element");

        kanban.destroy();
    });

    QUnit.test('document selector: render without facets & tags', async function (assert) {
        assert.expect(3);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'search_panel_select_multi_range') {
                    return Promise.resolve({values: [], });
                }
                return this._super.apply(this, arguments);
            },
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        assert.strictEqual(kanban.$('.o_search_panel .o_documents_selector_tags .o_search_panel_section_header').text().trim(),
            '', "shouldn't have a 'tags' section");
        assert.containsNone(kanban, '.o_search_panel .o_search_panel_filter_group',
            "shouldn't have any facet");
        assert.containsNone(kanban, '.o_search_panel .o_search_panel_filter_group .o_search_panel_filter_value',
            "shouldn't have any tag");

        kanban.destroy();
    });

    QUnit.test('document selector: render without related models', async function (assert) {
        assert.expect(4);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            domain: [['res_model', '=', false]],
        });

        assert.containsNone(kanban, '.o_search_panel .o_documents_selector_tags .o_search_panel_section_header',
            "shouldn't have a 'tags' section");
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));
        assert.strictEqual(kanban.$('.o_search_panel .o_search_panel_section:nth-child(3) .o_search_panel_section_header').text().trim(),
            'Attached To', "should have an 'attached to' section");
        assert.containsNone(kanban, '.o_search_panel .o_search_panel_section:nth-child(3) .o_search_panel_filter_value:contains("Not attached")',
            "should not have an unattached document");
        assert.containsOnce(kanban, '.o_search_panel .o_search_panel_section:nth-child(3) .o_search_panel_filter_value:contains("Not a file")',
            "should at least have a no-model element");

        kanban.destroy();
    });

    QUnit.test('document selector: filter on related model', async function (assert) {
        assert.expect(8);

        // TO: decide what should be done for Attached To section
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(0)'));

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_section:nth-child(2) .o_search_panel_filter_value', 4, "should have 4 related models");

        // filter on 'Task'
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Task")
        );
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2, "should have 3 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_section:nth-child(2) .o_search_panel_filter_value', 4, "should have 4 related models");

        // filter on 'Sale Order' (should be a disjunction)
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Sale Order")
        );

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3, "should have 3 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_section:nth-child(2) .o_search_panel_filter_value', 4, "should still have 4 related models");

        // remove both filters
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Sale Order")
        );
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Task")
        );

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_section:nth-child(2) .o_search_panel_filter_value', 4, "should still have 4 related models");

        kanban.destroy();
    });

    QUnit.test('document selector: filter on attachments without related model', async function (assert) {
        assert.expect(8);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(0)'));

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_filter_value', 4, "should have 4 related models");

        // filter on 'Not a file'
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Not a file")
        );

        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', "should have 1 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_filter_value', 4, "should still have 4 related models");

        // filter on 'Task'
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Task")
        );
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3, "should have 4 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_filter_value', 4, "should still have 4 related models");

        // remove both filters
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Not a file")
        );
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Task")
        );

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(kanban, '.o_search_panel .o_search_panel_filter_value', 4, "should still have 4 related models");

        kanban.destroy();
    });

    QUnit.test('document selector: mix filter on related model and search filters', async function (assert) {
        assert.expect(10);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            archs: {
                "documents.document,false,search": `
                    <search>
                        <filter name="owo" string="OwO" domain="[['public', '=', True]]"/>
                    </search>`
            },
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(0)'));

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.ok(
            testUtils.dom.find(kanban, '.o_search_panel_filter_value', "Task\n2"),
            "should display the correct number of records"
        );

        // filter on 'Task'
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Task")
        );
        assert.strictEqual(kanban.$('.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 2, "should have 3 records in the renderer");

        // reload with a domain
        await toggleFilterMenu(kanban.el);
        await toggleMenuItem(kanban.el, "OwO");

        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 1, "should have 1 record in the renderer");
        assert.ok(
            testUtils.dom.find(kanban, '.o_search_panel_filter_value', "Task\n1"),
            "should display the correct number of records"
        );
        assert.ok(
            testUtils.dom.find(kanban, '.o_search_panel_filter_value', "Sale Order\n1"),
            "should display the correct number of records"
        );

        // filter on 'Sale Order'
        await testUtils.dom.click(
            testUtils.dom.find(kanban, '.o_search_panel_label_title', "Sale Order")
        );

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2, "should have 2 records in the renderer");

        // reload without the domain
        await toggleFilterMenu(kanban.el);
        await toggleMenuItem(kanban.el, "OwO");

        assert.strictEqual(kanban.$('.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 3, "should have 4 record in the renderer");
        assert.ok(
            testUtils.dom.find(kanban, '.o_search_panel_filter_value', "Task\n2"),
            "should display the correct number of records"
        );
        assert.ok(
            testUtils.dom.find(kanban, '.o_search_panel_filter_value', "Sale Order\n1"),
            "should display the correct number of records"
        );

        kanban.destroy();
    });

    QUnit.test('document selector: selected tags are reset when switching between workspaces', async function (assert) {
        assert.expect(6);

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read' && args.model === 'documents.document') {
                    assert.step(JSON.stringify(args.domain || []));
                }
                return this._super.apply(this, arguments);
            },
        });

        // filter on records having tag Draft
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:contains(Draft) input'));

        assert.ok(kanban.$('.o_search_panel_filter_value:contains(Draft) input').is(':checked'),
            "tag selector should be checked");

        // switch to Workspace2
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(Workspace2) header'));

        assert.ok(kanban.$('.o_search_panel_filter_value:contains(Draft) input').is(':checked'),
            "tag selector should not be checked anymore");

        assert.verifySteps([
            '[["folder_id","child_of",1]]',
            '["&",["folder_id","child_of",1],["tag_ids","in",[2]]]',
            '["&",["folder_id","child_of",2],["tag_ids","in",[2]]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('document selector: should keep its selection when adding a tag', async function (assert) {
        assert.expect(5);
        var done = assert.async();

        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value header:eq(1)'));

        // filter on records having tag Draft
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:contains(Draft) input'));

        assert.ok(kanban.$('.o_search_panel_filter_value:contains(Draft) input').is(':checked'),
            "tag selector should be checked");

        assert.strictEqual(kanban.$('.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length,
            4, "should have records in the renderer");

        await testUtils.dom.click(kanban.$('.o_kanban_record:first .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        searchValue('.o_inspector_tag_add', 'stress');
        concurrency.delay(0).then(async function () {
            assert.strictEqual(autocompleteLength(), 1,
                "should have an entry in the autocomplete drodown");
            var $autocomplete = kanban.$('.o_inspector_tag_add').autocomplete('widget');
            await testUtils.dom.click($autocomplete.find('li > a:first'));

            assert.ok(kanban.$('.o_search_panel_filter_value:contains(Draft) input').is(':checked'),
                        "tag selector should still be checked");
            assert.strictEqual(kanban.$('.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length,
            4, "should still have the same records in the renderer");

            kanban.destroy();
            done();
        });
    });

    QUnit.test('documents Kanban color widget', async function (assert) {
        assert.expect(4);
        var kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="tag_ids" widget="documents_many2many_tags"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });
        assert.containsN(kanban, '.o_field_many2manytags', 5,
            "All the records should have a color widget");

        assert.containsN(kanban, '.o_field_many2manytags:nth(2) > span', 3,
            "All the records should have 3 tags");

        assert.containsOnce(kanban.$('.o_field_many2manytags:nth(2) > span:first'), '> span',
            "should have a span for color ball");

        assert.strictEqual(kanban.$('.o_field_many2manytags:nth(2) > span:first > span').css('color'),
            "rgb(240, 96, 80)", "should have the right color");

        kanban.destroy();
    });

    QUnit.test('kanban color widget without SearchPanel', async function (assert) {
        assert.expect(5);

        const kanban = await createView({
            View: KanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `<kanban><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                        <field name="tag_ids" widget="documents_many2many_tags"/>
                    </div>
                </t></templates></kanban>`,
        });

        assert.containsN(kanban, '.o_field_many2manytags', 6,
            "All the records should have a color widget");

        assert.containsN(kanban, '.o_field_many2manytags:nth(2) > span', 3,
            "Third record should have 3 tags");

        assert.containsOnce(kanban.$('.o_field_many2manytags:nth(2) > span:first'), '> span',
            "should have a span for color ball");
        assert.containsN(kanban.$('.o_field_many2manytags:nth(2)'), '.o_tag_color_0', 3,
            "should have 3 spans for color ball with grey color by default");

        assert.strictEqual(kanban.$('.o_field_many2manytags:nth(2) > span:first > span').css('color'),
            "rgb(68, 75, 90)", "should have the right color");

        kanban.destroy();
    });

    QUnit.test('SearchPanel: can drag and drop in the search panel', async function (assert) {
        assert.expect(4);
        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'write' && args.model === 'documents.document') {
                    assert.deepEqual(
                        args.args[0],
                        [1, 4, 2],
                        "should write the right records");
                    assert.deepEqual(
                        args.args[1],
                        {folder_id: 2},
                        "should have written on a folder");
                    assert.step('documents.documents/write');
                }
                return this._super.apply(this, arguments);
            },
            arch: `
            <kanban><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area o_document_draggable">
                    <i class="fa fa-circle-thin o_record_selector"/>
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        const $yopRecord = kanban.$('.o_kanban_record:contains(yop) .o_record_selector');
        // selects three records
        await testUtils.dom.click($yopRecord);
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(burp) .o_record_selector'));
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(blip) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        // starts the drag on a selected record
        const startEvent = new Event('dragstart', { bubbles: true, });
        const dataTransfer = new DataTransfer();
        startEvent.dataTransfer = dataTransfer;
        $yopRecord[0].dispatchEvent(startEvent);

        // drop on the second search panel category (folder)
        const endEvent = new Event('drop', { bubbles: true, });
        endEvent.dataTransfer = dataTransfer;
        kanban.$('.o_search_panel_category_value header:eq(2)')[0].dispatchEvent(endEvent);

        assert.verifySteps(['documents.documents/write']);

        // makes sure that we are after the setTimeout of the dragStart handler
        // that removes the drag Icon from the DOM.
        await testUtils.nextTick();

        kanban.destroy();
    });

    QUnit.test('SearchPanel: can not drag and hover over the search panel All selector', async function (assert) {
        assert.expect(1);

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'write' && args.model === 'documents.document') {
                    throw new Error('It should not be possible to drop a record on the All selector');
                }
                return this._super.apply(this, arguments);
            },
            arch: `
            <kanban><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area o_document_draggable">
                    <i class="fa fa-circle-thin o_record_selector"/>
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        const $yopRecord = kanban.$('.o_kanban_record:contains(yop) .o_record_selector');
        const $allSelector = kanban.$('.o_search_panel_category_value:eq(0)');
        // selects one record
        await testUtils.dom.click($yopRecord);

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        // starts the drag on a selected record
        const startEvent = new Event('dragstart', { bubbles: true, });
        const dataTransfer = new DataTransfer();
        startEvent.dataTransfer = dataTransfer;
        $yopRecord[0].dispatchEvent(startEvent);

        const dragenterEvent = new Event('dragenter', { bubbles: true, });
        $allSelector[0].dispatchEvent(dragenterEvent);
         assert.doesNotHaveClass($allSelector, 'o_drag_over_selector',
            "the All selector should not have the hover effect");

        // drop on the "All" search panel category
        // it should not add another write step.
        const dropEvent = new Event('drop', { bubbles: true, });
        dropEvent.dataTransfer = dataTransfer;
        $allSelector.find('header')[0].dispatchEvent(dropEvent);

        // makes sure that we are after the setTimeout of the dragStart handler
        // that removes the drag Icon from the DOM.
        await testUtils.nextTick();

        kanban.destroy();
    });

    QUnit.test('documents: upload progress bars', async function (assert) {
        assert.expect(5);

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, () => assert.step('xhrSend'));

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
            <kanban><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        testUtils.file.dropFile(kanban.$('.o_documents_view'), file);
        assert.verifySteps(['xhrSend']);

        await testUtils.nextTick();

        const progressEvent = new Event('progress', { bubbles: true, });
        progressEvent.loaded = 250000000;
        progressEvent.total = 500000000;
        progressEvent.lengthComputable = true;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);
        assert.strictEqual(kanban.$('.o_file_upload_progress_text_left').text(), "Uploading... (50%)",
            "the current upload progress should be at 50%");

        assert.containsOnce(kanban, '.fa.fa-circle-o-notch');

        progressEvent.loaded = 350000000;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);
        assert.strictEqual(kanban.$('.o_file_upload_progress_text_right').text(), "(350/500Mb)",
            "the current upload progress should be at (350/500Mb)");

        kanban.destroy();
    });

    QUnit.test('documents: upload replace bars', async function (assert) {
        assert.expect(5);

        const documentId = 23;
        this.data['documents.document'].records = []; // reset incompatible setup
        this.data['documents.document'].records.push({
            folder_id: 1,
            id: documentId,
            name: 'request',
            type: 'empty',
        });

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const ORIGINAL_PROMPT_FILE_INPUT = DocumentsKanbanController.prototype._promptFileInput;
        DocumentsKanbanController.prototype._promptFileInput = $input => testUtils.file.inputFiles($input[0], [file]);

        this.patchDocumentXHR([], () => assert.step('xhrSend'));

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <kanban><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area o_documents_attachment" data-id="${documentId}">
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await testUtils.dom.click(kanban.$('.o_documents_attachment'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        await testUtils.dom.click(kanban.$('.o_inspector_request_icon'));
        await testUtils.nextTick();

        assert.verifySteps(['xhrSend']);

        assert.containsOnce(kanban, '.o_documents_attachment > .o_file_upload_progress_bar',
            "there should be a progress card");
        assert.containsOnce(kanban, '.o_documents_attachment > .o_file_upload_progress_bar > .o_file_upload_progress_bar_value',
            "there should be a progress bar");
        assert.containsOnce(kanban, '.o_documents_attachment > .o_file_upload_progress_bar > .o_upload_cross',
            "there should be cancel upload cross");

        kanban.destroy();
        DocumentsKanbanController.prototype._promptFileInput = ORIGINAL_PROMPT_FILE_INPUT;
    });

    QUnit.test('documents: upload multiple progress bars', async function (assert) {
        assert.expect(8);

        const file1 = await testUtils.file.createFile({
            name: 'text1.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        const file2 = await testUtils.file.createFile({
            name: 'text2.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        const file3 = await testUtils.file.createFile({
            name: 'text3.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, () => assert.step('xhrSend'));

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
            <kanban><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        const $dropZone = kanban.$('.o_documents_view');
        testUtils.file.dropFile($dropZone, file1);

        // awaiting next tick as the file drop is not synchronous
        await testUtils.nextTick();

        assert.verifySteps(['xhrSend']);
        assert.strictEqual(kanban.$('.o_kanban_record_title > span:eq(0)').text(), 'text1.txt',
            "The first kanban card should be named after the file");

        testUtils.file.dropFiles($dropZone, [file2, file3]);

        // awaiting next tick as the file drop is not synchronous
        await testUtils.nextTick();

        assert.verifySteps(['xhrSend']);
        assert.strictEqual(kanban.$('.o_kanban_record_title > span:eq(0)').text(), '2 Files',
            "The new kanban card should be named after the amount of files");
        assert.containsN(kanban, '.o_kanban_progress_card', 2, "There should be 2 cards");

        // simulates 1st upload successful completion
        mockedXHRs[1].response = JSON.stringify({
            success: "All files uploaded"
        });
        mockedXHRs[1].onload();

        // awaiting next tick as the render of the notify card isn't synchronous
        await testUtils.nextTick();

        assert.containsOnce(kanban, '.o_kanban_progress_card', "There should only be one card left");

        kanban.destroy();
    });

    QUnit.test('documents: notifies server side errors', async function (assert) {
        assert.expect(2);

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs);

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            services: {
                notification: {
                    notify(notification) {
                        assert.strictEqual(
                            notification.message,
                            "One or more file(s) failed to upload",
                            "the notification message should be the response error message"
                        );
                    },
                },
            },
            arch: `
            <kanban><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        const $dropZone = kanban.$('.o_documents_view');
        testUtils.file.dropFile($dropZone, file);
        await testUtils.nextTick();


        // simulates 1st upload server side error completion
        mockedXHRs[0].response = JSON.stringify({
            error: "One or more file(s) failed to upload"
        });
        mockedXHRs[0].status = 200;
        mockedXHRs[0].onload();
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_kanban_progress_card', "There should be no upload card left");
        kanban.destroy();
    });

    QUnit.test('documents Kanban: displays youtube thumbnails', async function (assert) {
        assert.expect(1);

        this.data['documents.document'].records.push({
            folder_id: 1,
            id: 12,
            name: 'youtubeVideo',
            type: 'url',
            url: 'https://youtu.be/Ayab6wZ_U1A'
        });

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <kanban><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(youtubeVideo) .o_record_selector'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(
            kanban.$('.o_documents_inspector img, .o_documents_single_preview .o_preview_available').attr('data-src'),
            "https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg",
            "the inspector should display the thumbnail of the youtube video");
        kanban.destroy();
    });

    QUnit.test('documents List: multi selection', async function (assert) {
        assert.expect(4);

        const list = await createDocumentsView({
            View: DocumentsListView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <tree>
                    <field name="type" invisible="1"/>
                    <field name="name"/>
                    <field name="partner_id"/>
                    <field name="owner_id"/>
                    <field name="type"/>
                </tree>`,
        });

        const $record = list.$('.o_document_list_record[data-res-id="2"]');
        await testUtils.dom.click($record);
        assert.ok($record.find('.o_list_record_selector input').prop('checked'), "the record should be selected");

        list.$('.o_document_list_record[data-res-id="5"]').trigger($.Event('click', {
            shiftKey: true,
        }));
        await testUtils.nextTick();
        assert.containsN(list, '.o_list_record_selector input:checked', 4, "there should be 4 selected records");

        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsN(list, '.o_list_record_selector input:checked', 6, "All (6) records should be selected");

        await testUtils.dom.click(list.$('thead .o_list_record_selector input'));
        assert.containsNone(list, '.o_list_record_selector input:checked', "No record should be selected");

        list.destroy();
    });

    QUnit.test('documents List: selection using keyboard', async function (assert) {
        assert.expect(6);

        const list = await createDocumentsView({
            View: DocumentsListView,
            model: 'documents.document',
            data: this.data,
            arch: `
            <tree>
                <field name="type" invisible="1"/>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="owner_id"/>
                <field name="type"/>
            </tree>`,
        });

        let $recordSelector = list.$('.o_document_list_record[data-res-id="5"] .o_list_record_selector');
        $recordSelector.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();
        assert.containsOnce(list, '.o_list_record_selector input:checked',
            "there should be 1 selected record");
        assert.ok($recordSelector.find('input').prop('checked'),
            "the right record should be selected");

        $recordSelector = list.$('.o_document_list_record[data-res-id="4"] .o_list_record_selector');
        $recordSelector.focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();
        assert.containsOnce(list, '.o_list_record_selector input:checked',
            "there should be 1 selected record");
        assert.ok($recordSelector.find('input').prop('checked'),
            "the right record should be selected");

        // Press Enter key with Shift key should select multiple records
        list.$('.o_document_list_record[data-res-id="3"] td:first').focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
            shiftKey: true,
        }));
        await testUtils.nextTick();
        assert.containsN(list, '.o_list_record_selector input:checked', 2,
            "there should be 2 selected records");

        list.$('.o_document_list_record[data-res-id="2"] .o_list_record_selector').focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.SPACE,
            which: $.ui.keyCode.SPACE,
        }));
        await testUtils.nextTick();
        assert.containsN(list, '.o_list_record_selector input:checked', 3,
            "there should be 3 selected records");

        list.destroy();
    });

    QUnit.test('documents List: listview is not groupable', async function (assert) {
        assert.expect(1);

        const list = await createDocumentsView({
            View: DocumentsListView,
            model: 'documents.document',
            data: this.data,
            arch: `
            <tree>
                <field name="type" invisible="1"/>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="owner_id"/>
                <field name="type"/>
            </tree>`,
        });

        assert.containsNone(list, '.o_control_panel div.o_search_options div.o_group_by_menu',
            "there should not be groupby menu");

        list.destroy();
    });

    QUnit.test('documents: Versioning', async function (assert) {
        assert.expect(13);

        this.data['documents.document'].records.push({
            folder_id: 1,
            id: 12,
            name: 'newYoutubeVideo',
            type: 'url',
            url: 'https://youtu.be/Ayab6wZ_U1A',
            previous_attachment_ids: [99],
        });
        this.data['ir.attachment'].records.push({
            id: 99,
            name: 'oldYoutubeVideo',
            create_date: '2019-12-09 14:13:21',
            create_uid: 12,
        });

        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: 'documents.document',
            data: this.data,
            arch: `
                <kanban><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area">
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            async mockRPC(route, args) {
                if (args.model === 'ir.attachment' && args.method === 'unlink') {
                    assert.deepEqual(args.args[0], [99],
                        "should unlink the right attachment");
                    assert.step('attachmentUnlinked');
                    return;
                }
                if (args.model === 'documents.document' && args.method === 'write') {
                    assert.deepEqual(args.args[0], [12],
                        "should target the right document");
                    assert.deepEqual(args.args[1], {attachment_id: 99},
                        "should target the right attachment");
                    assert.step('attachmentRestored');
                    return;
                }
                return this._super(...arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_kanban_record:nth(5)'));

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        assert.strictEqual(kanban.$('.o_inspector_history_name').text(), 'oldYoutubeVideo',
            "should display the correct record name");
        assert.strictEqual(kanban.$('.o_inspector_history_create_name').text(), 'Lukaku',
            "should display the correct name");
        assert.strictEqual(
            kanban.$('.o_inspector_history_info_date').text(),
            str_to_datetime('2019-12-09 14:13:21').toLocaleDateString(),
            "should display the correct date"
        );

        assert.containsOnce(kanban, '.o_inspector_history_item_restore',
            "There should be one restore button");
        assert.containsOnce(kanban, '.o_inspector_history_item_download',
            "There should be one download button");
        assert.containsOnce(kanban, '.o_inspector_history_item_delete',
            "There should be one delete button");

        await testUtils.dom.click(kanban.$('.o_inspector_history_item_restore'));
        assert.verifySteps(['attachmentRestored']);
        await testUtils.dom.click(kanban.$('.o_inspector_history_item_delete'));
        assert.verifySteps(['attachmentUnlinked']);
        kanban.destroy();
    });

    QUnit.test("store and retrieve active category value", async function (assert) {
        assert.expect(8);

        let expectedActiveId = 3;
        const storageKey = "searchpanel_documents.document_folder_id";
        const Storage = RamStorage.extend({
            init() {
                this._super(...arguments);
                this.setItem(storageKey, expectedActiveId);
            },
            getItem(key) {
                const value = this._super(...arguments);
                if (key === storageKey) {
                    assert.step(`storage get ${value}`);
                }
                return value;
            },
            setItem(key, value) {
                if (key === storageKey) {
                    assert.step(`storage set ${value}`);
                }
                this._super(...arguments);
            },
        });
        const local_storage = AbstractStorageService.extend({
            storage: new Storage(),
        });
        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: "documents.document",
            data: this.data,
            services: { local_storage },
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="name"/>
                        </div>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (route === "/web/dataset/search_read") {
                    assert.deepEqual(args.domain, [["folder_id", "child_of", expectedActiveId]]);
                }
                return this._super(...arguments);
            },
        });

        assert.containsOnce(kanban, ".o_search_panel_category_value .active");
        assert.containsOnce(kanban, ".o_search_panel_category_value:nth(1) .active");

        expectedActiveId = 2;
        await testUtils.dom.click(kanban.$(".o_search_panel_category_value:nth(3) header"));

        assert.verifySteps([
            "storage set 3", // Manual set for initial value
            "storage get 3",
            "storage set 2", // Set on toggle
        ]);

        kanban.destroy();
    });

    QUnit.test("retrieved category value does not exist", async function (assert) {
        assert.expect(5);

        const storageKey = "searchpanel_documents.document_folder_id";
        const Storage = RamStorage.extend({
            init() {
                this._super(...arguments);
                this.setItem(storageKey, 343); // Doesn't exist
            },
            getItem(key) {
                const value = this._super(...arguments);
                if (key === storageKey) {
                    assert.step(`storage get ${value}`);
                }
                return value;
            },
        });
        const local_storage = AbstractStorageService.extend({
            storage: new Storage(),
        });
        const kanban = await createDocumentsView({
            View: DocumentsKanbanView,
            model: "documents.document",
            data: this.data,
            services: { local_storage },
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="name"/>
                        </div>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (route === "/web/dataset/search_read") {
                    assert.deepEqual(args.domain, [["folder_id", "child_of", 1]]);
                }
                return this._super(...arguments);
            },
        });

        assert.containsOnce(kanban, ".o_search_panel_category_value .active");
        assert.containsOnce(kanban, ".o_search_panel_category_value:nth(1) .active");

        assert.verifySteps(["storage get 343"]);

        kanban.destroy();
    });
});
});

});
