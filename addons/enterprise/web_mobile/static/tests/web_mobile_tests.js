odoo.define("web_mobile.tests", function (require) {
    "use strict";

    const Dialog = require("web.Dialog");
    const dom = require("web.dom");
    const FormView = require("web.FormView");
    const OwlDialog = require("web.OwlDialog");
    const Popover = require("web.Popover");
    const session = require("web.session");
    const makeTestEnvironment = require("web.test_env");
    const testUtils = require("web.test_utils");
    const Widget = require("web.Widget");

    const { useBackButton } = require("web_mobile.hooks");
    const {
        BackButtonEventMixin,
        UpdateDeviceAccountControllerMixin,
    } = require("web_mobile.mixins");
    const mobile = require("web_mobile.core");
    const UserPreferencesFormView = require("web_mobile.UserPreferencesFormView");
    const { base64ToBlob } = require("web_mobile.testUtils");

    const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');

    const { Component, tags, useState } = owl;
    const { xml } = tags;

    const { createParent, createView, mock } = testUtils;

    const MY_IMAGE =
        "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";
    const BASE64_SVG_IMAGE =
        "PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPScxNzUnIGhlaWdodD0nMTAwJyBmaWxsPScjMDAwJz48cG9seWdvbiBwb2ludHM9JzAsMCAxMDAsMCA1MCw1MCcvPjwvc3ZnPg==";
    const BASE64_PNG_HEADER = "iVBORw0KGg";

    QUnit.module(
        "web_mobile",
        {
            beforeEach: function () {
                this.data = {
                    partner: {
                        fields: {
                            name: { string: "name", type: "char" },
                            avatar_1920: {},
                            parent_id: { string: "Parent", type: "many2one", relation: "partner" },
                            sibling_ids: {
                                string: "Sibling",
                                type: "many2many",
                                relation: "partner",
                            },
                            phone: {},
                            mobile: {},
                            email: {},
                            street: {},
                            street2: {},
                            city: {},
                            state_id: {},
                            zip: {},
                            country_id: {},
                            website: {},
                            function: {},
                            title: {},
                            date: { string: "A date", type: "date" },
                            datetime: { string: "A datetime", type: "datetime" },
                        },
                        records: [
                            {
                                id: 1,
                                name: "coucou1",
                            },
                            {
                                id: 2,
                                name: "coucou2",
                            },
                            {
                                id: 11,
                                name: "coucou3",
                                avatar_1920: "image",
                                parent_id: 1,
                                phone: "phone",
                                mobile: "mobile",
                                email: "email",
                                street: "street",
                                street2: "street2",
                                city: "city",
                                state_id: "state_id",
                                zip: "zip",
                                country_id: "country_id",
                                website: "website",
                                function: "function",
                                title: "title",
                            },
                        ],
                    },
                    users: {
                        fields: {
                            name: { string: "name", type: "char" },
                        },
                        records: [],
                    },
                };
            },
        },
        function () {
            QUnit.module("core", function () {
                QUnit.test("BackButtonManager", async function (assert) {
                    assert.expect(13);

                    mock.patch(mobile.methods, {
                        overrideBackButton({ enabled }) {
                            assert.step(`overrideBackButton: ${enabled}`);
                        },
                    });

                    const { BackButtonManager, BackButtonListenerError } = mobile;
                    const manager = new BackButtonManager();
                    const DummyWidget = Widget.extend({
                        _onBackButton(ev) {
                            assert.step(`${ev.type} event`);
                        },
                    });
                    const dummy = new DummyWidget();

                    manager.addListener(dummy, dummy._onBackButton);
                    assert.verifySteps(["overrideBackButton: true"]);

                    // simulate 'backbutton' event triggered by the app
                    await testUtils.dom.triggerEvent(document, "backbutton");
                    assert.verifySteps(["backbutton event"]);

                    manager.removeListener(dummy);
                    assert.verifySteps(["overrideBackButton: false"]);
                    await testUtils.dom.triggerEvent(document, "backbutton");
                    assert.verifySteps([], "shouldn't trigger any handler");

                    manager.addListener(dummy, dummy._onBackButton);
                    assert.throws(
                        () => {
                            manager.addListener(dummy, dummy._onBackButton);
                        },
                        BackButtonListenerError,
                        "should raise an error if adding a listener twice"
                    );
                    assert.verifySteps(["overrideBackButton: true"]);

                    manager.removeListener(dummy);
                    assert.throws(
                        () => {
                            manager.removeListener(dummy);
                        },
                        BackButtonListenerError,
                        "should raise an error if removing a non-registered listener"
                    );
                    assert.verifySteps(["overrideBackButton: false"]);

                    dummy.destroy();
                    mock.unpatch(mobile.methods);
                });
            });

            QUnit.module("BackButtonEventMixin");

            QUnit.test("widget should receive a backbutton event", async function (assert) {
                assert.expect(5);

                const __overrideBackButton = mobile.methods.overrideBackButton;
                mobile.methods.overrideBackButton = function ({ enabled }) {
                    assert.step(`overrideBackButton: ${enabled}`);
                };

                const DummyWidget = Widget.extend(BackButtonEventMixin, {
                    _onBackButton(ev) {
                        assert.step(`${ev.type} event`);
                    },
                });
                const backButtonEvent = new Event("backbutton");
                const dummy = new DummyWidget();
                dummy.appendTo($("<div>"));

                // simulate 'backbutton' event triggered by the app
                document.dispatchEvent(backButtonEvent);
                // waiting nextTick to match testUtils.dom.triggerEvents() behavior
                await testUtils.nextTick();

                assert.verifySteps([], "shouldn't have register handle before attached to the DOM");

                dom.append($("qunit-fixture"), dummy.$el, {
                    in_DOM: true,
                    callbacks: [{ widget: dummy }],
                });

                // simulate 'backbutton' event triggered by the app
                document.dispatchEvent(backButtonEvent);
                await testUtils.nextTick();

                dom.detach([{ widget: dummy }]);

                assert.verifySteps(
                    ["overrideBackButton: true", "backbutton event", "overrideBackButton: false"],
                    "should have enabled/disabled the back-button override"
                );

                dummy.destroy();
                mobile.methods.overrideBackButton = __overrideBackButton;
            });

            QUnit.test(
                "multiple widgets should receive backbutton events in the right order",
                async function (assert) {
                    assert.expect(6);

                    const __overrideBackButton = mobile.methods.overrideBackButton;
                    mobile.methods.overrideBackButton = function ({ enabled }) {
                        assert.step(`overrideBackButton: ${enabled}`);
                    };

                    const DummyWidget = Widget.extend(BackButtonEventMixin, {
                        init(parent, { name }) {
                            this._super.apply(this, arguments);
                            this.name = name;
                        },
                        _onBackButton(ev) {
                            assert.step(`${this.name}: ${ev.type} event`);
                            dom.detach([{ widget: this }]);
                        },
                    });
                    const backButtonEvent = new Event("backbutton");
                    const dummy1 = new DummyWidget(null, { name: "dummy1" });
                    dom.append($("qunit-fixture"), dummy1.$el, {
                        in_DOM: true,
                        callbacks: [{ widget: dummy1 }],
                    });

                    const dummy2 = new DummyWidget(null, { name: "dummy2" });
                    dom.append($("qunit-fixture"), dummy2.$el, {
                        in_DOM: true,
                        callbacks: [{ widget: dummy2 }],
                    });

                    const dummy3 = new DummyWidget(null, { name: "dummy3" });
                    dom.append($("qunit-fixture"), dummy3.$el, {
                        in_DOM: true,
                        callbacks: [{ widget: dummy3 }],
                    });

                    // simulate 'backbutton' events triggered by the app
                    document.dispatchEvent(backButtonEvent);
                    // waiting nextTick to match testUtils.dom.triggerEvents() behavior
                    await testUtils.nextTick();
                    document.dispatchEvent(backButtonEvent);
                    await testUtils.nextTick();
                    document.dispatchEvent(backButtonEvent);
                    await testUtils.nextTick();

                    assert.verifySteps([
                        "overrideBackButton: true",
                        "dummy3: backbutton event",
                        "dummy2: backbutton event",
                        "dummy1: backbutton event",
                        "overrideBackButton: false",
                    ]);

                    dummy1.destroy();
                    dummy2.destroy();
                    dummy3.destroy();
                    mobile.methods.overrideBackButton = __overrideBackButton;
                }
            );

            QUnit.module("useBackButton");

            QUnit.test("component should receive a backbutton event", async function (assert) {
                assert.expect(5);

                mock.patch(mobile.methods, {
                    overrideBackButton({ enabled }) {
                        assert.step(`overrideBackButton: ${enabled}`);
                    },
                });

                class DummyComponent extends Component {
                    constructor() {
                        super();
                        this._backButtonHandler = useBackButton(this._onBackButton);
                    }

                    _onBackButton(ev) {
                        assert.step(`${ev.type} event`);
                    }
                }
                DummyComponent.template = xml`<div/>`;

                const dummy = new DummyComponent();

                await dummy.mount(document.createDocumentFragment());
                // simulate 'backbutton' event triggered by the app
                await testUtils.dom.triggerEvent(document, "backbutton");
                assert.verifySteps([], "shouldn't have register handle before attached to the DOM");
                dummy.unmount();

                await dummy.mount(document.getElementById("qunit-fixture"));
                // simulate 'backbutton' event triggered by the app
                await testUtils.dom.triggerEvent(document, "backbutton");
                dummy.unmount();
                assert.verifySteps(
                    ["overrideBackButton: true", "backbutton event", "overrideBackButton: false"],
                    "should have enabled/disabled the back-button override"
                );

                dummy.destroy();
                mock.unpatch(mobile.methods);
            });

            QUnit.test(
                "multiple components should receive backbutton events in the right order",
                async function (assert) {
                    assert.expect(6);

                    mock.patch(mobile.methods, {
                        overrideBackButton({ enabled }) {
                            assert.step(`overrideBackButton: ${enabled}`);
                        },
                    });

                    class DummyComponent extends Component {
                        constructor() {
                            super(...arguments);
                            this._backButtonHandler = useBackButton(this._onBackButton);
                        }

                        _onBackButton(ev) {
                            assert.step(`${this.props.name}: ${ev.type} event`);
                            this.unmount();
                        }
                    }
                    DummyComponent.template = xml`<div/>`;

                    const fixture = document.getElementById("qunit-fixture");

                    const dummy1 = new DummyComponent(null, { name: "dummy1" });
                    await dummy1.mount(fixture);

                    const dummy2 = new DummyComponent(null, { name: "dummy2" });
                    await dummy2.mount(fixture);

                    const dummy3 = new DummyComponent(null, { name: "dummy3" });
                    await dummy3.mount(fixture);

                    // simulate 'backbutton' events triggered by the app
                    await testUtils.dom.triggerEvent(document, "backbutton");
                    await testUtils.dom.triggerEvent(document, "backbutton");
                    await testUtils.dom.triggerEvent(document, "backbutton");

                    assert.verifySteps([
                        "overrideBackButton: true",
                        "dummy3: backbutton event",
                        "dummy2: backbutton event",
                        "dummy1: backbutton event",
                        "overrideBackButton: false",
                    ]);

                    dummy1.destroy();
                    dummy2.destroy();
                    dummy3.destroy();
                    mock.unpatch(mobile.methods);
                }
            );

            QUnit.test(
                "component should receive a backbutton event: custom activation",
                async function (assert) {
                    assert.expect(10);

                    mock.patch(mobile.methods, {
                        overrideBackButton({ enabled }) {
                            assert.step(`overrideBackButton: ${enabled}`);
                        },
                    });

                    class DummyComponent extends Component {
                        constructor() {
                            super();
                            this._backButtonHandler = useBackButton(
                                this._onBackButton,
                                this.shouldActivateBackButton.bind(this)
                            );
                            this.state = useState({
                                show: false,
                            });
                        }

                        toggle() {
                            this.state.show = !this.state.show;
                        }

                        shouldActivateBackButton() {
                            return this.state.show;
                        }

                        _onBackButton(ev) {
                            assert.step(`${ev.type} event`);
                        }
                    }
                    DummyComponent.template = xml`<button t-esc="state.show" t-on-click="toggle"/>`;

                    const dummy = new DummyComponent();

                    await dummy.mount(document.getElementById("qunit-fixture"));
                    assert.verifySteps([], "shouldn't have enabled backbutton mount");
                    await testUtils.dom.click(dummy.el);
                    // simulate 'backbutton' event triggered by the app
                    await testUtils.dom.triggerEvent(document, "backbutton");
                    await testUtils.dom.click(dummy.el);
                    assert.verifySteps(
                        [
                            "overrideBackButton: true",
                            "backbutton event",
                            "overrideBackButton: false",
                        ],
                        "should have enabled/disabled the back-button override"
                    );
                    dummy.unmount();

                    // enabled at mount
                    dummy.state.show = true;
                    await dummy.mount(document.getElementById("qunit-fixture"));
                    assert.verifySteps(
                        ["overrideBackButton: true"],
                        "shouldn have enabled backbutton at mount"
                    );
                    // simulate 'backbutton' event triggered by the app
                    await testUtils.dom.triggerEvent(document, "backbutton");
                    // unmounting without disabling first
                    dummy.unmount();
                    assert.verifySteps(
                        ["backbutton event", "overrideBackButton: false"],
                        "should have disabled the back-button override during unmount"
                    );

                    dummy.destroy();
                    mock.unpatch(mobile.methods);
                }
            );

            QUnit.module("Dialog");

            QUnit.test("dialog is closable with backbutton event", async function (assert) {
                assert.expect(7);

                const __overrideBackButton = mobile.methods.overrideBackButton;
                mobile.methods.overrideBackButton = function ({ enabled }) {
                    assert.step(`overrideBackButton: ${enabled}`);
                };

                testUtils.mock.patch(Dialog, {
                    close: function () {
                        assert.step("close");
                        return this._super.apply(this, arguments);
                    },
                });

                const parent = await createParent({
                    data: this.data,
                    archs: {
                        "partner,false,form": `
                    <form>
                        <sheet>
                            <field name="name"/>
                        </sheet>
                   </form>
                `,
                    },
                });

                const backButtonEvent = new Event("backbutton");
                const dialog = new Dialog(parent, {
                    res_model: "partner",
                    res_id: 1,
                }).open();
                await dialog.opened().then(() => {
                    assert.step("opened");
                });
                assert.containsOnce(document.body, ".modal", "should have a modal");

                // simulate 'backbutton' event triggered by the app waiting
                document.dispatchEvent(backButtonEvent);
                // nextTick to match testUtils.dom.triggerEvents() behavior
                await testUtils.nextTick();

                // The goal of this assert is to check that our event called the
                // opened/close methods on Dialog.
                assert.verifySteps(
                    ["overrideBackButton: true", "opened", "close", "overrideBackButton: false"],
                    "should have open/close dialog"
                );
                assert.containsNone(document.body, ".modal", "modal should be closed");

                parent.destroy();
                testUtils.mock.unpatch(Dialog);
                mobile.methods.overrideBackButton = __overrideBackButton;
            });

            QUnit.module("OwlDialog");

            QUnit.test("dialog is closable with backbutton event", async function (assert) {
                assert.expect(7);

                mock.patch(mobile.methods, {
                    overrideBackButton({ enabled }) {
                        assert.step(`overrideBackButton: ${enabled}`);
                    },
                });

                class Parent extends Component {
                    constructor() {
                        super(...arguments);
                        this.state = useState({ display: true });
                    }
                    _onDialogClosed() {
                        this.state.display = false;
                        assert.step("dialog_closed");
                    }
                }

                Parent.components = { OwlDialog };
                Parent.env = makeTestEnvironment();
                Parent.template = xml`
            <div>
                <OwlDialog
                    t-if="state.display"
                    t-on-dialog-closed="_onDialogClosed">
                    Some content
                </OwlDialog>
            </div>`;

                const parent = new Parent();
                await parent.mount(testUtils.prepareTarget());

                assert.containsOnce(document.body, ".o_dialog");
                assert.verifySteps(["overrideBackButton: true"]);
                // simulate 'backbutton' event triggered by the app
                await testUtils.dom.triggerEvent(document, "backbutton");
                assert.verifySteps(["dialog_closed", "overrideBackButton: false"]);
                assert.containsNone(document.body, ".o_dialog", "should have been closed");

                parent.destroy();
                mock.unpatch(mobile.methods);
            });

            QUnit.module("Popover");

            QUnit.test("popover is closable with backbutton event", async function (assert) {
                assert.expect(7);

                mock.patch(mobile.methods, {
                    overrideBackButton({ enabled }) {
                        assert.step(`overrideBackButton: ${enabled}`);
                    },
                });

                class Parent extends Component {}

                Parent.components = { Popover };
                Parent.env = makeTestEnvironment();
                Parent.template = xml`
            <div>
                <Popover>
                    <t t-set="opened">
                        Some content
                    </t>
                    <button id="target">
                        Show me
                    </button>
                </Popover>
            </div>`;

                const parent = new Parent();
                await parent.mount(testUtils.prepareTarget());

                assert.containsNone(document.body, ".o_popover");
                await testUtils.dom.click(document.querySelector("#target"));
                assert.containsOnce(document.body, ".o_popover");
                assert.verifySteps(["overrideBackButton: true"]);
                // simulate 'backbutton' event triggered by the app
                await testUtils.dom.triggerEvent(document, "backbutton");
                assert.verifySteps(["overrideBackButton: false"]);
                assert.containsNone(document.body, ".o_popover", "should have been closed");

                parent.destroy();
                mock.unpatch(mobile.methods);
            });

            QUnit.module("ControlPanel");

            QUnit.test("mobile search: close with backbutton event", async function (assert) {
                assert.expect(7);

                mock.patch(mobile.methods, {
                    overrideBackButton({ enabled }) {
                        assert.step(`overrideBackButton: ${enabled}`);
                    },
                });

                const actions = {
                    1: {
                        id: 1,
                        name: "Yes",
                        res_model: "partner",
                        type: "ir.actions.act_window",
                        views: [[false, "list"]],
                    },
                };

                const views = {
                    "partner,false,list": '<tree><field name="foo"/></tree>',
                    "partner,false,search": `
                <search>
                    <filter string="Active" name="my_projects" domain="[('boolean_field', '=', True)]"/>
                    <field name="foo" string="Foo"/>
                </search>`,
                };

                const models = {
                    partner: {
                        fields: {
                            foo: { string: "Foo", type: "char" },
                            boolean_field: { string: "I am a boolean", type: "boolean" },
                        },
                        records: [{ id: 1, display_name: "First record", foo: "yop" }],
                    },
                };
                const serverData = {actions, models, views};

                const webClient = await createWebClient({ serverData });

                await doAction(webClient, 1);

                assert.containsNone(document.body, ".o_mobile_search");

                // open the search view
                await testUtils.dom.click(
                    webClient.el.querySelector("button.o_enable_searchview")
                );
                // open it in full screen
                await testUtils.dom.click(
                    webClient.el.querySelector(".o_toggle_searchview_full")
                );

                assert.containsOnce(document.body, ".o_mobile_search");
                assert.verifySteps(["overrideBackButton: true"]);

                // simulate 'backbutton' event triggered by the app
                await testUtils.dom.triggerEvent(document, "backbutton");
                assert.containsNone(document.body, ".o_mobile_search");
                assert.verifySteps(["overrideBackButton: false"]);

                mock.unpatch(mobile.methods);
            });

            QUnit.module("UpdateDeviceAccountControllerMixin");

            QUnit.test(
                "controller should call native updateAccount method when saving record",
                async function (assert) {
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

                    const DummyView = FormView.extend({
                        config: Object.assign({}, FormView.prototype.config, {
                            Controller: FormView.prototype.config.Controller.extend(
                                UpdateDeviceAccountControllerMixin
                            ),
                        }),
                    });

                    const dummy = await createView({
                        View: DummyView,
                        model: "partner",
                        data: this.data,
                        arch: `
                <form>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
                        viewOptions: {
                            mode: "edit",
                        },
                        session: {
                            username: "demo",
                            name: "Marc Demo",
                        },
                    });

                    await testUtils.form.clickSave(dummy);
                    await dummy.savingDef;

                    dummy.destroy();
                    testUtils.mock.unpatch(session);
                    mobile.methods.updateAccount = __updateAccount;
                }
            );

            QUnit.test(
                "controller should call native updateAccount method with SVG avatar when saving record",
                async function (assert) {
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
                                return `data:image/svg+xml;base64,${BASE64_SVG_IMAGE}`;
                            }
                            return this._super(...arguments);
                        },
                    });

                    const DummyView = FormView.extend({
                        config: Object.assign({}, FormView.prototype.config, {
                            Controller: FormView.prototype.config.Controller.extend(
                                UpdateDeviceAccountControllerMixin
                            ),
                        }),
                    });

                    const dummy = await createView({
                        View: DummyView,
                        model: "partner",
                        data: this.data,
                        arch: `
                <form>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
                        viewOptions: {
                            mode: "edit",
                        },
                        session: {
                            username: "demo",
                            name: "Marc Demo",
                        },
                    });

                    await testUtils.form.clickSave(dummy);
                    await dummy.savingDef;

                    dummy.destroy();
                    testUtils.mock.unpatch(session);
                    mobile.methods.updateAccount = __updateAccount;
                }
            );

            QUnit.test(
                "UserPreferencesFormView should call native updateAccount method when saving record",
                async function (assert) {
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
                        View: UserPreferencesFormView,
                        model: "users",
                        data: this.data,
                        arch: `
                <form>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
                        viewOptions: {
                            mode: "edit",
                        },
                        session: {
                            username: "demo",
                            name: "Marc Demo",
                        },
                    });

                    await testUtils.form.clickSave(view);
                    await view.savingDef;

                    view.destroy();
                    testUtils.mock.unpatch(session);
                    mobile.methods.updateAccount = __updateAccount;
                }
            );

            QUnit.module("FieldDate");

            QUnit.test("date field: toggle datepicker", async function (assert) {
                assert.expect(8);

                mock.patch(mobile.methods, {
                    requestDateTimePicker({ value, type }) {
                        assert.step("requestDateTimePicker");
                        assert.strictEqual(false, value, "field shouldn't have an initial value");
                        assert.strictEqual("date", type, "datepicker's mode should be 'date'");
                        return Promise.resolve({ data: "2020-01-12" });
                    },
                });

                const form = await createView({
                    View: FormView,
                    model: "partner",
                    data: this.data,
                    arch: '<form><field name="date"/><field name="name"/></form>',
                    translateParameters: {
                        // Avoid issues due to localization formats
                        date_format: "%m/%d/%Y",
                    },
                });

                assert.containsNone(
                    document.body,
                    ".bootstrap-datetimepicker-widget",
                    "datepicker shouldn't be present initially"
                );

                await testUtils.dom.openDatepicker(form.$(".o_datepicker"));

                assert.containsNone(
                    document.body,
                    ".bootstrap-datetimepicker-widget",
                    "datepicker shouldn't be opened"
                );
                assert.verifySteps(
                    ["requestDateTimePicker"],
                    "native datepicker should have been called"
                );
                // ensure focus has been restored to the date field
                form.$(".o_datepicker_input").focus();
                assert.strictEqual(
                    form.$(".o_datepicker_input").val(),
                    "01/12/2020",
                    "should be properly formatted"
                );

                // focus another field
                await testUtils.dom.click(form.$(".o_field_widget[name=name]").focus());
                assert.strictEqual(
                    form.$(".o_datepicker_input").val(),
                    "01/12/2020",
                    "shouldn't have changed after loosing focus"
                );

                form.destroy();
                mock.unpatch(mobile.methods);
            });

            QUnit.module("FieldDateTime");

            QUnit.test("datetime field: toggle datepicker", async function (assert) {
                assert.expect(8);

                mock.patch(mobile.methods, {
                    requestDateTimePicker({ value, type }) {
                        assert.step("requestDateTimePicker");
                        assert.strictEqual(false, value, "field shouldn't have an initial value");
                        assert.strictEqual(
                            "datetime",
                            type,
                            "datepicker's mode should be 'datetime'"
                        );
                        return Promise.resolve({ data: "2020-01-12 12:00:00" });
                    },
                });

                const form = await createView({
                    View: FormView,
                    model: "partner",
                    data: this.data,
                    arch: '<form><field name="datetime"/><field name="name"/></form>',
                    translateParameters: {
                        // Avoid issues due to localization formats
                        date_format: "%m/%d/%Y",
                        time_format: "%H:%M:%S",
                    },
                });

                assert.containsNone(
                    document.body,
                    ".bootstrap-datetimepicker-widget",
                    "datepicker shouldn't be present initially"
                );

                await testUtils.dom.openDatepicker(form.$(".o_datepicker"));

                assert.containsNone(
                    document.body,
                    ".bootstrap-datetimepicker-widget",
                    "datepicker shouldn't be opened"
                );
                assert.verifySteps(
                    ["requestDateTimePicker"],
                    "native datepicker should have been called"
                );
                // ensure focus has been restored to the datetime field
                form.$(".o_datepicker_input").focus();
                assert.strictEqual(
                    form.$(".o_datepicker_input").val(),
                    "01/12/2020 12:00:00",
                    "should be properly formatted"
                );

                // focus another field
                await testUtils.dom.click(form.$(".o_field_widget[name=name]").focus());
                assert.strictEqual(
                    form.$(".o_datepicker_input").val(),
                    "01/12/2020 12:00:00",
                    "shouldn't have changed after loosing focus"
                );

                form.destroy();
                mock.unpatch(mobile.methods);
            });
        }
    );
});
