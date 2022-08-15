odoo.define('hr_mobile.language_mobile_tests', function (require) {
    "use strict";
    
    const EmployeeProfileFormView = require('@hr/js/language')[Symbol.for("default")];
    const session = require('web.session');
    const testUtils = require('web.test_utils');

    const mobile = require('web_mobile.core');
    const { base64ToBlob } = require('web_mobile.testUtils');

    const { createView } = testUtils;

    const MY_IMAGE = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
    const BASE64_PNG_HEADER = "iVBORw0KGg";

    QUnit.module('hr_mobile', {
        beforeEach() {
            this.data = {
                users: {
                    fields: {
                        name: { string: "name", type: "char" },
                    },
                    records: [],
                },
            };
        },
    }, function () {
        QUnit.test('EmployeeProfileFormView should call native updateAccount method when saving record', async function (assert) {
            assert.expect(4);

            const __updateAccount = mobile.methods.updateAccount;
            mobile.methods.updateAccount = function (options) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            };

            testUtils.mock.patch(session, {
                url(path) {
                    if (path === '/web/image') {
                        return `data:image/png;base64,${MY_IMAGE}`;
                    }
                    return this._super(...arguments);
                },
            });

            const view = await createView({
                View: EmployeeProfileFormView,
                model: 'users',
                data: this.data,
                arch: `
                    <form>
                        <sheet>
                            <field name="name"/>
                        </sheet>
                    </form>`,
                viewOptions: {
                    mode: 'edit',
                },
                session: {
                    username: "demo",
                    name: "Marc Demo",
                }
            });

            await testUtils.form.clickSave(view);
            await view.savingDef;

            view.destroy();
            testUtils.mock.unpatch(session);
            mobile.methods.updateAccount = __updateAccount;
        });
    });
});
