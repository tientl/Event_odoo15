/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

import { file } from 'web.test_utils';
import config from 'web.config';
import FormView from 'web.FormView';
import testUtils from 'web.test_utils';
const { createFile, inputFiles } = file;

QUnit.module('mail_enterprise', {}, function () {
QUnit.module('attachment_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        Object.assign(this.data, {
            partner: {
                fields: {
                    message_attachment_count: { string: 'Attachment count', type: 'integer' },
                    display_name: { string: "Displayed name", type: "char" },
                    foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                    message_ids: { string: "messages", type: "one2many", relation: 'mail.message', relation_field: "res_id" },
                },
                records: [{
                    id: 2,
                    message_attachment_count: 0,
                    display_name: "first partner",
                    foo: "HELLO",
                    message_ids: [],
                }],
            },
        });
    },
    afterEach() {
        afterEach(this);
    },
}, function () {

    QUnit.test('Should not have attachment preview for still uploading attachment', async function (assert) {
        assert.expect(2);
        let form;
        await afterNextRender(async () => { // because of chatter container
            const { env, widget } = await start({
                hasView: true,
                View: FormView,
                model: 'res.partner',
                data: this.data,
                arch: '<form string="Partners">' +
                        '<div class="o_attachment_preview" options="{\'order\':\'desc\'}"></div>' +
                        '<div class="oe_chatter">' +
                            '<field name="message_ids"/>' +
                        '</div>' +
                    '</form>',
                // FIXME could be removed once task-2248306 is done
                archs: {
                    'mail.message,false,list': '<tree/>',
                },
                res_id: 2,
                config: {
                    device: {
                        size_class: config.device.SIZES.XXL,
                    },
                },
                async mockRPC(route, args) {
                    if (_.str.contains(route, '/web/static/lib/pdfjs/web/viewer.html')) {
                        assert.step("pdf viewer");
                    }
                    return this._super.apply(this, arguments);
                },
                async mockFetch(resource, init) {
                    const res = this._super(...arguments);
                    if (resource === '/mail/attachment/upload') {
                        await new Promise(() => {});
                    }
                    return res;
                }
            });
            this.env = env;
            form = widget;
        });

        await afterNextRender(() =>
            document.querySelector('.o_ChatterTopbar_buttonAttachments').click()
        );
        const files = [
            await createFile({ name: 'invoice.pdf', contentType: 'application/pdf' }),
        ];
        await afterNextRender(() =>
            inputFiles(document.querySelector('.o_FileUploader_input'), files)
        );
        assert.containsNone(form, '.o_attachment_preview_container');
        assert.verifySteps([], "The page should never render a PDF while it is uploading, as the uploading is blocked in this test we should never render a PDF preview");
        form.destroy();
    });

    QUnit.test('Attachment on side', async function (assert) {
        assert.expect(10);

        this.data.partner.records[0].message_ids = [11];
        this.data['ir.attachment'].records.push({
            id: 1,
            mimetype: 'image/jpeg',
            res_id: 2,
            res_model: 'partner',
        });
        this.data['mail.message'].records.push({
            id: 11,
            attachment_ids: [1],
            model: 'partner',
            res_id: 2,
        });
        let form;
        await afterNextRender(async () => { // because of chatter container
            const { env, widget } = await start({
                hasView: true,
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="foo"/>' +
                        '</sheet>' +
                        '<div class="o_attachment_preview" options="{\'order\':\'desc\'}"></div>' +
                        '<div class="oe_chatter">' +
                            '<field name="message_ids"/>' +
                        '</div>' +
                    '</form>',
                // FIXME could be removed once task-2248306 is done
                archs: {
                    'mail.message,false,list': '<tree/>',
                },
                res_id: 2,
                config: {
                    device: {
                        size_class: config.device.SIZES.XXL,
                    },
                },
                async mockRPC(route, args) {
                    if (_.str.contains(route, '/web/static/lib/pdfjs/web/viewer.html')) {
                        var canvas = document.createElement('canvas');
                        return canvas.toDataURL();
                    }
                    if (args.method === 'register_as_main_attachment') {
                        return true;
                    }
                    return this._super.apply(this, arguments);
                },
            });
            this.env = env;
            form = widget;
        });

        assert.containsOnce(form, '.o_attachment_preview_img > img',
            "There should be an image for attachment preview");
        assert.containsOnce(form, '.o_form_sheet_bg > .o_FormRenderer_chatterContainer',
            "Chatter should moved inside sheet");
        assert.doesNotHaveClass(
            document.querySelector('.o_FormRenderer_chatterContainer'),
            'o-aside',
            "Chatter should not have o-aside class as it is below form view and not aside",
        );
        assert.containsOnce(form, '.o_form_sheet_bg + .o_attachment_preview',
            "Attachment preview should be next sibling to .o_form_sheet_bg");

        // Don't display arrow if there is no previous/next element
        assert.containsNone(form, '.arrow',
            "Don't display arrow if there is no previous/next attachment");

        // send a message with attached PDF file
        await afterNextRender(() =>
            document.querySelector('.o_ChatterTopbar_buttonSendMessage').click()
        );
        const files = [
            await createFile({ name: 'invoice.pdf', contentType: 'application/pdf' }),
        ];
        await afterNextRender(() =>
            inputFiles(document.querySelector('.o_FileUploader_input'), files)
        );
        await afterNextRender(() =>
            document.querySelector('.o_Composer_buttonSend').click()
        );

        assert.containsN(form, '.arrow', 2,
            "Display arrows if there multiple attachments");
        assert.containsNone(form, '.o_attachment_preview_img > img',
            "Preview image should be removed");
        assert.containsOnce(form, '.o_attachment_preview_container > iframe',
            "There should be iframe for pdf viewer");
        await testUtils.dom.click(form.$('.o_move_next'), {allowInvisible:true});
        assert.containsOnce(form, '.o_attachment_preview_img > img',
            "Display next attachment");
        await testUtils.dom.click(form.$('.o_move_previous'), {allowInvisible:true});
        assert.containsOnce(form, '.o_attachment_preview_container > iframe',
            "Display preview attachment");
        form.destroy();
    });

    QUnit.test('After switching record with the form pager, when using the attachment preview navigation, the attachment should be switched',
        async function (assert) {
            assert.expect(4);

            this.data.partner.records[0].message_ids = [11, 12];
            this.data['ir.attachment'].records.push({
                id: 1,
                mimetype: 'image/jpeg',
                res_id: 2,
                res_model: 'partner',
            });
            this.data['mail.message'].records.push({
                id: 11,
                attachment_ids: [1],
                model: 'partner',
                res_id: 2,
            });

            this.data['ir.attachment'].records.push({
                id: 2,
                mimetype: 'application/pdf',
                res_id: 2,
                res_model: 'partner',
            });
            this.data['mail.message'].records.push({
                id: 12,
                attachment_ids: [3],
                model: 'partner',
                res_id: 2,
            });

            this.data.partner.records.push({
                id: 3,
                message_attachment_count: 0,
                display_name: 'second partner',
                foo: 'HELLO',
                message_ids: [],
            });

            const {widget: form} = await start({
                hasView: true,
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: `
                    <form string="Partners">
                        <sheet>
                            <field name="foo"/>
                        </sheet>
                        <div class="o_attachment_preview" options="{'order':'desc'}"></div>
                        <div class="oe_chatter">
                            <field name="message_ids"/>
                        </div>
                    </form>`,
                // FIXME could be removed once task-2248306 is done
                archs: {
                    'mail.message,false,list': '<tree/>',
                },
                res_id: 2,
                viewOptions: {
                    ids: [2, 3],
                    index: 0,
                },
                config: {
                    device: {
                        size_class: config.device.SIZES.XXL,
                    },
                },
                async mockRPC(route, args) {
                    if (route.includes('/web/static/lib/pdfjs/web/viewer.html')) {
                        return document.createElement('canvas').toDataURL();
                    }
                    if (args.method === 'register_as_main_attachment') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            });

            assert.strictEqual($('.o_pager_counter').text(), '1 / 2',
                'The form view pager should display 1 / 2');

            await testUtils.dom.click(form.$('.o_pager_next'));
            await testUtils.dom.click(form.$('.o_pager_previous'));
            assert.containsN(form, '.arrow', 2,
                'The attachment preview should contain 2 arrows to navigated between attachments');

            await testUtils.dom.click(form.$('.o_attachment_preview_container .o_move_next'), {allowInvisible: true});
            assert.containsOnce(form, '.o_attachment_preview_img img',
                'The second attachment (of type img) should be displayed');

            await testUtils.dom.click(form.$('.o_attachment_preview_container .o_move_previous'), {allowInvisible: true});
            assert.containsOnce(form, '.o_attachment_preview_container iframe',
                'The first attachment (of type pdf) should be displayed');

            form.destroy();
        });

    QUnit.test('Attachment on side on new record', async function (assert) {
        assert.expect(3);

        let form;
        await afterNextRender(async () => { // because of chatter container
            const { env, widget } = await start({
                hasView: true,
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="foo"/>' +
                        '</sheet>' +
                        '<div class="o_attachment_preview" options="{\'order\':\'desc\'}"></div>' +
                        '<div class="oe_chatter">' +
                            '<field name="message_ids"/>' +
                        '</div>' +
                    '</form>',
                // FIXME could be removed once task-2248306 is done
                archs: {
                    'mail.message,false,list': '<tree/>',
                },
                config: {
                    device: {
                        size_class: config.device.SIZES.XXL,
                    },
                },
            });
            this.env = env;
            this.widget = widget;
            form = widget;
        });

        assert.containsOnce(form, '.o_form_sheet_bg .o_attachment_preview',
            "the preview should not be displayed");
        assert.strictEqual(form.$('.o_form_sheet_bg .o_attachment_preview').children().length, 0,
            "the preview should be empty");
        assert.containsOnce(form, '.o_form_sheet_bg + .o_FormRenderer_chatterContainer',
            "chatter should not have been moved");

        form.destroy();
    });

    QUnit.test('Attachment on side not displayed on smaller screens', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].message_ids = [11];
        this.data['ir.attachment'].records.push({
            id: 1,
            mimetype: 'image/jpeg',
            res_id: 2,
            res_model: 'partner',
        });
        this.data['mail.message'].records.push({
            id: 11,
            attachment_ids: [1],
            model: 'partner',
            res_id: 2,
        });
        let form;
        await afterNextRender(async () => { // because of chatter container
            const { env, widget } = await start({
                hasView: true,
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="foo"/>' +
                        '</sheet>' +
                        '<div class="o_attachment_preview" options="{\'order\':\'desc\'}"></div>' +
                        '<div class="oe_chatter">' +
                            '<field name="message_ids"/>' +
                        '</div>' +
                    '</form>',
                // FIXME could be removed once task-2248306 is done
                archs: {
                    'mail.message,false,list': '<tree/>',
                },
                res_id: 2,
                config: {
                    device: {
                        size_class: config.device.SIZES.XL,
                    },
                },
            });
            this.env = env;
            this.widget = widget;
            form = widget;
        });
        assert.strictEqual(form.$('.o_attachment_preview').children().length, 0,
            "there should be nothing previewed");
        assert.containsOnce(form, '.o_form_sheet_bg + .o_FormRenderer_chatterContainer',
            "chatter should not have been moved");

        form.destroy();
    });

    QUnit.test('Attachment triggers list resize', async function (assert) {
        assert.expect(3);

        this.data.partner.fields.yeses = { relation: 'yes', string: "Yeses", type: 'many2many' };
        this.data.partner.records[0].yeses = [-1720932];
        this.data.yes = {
            fields: { the_char: { string: "The Char", type: 'char' } },
            records: [{ id: -1720932, the_char: new Array(100).fill().map(_ => "yes").join() }],
        };
        this.data['ir.attachment'].records.push({
            id: 1,
            mimetype: 'image/jpeg',
            name: 'Test Image 1',
            res_id: 2,
            res_model: 'partner',
            url: '/web/content/1?download=true',
        });
        const attachmentLoaded = testUtils.makeTestPromise();
        const { widget: form } = await start({
            hasView: true,
            arch: `
                <form string="Whatever">
                    <sheet>
                        <field name="yeses"/>
                    </sheet>
                    <div class="o_attachment_preview" options="{ 'order': 'desc' }"/>
                    <div class="oe_chatter">
                        <field name="message_ids"/>
                    </div>
                </form>`,
            archs: {
                // FIXME could be removed once task-2248306 is done
                'mail.message,false,list': '<tree/>',
                'yes,false,list': `
                    <tree>
                        <field name="the_char"/>
                    </tree>`,
            },
            async mockRPC(route, { method }) {
                const _super = this._super.bind(this, ...arguments); // limitation of class.js
                if (route === '/web/image/1?unique=1') {
                    await testUtils.nextTick();
                    attachmentLoaded.resolve();
                }
                switch (method) {
                    case 'register_as_main_attachment':
                        return true;
                }
                return _super();
            },
            config: {
                device: { size_class: config.device.SIZES.XXL },
            },
            data: this.data,
            model: 'partner',
            res_id: 2,
            View: FormView,
        });

        // Sets an arbitrary width to check if it is correctly overriden.
        form.el.querySelector('table th').style.width = '0px';

        assert.containsNone(form, 'img#attachment_img');

        await attachmentLoaded;

        assert.containsOnce(form, 'img#attachment_img');
        assert.notEqual(form.el.querySelector('table th').style.width, '0px',
            "List should have been resized after the attachment has been appended.");

        form.destroy();
    });
});
});
