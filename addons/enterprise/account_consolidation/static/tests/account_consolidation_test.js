odoo.define('account_consolidation.FieldJsonTests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');
    const ListView = require('web.ListView');
    const createView = testUtils.createView;

    QUnit.module('fields', {
        beforeEach: function () {
            this.data = {
                foo: {
                    fields: {
                        json: {string: 'Json', type: 'text'},
                    },
                    records: [
                        {
                            id: 1
                        },
                        {
                            id: 2,
                            json: '[["Section 1","126.00 €"],["Section 2","294.00 €"]]'
                        }
                    ]
                }
            }
        }
    }, function() {
        QUnit.test('render empty json field', async function (assert) {
            assert.expect(1);

            const view = await createView({
                debug: 1,
                View: ListView,
                model: 'foo',
                data: this.data,
                arch: `
                    <tree editable="top" multi_edit="1">
                        <field name="json" widget="json"/>
                    </tree>`
            });

            assert.equal(view.$('.o_field_json').length, 2, "Both records are rendered");

            view.destroy();
        });
    });
});
