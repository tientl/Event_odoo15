odoo.define('industry_fsm_sale.fsm_product_quantity_tests', function (require) {
"use strict";

const ProductKanbanView = require('industry_fsm_sale.ProductKanbanView');
const {
    dom,
    createView,
    nextTick,
} = require('web.test_utils');

QUnit.module('industry_fsm_sale', {}, function () {
    QUnit.module('FSMProductQuantity', {
        beforeEach(assert) {
            this.data = {
                'product.product': {
                    fields: {
                        fsm_quantity: { string: "Material Quantity", type: 'integer' },
                    },
                    records: [
                        { id: 1, fsm_quantity: 0 },
                        { id: 2, fsm_quantity: 0 },
                        { id: 3, fsm_quantity: 1 },
                    ],
                },
            };

            this.kanban = {
                hasView: true,
                View: ProductKanbanView,
                model: 'product.product',
                data: this.data,
                res_id: 1,
                async mockRPC(route, params) {
                    const { args, model, method } = params;
                    if (method === 'fsm_remove_quantity') {
                        const [id] = args;
                        return new Promise((resolve, reject) => {
                            const records = this.data[model].records.map((record) => {
                                if (id === record.id) {
                                    record.fsm_quantity -= 1;
                                }
                                return record;
                            });
                            assert.step('fsm_remove_quantity');
                            return resolve(true);
                        });
                    } else if (method === 'fsm_add_quantity') {
                        const [id] = args;
                        return new Promise((resolve, reject) => {
                            const records = this.data[model].records.map((record) => {
                                if (id === record.id) {
                                    record.fsm_quantity += 1;
                                }
                                return record;
                            });
                            assert.step('fsm_add_quantity');
                            return resolve(true);
                        });
                    } else if (method === 'set_fsm_quantity') {
                        const [id, quantity] = args;
                        return new Promise((resolve, reject) => {
                            const records = this.data[model].records.map((record) => {
                                if (id === record.id) {
                                    record.fsm_quantity = quantity;
                                }
                                return record;
                            });
                            assert.step('set_fsm_quantity');
                            return resolve(true);
                        });
                    }
                    return this._super(...arguments);
                },
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div class="o_fsm_industry_product">
                                    <field name="fsm_quantity" widget="fsm_product_quantity"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
            };
        },
    });

    QUnit.test('fsm_product_quantity widget in kanban view', async function (assert) {
        assert.expect(7);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(1) input[name="fsm_quantity"]').val(), "0", "The product quantity should be equal to 0.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(2) input[name="fsm_quantity"]').val(), "0", "The product quantity should be equal to 0.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(3) input[name="fsm_quantity"]').val(), "1", "The product quantity should be equal to 1.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(1) input[name="fsm_quantity"]').attr("type"), "number", "The input type should be number");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(2) input[name="fsm_quantity"]').attr("type"), "number", "The input type should be number");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(3) input[name="fsm_quantity"]').attr("type"), "number", "The input type should be number");
        kanban.destroy();
    });

    QUnit.test('fsm_product_quantity: click on fsm_remove_button to decrease the quantity.', async function (assert) {
        assert.expect(6);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");
        kanban.$('.o_fsm_industry_product button[name="fsm_remove_quantity"]').click();
        assert.verifySteps(['fsm_remove_quantity']);
        await kanban.reload();

        // Normally, only the last one should be decrease because the others have the quantity is equal to 0 and then we must not decrease it.
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(1) input[name="fsm_quantity"]').val(), "0", "The product quantity should be equal to 0.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(2) input[name="fsm_quantity"]').val(), "0", "The product quantity should be equal to 0.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(3) input[name="fsm_quantity"]').val(), "0", "The product quantity should be equal to 0.");

        kanban.destroy();
    });

    QUnit.test('fsm_product_quantity: click on fsm_add_button to add a quantity unit in a product', async function (assert) {
        assert.expect(8);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");

        // Click on the button for each product in the kanban view
        kanban.$('.o_fsm_industry_product button[name="fsm_add_quantity"]').click();
        assert.verifySteps(['fsm_add_quantity', 'fsm_add_quantity', 'fsm_add_quantity']);
        await kanban.reload();
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(1) input[name="fsm_quantity"]').val(), "1", "The product quantity should be equal to 1.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(2) input[name="fsm_quantity"]').val(), "1", "The product quantity should be equal to 1.");
        assert.strictEqual(kanban.$('.o_fsm_industry_product:nth-child(3) input[name="fsm_quantity"]').val(), "2", "The product quantity should be equal to 2.");

        kanban.destroy();
    });

    QUnit.test('fsm_product_quantity: edit manually the product quantity', async function (assert) {
        assert.expect(9);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");
        const $firstFsmQuantitySpan = kanban.$('.o_fsm_industry_product:first() input[name="fsm_quantity"]');
        assert.strictEqual($firstFsmQuantitySpan.val(), "0", "The product quantity should be equal to 0.");
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), true, "The produdt quantity should not be editable.");

        $firstFsmQuantitySpan.click();
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), false, "The product quantity should be editable.");
        document.execCommand('insertText', false, "12");
        await dom.triggerEvent($firstFsmQuantitySpan, 'blur');
        assert.verifySteps(['set_fsm_quantity']);
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), true, "The product quantity should not be editable.");
        assert.doesNotHaveClass($firstFsmQuantitySpan, 'o_field_invalid', "the element should not be formatted like there is an error.");
        assert.strictEqual($firstFsmQuantitySpan.val(), "12", "The content of the span tag should be the one written by the user.");

        kanban.destroy();
    });

    QUnit.test('fsm_product_quantity: edit manually a wrong product quantity', async function (assert) {
        assert.expect(9);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");
        let $firstFsmQuantitySpan = kanban.$('.o_fsm_industry_product:nth(0) input[name="fsm_quantity"]');
        assert.strictEqual($firstFsmQuantitySpan.val(), "0", "The product quantity should be equal to 0.");
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), true, "The product quantity should not be editable.");

        $firstFsmQuantitySpan.click();
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), false, "The product quantity should be editable.");

        document.execCommand('insertText', false, "12a");
        await dom.triggerEvent($firstFsmQuantitySpan, 'blur');
        assert.strictEqual($firstFsmQuantitySpan.val(), "12", "Input with number type shouldn't allow character");

        $firstFsmQuantitySpan.click();
        $firstFsmQuantitySpan.val(""); // simulate the deleting of the text
        document.execCommand('insertText', false, "12");
        await dom.triggerEvent($firstFsmQuantitySpan, 'blur');
        assert.verifySteps(['set_fsm_quantity']);
        assert.doesNotHaveClass($firstFsmQuantitySpan, 'o_field_invalid', "the element should not be formatted like there is an error.");
        assert.strictEqual($firstFsmQuantitySpan.val(), "12", "The content of the span tag should be 12 units of product quantity.");
        kanban.destroy();
    });

    QUnit.test('fsm_product_quantity: edit manually and press ENTER key to save the edition', async function (assert) {
        assert.expect(9);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");
        let $firstFsmQuantitySpan = kanban.$('.o_fsm_industry_product:nth(0) input[name="fsm_quantity"]');
        assert.strictEqual($firstFsmQuantitySpan.val(), '0', "The product quantity should be equal to 0.");
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), true, "The product quantity should not be editable.");

        $firstFsmQuantitySpan.click();
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), false, "The product quantity should be editable.");

        document.execCommand('insertText', false, '42');

        const target = document.activeElement;
        assert.strictEqual($firstFsmQuantitySpan[0], target, "The active element should be the first product quantity span tag.");
        await dom.triggerEvent(target, 'keydown', { key: 'Enter', which: 13 });
        assert.verifySteps(['set_fsm_quantity']);
        assert.doesNotHaveClass($firstFsmQuantitySpan, 'o_field_invalid', "The element should not be formatted like there is an error.");
        assert.strictEqual($firstFsmQuantitySpan.val(), '42', "The content of the span tag should be 12 units of product quantity.");
        kanban.destroy();
    });

    QUnit.test('fsm_product_quantity: when the user edits and enters more than 5 digits, a class should be added to the active span.', async function (assert) {
        assert.expect(10);

        const kanban = await createView(this.kanban);

        assert.containsN(kanban, '.o_fsm_industry_product', 3, "The number of kanban record should be equal to 3 records.");
        let $firstFsmQuantitySpan = kanban.$('.o_fsm_industry_product:nth(0) input[name="fsm_quantity"]');
        assert.strictEqual($firstFsmQuantitySpan.val(), '0', "The product quantity should be equal to 0.");
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), true, "The product quantity should not be editable.");
        assert.doesNotHaveClass($firstFsmQuantitySpan, 'small', "The product quantity should not have this class.");

        $firstFsmQuantitySpan.click();
        assert.strictEqual($firstFsmQuantitySpan.prop('readonly'), false, "The product quantity should be editable.");

        document.execCommand('insertText', false, '123456');

        assert.hasClass($firstFsmQuantitySpan, 'small', "The font size of the product quantity should be smaller than before.");
        const target = document.activeElement;
        assert.strictEqual($firstFsmQuantitySpan[0], target, "The active element should be the first product quantity span tag.");
        assert.strictEqual($firstFsmQuantitySpan.val(), '123456', "The content of the span tag should be 123456 units of product quantity.");
        document.execCommand('delete');
        assert.strictEqual($firstFsmQuantitySpan.val(), '12345', "The content of the span tag should be 12345 units of product quantity.");
        assert.doesNotHaveClass($firstFsmQuantitySpan, 'small', "The product quantity should not have this class.");

        kanban.destroy();
    });
});

});
