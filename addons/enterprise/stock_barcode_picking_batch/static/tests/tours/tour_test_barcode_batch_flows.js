odoo.define('test_barcode_batch_flows.tour', function(require) {
'use strict';

const tour = require('web_tour.tour');
const helper = require('stock_barcode_picking_batch.tourHelper');

function checkState(state) {
    helper.assertPageSummary(state.pageSummary);
    helper.assertPreviousVisible(state.previous.isVisible);
    helper.assertPreviousEnabled(state.previous.isEnabled);
    helper.assertNextVisible(state.next.isVisible);
    helper.assertNextEnabled(state.next.isEnabled);
    helper.assertNextIsHighlighted(state.next.isHighlighted);
    helper.assertLinesCount(state.linesCount);
    helper.assertScanMessage(state.scanMessage);
    helper.assertPager(state.pager);
    helper.assertValidateVisible(state.validate.isVisible);
    helper.assertValidateIsHighlighted(state.validate.isHighlighted);
    helper.assertValidateEnabled(state.validate.isEnabled);
}

function updateState(oldState, newState) {
    const state = Object.assign({}, oldState, newState);
    const buttonNames = ['next', 'previous', 'validate'];
    for (const buttonName of buttonNames) {
        state[buttonName] = Object.assign({}, oldState[buttonName], newState[buttonName]);
    }
    return state;
}

const defaultViewState = {
    destLocationHighlight: false,
    locationHighlight: false,
    linesCount: 0,
    next: {
        isEnabled: false,
        isHighlighted: false,
        isVisible: false,
    },
    nextEnabled: false,
    nextIsHighlighted: false,
    nextVisible: false,
    pageSummary: '',
    pager: '0/0',
    previous: {
        isEnabled: false,
        isVisible: false,
    },
    scanMessage: '',
    validate: {
        isEnabled: false,
        isHighlighted: false,
        isVisible: false,
    },
};
let currentViewState;

// ----------------------------------------------------------------------------
// Tours
// ----------------------------------------------------------------------------
tour.register('test_barcode_batch_receipt_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 5, // 6 move lines but 5 visibles as tracked by SN lines are grouped.
                pager: '1/1',
                pageSummary: 'To WH/Stock',
                previous: {isVisible: false},
                scanMessage: 'scan_product',
                validate: {
                    isEnabled: true,
                    isVisible: true,
                },
            });
            checkState(currentViewState);
            const $linesFromFirstPicking = $(helper.getLines({index: [1, 5]}));
            const $linesFromSecondPicking = $(helper.getLines({from: 2, to: 3}));
            const $linesFromThirdPicking = $(helper.getLines({index: 4}));
            helper.assertLinesBelongTo($linesFromFirstPicking, 'picking_receipt_1');
            helper.assertLinesBelongTo($linesFromSecondPicking, 'picking_receipt_2');
            helper.assertLinesBelongTo($linesFromThirdPicking, 'picking_receipt_3');
        },
    },
    // Unfolds grouped lines for product tracked by SN.
    { trigger: '.o_line_button.o_toggle_sublines' },
    {
        trigger: '.o_sublines .o_barcode_line',
        run: function () {
            const sublines = document.querySelectorAll('.o_sublines .o_barcode_line');
            helper.assert(sublines.length, 2, 'it should have 2 sublines');
        }
    },

    //Check show information.
    {
        trigger: '.o_show_information',
    },
    {
        trigger: '.o_form_label:contains("State")',
    },
    {
        trigger: '.o_close',
    },

    // Scan product1 x4
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("1")',
        run: function() {
            currentViewState.scanMessage = 'scan_product_or_dest';
            checkState(currentViewState);
            const $lines =  helper.getLines({barcode: 'product1'});
            helper.assert($lines.length, 2, "Expect 2 lines for product1");
            helper.assertLineIsHighlighted($lines, true);
            helper.assertLineQty($($lines[1]), '1');
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("3")',
        run: function() {
            checkState(currentViewState);
            const $lines =  helper.getLines({barcode: 'product1'});
            helper.assert($lines.length, 2, "Expect 2 lines for product1");
            helper.assertLineIsHighlightedGreen($lines, true);
            helper.assertLineQty($($lines[0]), '1');
            helper.assertLineQty($($lines[1]), '3');
        }
    },

    // Scan one more time the product1 -> As no more quantity is expected, it must create
    // a new line and it will take the picking id of the selected line (here, 'picking_receipt_2').
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line:nth-child(6)',
        run: function() {
            currentViewState.linesCount = 6;
            checkState(currentViewState);
            const $lines =  helper.getLines({barcode: 'product1'});
            helper.assert($lines.length, 3, "Expect 3 lines for product1");
            const $line1 = $($lines[0]);
            const $line2 = $($lines[1]);
            const $line3 = $($lines[2]);
            helper.assertLineQty($line1, '1'); // Last added line:      qty 1
            helper.assertLineIsHighlightedGreen($line1, true);
            helper.assert($line1.find('.o_picking_label').text(), 'picking_receipt_2');
            helper.assertLineQty($line2, '1'); // First product1 line:  qty 1/1
            helper.assertLineIsHighlighted($line2, false);
            helper.assertLineQty($line3, '3'); // Second product1 line: qty 3/3
            helper.assertLineIsHighlighted($line3, false);
        }
    },

    // Scan productserial1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line:nth-child(4).o_highlight[data-barcode="productserial1"]',
        run: function() {
            currentViewState.scanMessage = 'scan_serial';
            checkState(currentViewState);
            const sublines = document.querySelectorAll('.o_barcode_line.o_selected .o_sublines .o_barcode_line');
            helper.assert(sublines.length, 2);
            helper.assertLineQty($(sublines[0]), '0');
            helper.assertLineIsHighlighted($(sublines[0]), true);
            helper.assertLineQty($(sublines[1]), '0');
            helper.assertLineIsHighlighted($(sublines[1]), false);
        }
    },

    // Scan two serial numbers
    {
        trigger: '.o_barcode_client_action',
        run: 'scan SN-LHOOQ'
    },
    {
        trigger: '.o_barcode_line.o_highlight[data-barcode="productserial1"]:contains("SN-LHOOQ")',
        run: function() {
            currentViewState.scanMessage = 'scan_product_or_dest';
            checkState(currentViewState);
            const sublines = document.querySelectorAll('.o_sublines [data-barcode=productserial1]');
            helper.assert(sublines.length, 2, "Expect 2 lines for productserial1");
            helper.assertLineQty($(sublines[0]), '0');
            helper.assertLineQty($(sublines[1]), '1');
        }
    },
    // Scan the same serial number -> Should show an warning message.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan SN-LHOOQ'
    },
    {
        trigger: '.o_notification.bg-danger'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan SN-OQPAPT'
    },
    {
        trigger: '.o_barcode_line.o_highlight[data-barcode="productserial1"]:contains("SN-OQPAPT")',
        run: function() {
            checkState(currentViewState);
            const sublines = document.querySelectorAll('.o_sublines [data-barcode=productserial1]');
            helper.assert(sublines.length, 2, "Expect 2 lines for productserial1");
            helper.assertLineQty($(sublines[0]), '1');
            helper.assertLineQty($(sublines[1]), '1');
        }
    },

    // Scan productlot1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_barcode_line.o_highlight[data-barcode="productlot1"]',
        run: function() {
            currentViewState.scanMessage = 'scan_lot';
            checkState(currentViewState);
            const $lines =  helper.getLines({barcode: 'productlot1'});
            helper.assert($lines.length, 2, "Expect 2 lines for productlot1");
            const $line1 = $($lines[0]);
            const $line2 = $($lines[1]);
            helper.assertLineQty($line1, '0');
            helper.assertLineIsHighlighted($line1, true);
            helper.assert($line1.find('.o_picking_label').text(), 'picking_receipt_2');
            helper.assertLineQty($line2, '0');
            helper.assertLineIsHighlighted($line2, false);
            helper.assert($line2.find('.o_picking_label').text(), 'picking_receipt_3');
        }
    },

    // Scan lot0001 x4
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_line.o_highlight .qty-done:contains("4")',
        run: function() {
            currentViewState.scanMessage = 'scan_lot';
            checkState(currentViewState);
            const $lines =  helper.getLines({barcode: 'productlot1'});
            helper.assert($lines.length, 2, "Expect 2 lines for productlot1");
            const $line1 = $($lines[0]);
            const $line2 = $($lines[1]);
            helper.assertLineQty($line1, '4');
            helper.assertLineIsHighlighted($line1, true);
            helper.assert($line1.find('.o_picking_label').text(), 'picking_receipt_2');
            helper.assertLineQty($line2, '0');
            helper.assertLineIsHighlighted($line2, false);
            helper.assert($line2.find('.o_picking_label').text(), 'picking_receipt_3');
        },
    },
    // Open the view to add a line and close it immediately.
    {
        trigger: '.o_add_line',
    },
    {
        trigger: '.o_discard',
    },
    {
        trigger: '.o_validate_page',
        run: function() {
            checkState(currentViewState);
        },
    },

    // Create a new line for productlot1 with an another lot name...
    {
        trigger: '.o_add_line',
    },
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text productlot1',
    },
    {
        trigger: ".ui-menu-item > a:contains('productlot1')",
    },
    {
        trigger: "input.o_field_widget[name=qty_done]",
        run: 'text 0',
    },
    {
        trigger: ".o_field_widget[name=picking_id] input",
        run: 'text picking_receipt_2',
    },
    {
        trigger: ".ui-menu-item > a:contains('picking_receipt_2')",
    },
    {
        trigger: '.o_save',
    },
    {
        trigger: '.o_sublines .o_barcode_line:nth-child(2)',
        run: function() {
            checkState(currentViewState);
            const groupLines =  document.querySelectorAll('.o_barcode_lines > [data-barcode=productlot1]');
            helper.assert(groupLines.length, 2, "Expect 2 lines for productlot1");
            const sublines = document.querySelectorAll('.o_sublines [data-barcode=productlot1]');
            helper.assert(sublines.length, 2, "Expect 2 sublines for productlot1");
            helper.assertLineQty($(sublines[0]), '4'); // Previous line (4/8).
            helper.assertLineIsHighlighted($(sublines[0]), false);
            helper.assertLineQty($(sublines[1]), '0'); // New created line.
            helper.assertLineIsHighlighted($(sublines[1]), true);
        },
    },

    // Scans lot0002 x4
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    {
        trigger: '.o_sublines .o_barcode_line.o_highlight:contains("lot0002") .qty-done:contains("4")',
        run: function() {
            const sublines = document.querySelectorAll('.o_sublines [data-barcode=productlot1]');
            helper.assert(sublines.length, 2, "Expect 2 lines for productlot1");
            helper.assertLineQty($(sublines[0]), '4');
            helper.assertLineIsHighlighted($(sublines[0]), false);
            helper.assertLineQty($(sublines[1]), '4');
            helper.assertLineIsHighlighted($(sublines[1]), true);
        }
    },
    // Scan again the same lot0002 x4, it should select and increment the empty line.
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    {
        trigger: '.o_barcode_line.o_highlight:contains("lot0002"):contains("picking_receipt_3") .qty-done:contains("4")',
        run: function() {
            currentViewState.scanMessage = 'scan_product_or_dest';
            checkState(currentViewState);
            const lines =  document.querySelectorAll('.o_barcode_lines > [data-barcode=productlot1]');
            helper.assert(lines.length, 2, "Expect 2 lines for productlot1");
            const $line1 = $(lines[0]);
            const $line2 = $(lines[1]);
            helper.assertLineQty($line1, '8');
            helper.assertLineIsHighlighted($line1, false);
            helper.assert($line1.find('.o_picking_label').text(), 'picking_receipt_2');
            helper.assertLineQty($line2, '4');
            helper.assertLineIsHighlighted($line2, true);
            helper.assert($line2.find('.o_picking_label').text(), 'picking_receipt_3');
        }
    },
    // Selects the subline with the lot0002 and scans it again, it should increment the selected line.
    { trigger: '.o_barcode_line:contains("productlot1") .o_toggle_sublines' },
    { trigger: '.o_sublines:contains("lot0002")' },
    {
        trigger: '.o_sublines .o_selected:contains("lot0002")',
        run: 'scan lot0002'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_highlight:contains("lot0002") .qty-done:contains("5")',
        run: function() {
            const sublines = document.querySelectorAll('.o_sublines [data-barcode=productlot1]');
            helper.assert(sublines.length, 2, "Expect 2 lines for productlot1");
            helper.assertLineQty($(sublines[0]), '4');
            helper.assertLineIsHighlighted($(sublines[0]), false);
            helper.assertLineQty($(sublines[1]), '5');
            helper.assertLineIsHighlighted($(sublines[1]), true);
        }
    },
]);

tour.register('test_barcode_batch_delivery_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 4,
                pager: '1/5',
                pageSummary: 'From WH/Stock/Section 1',
                next: {
                    isEnabled: true,
                    isVisible: true,
                },
                previous: {
                    isEnabled: true,
                    isVisible: true
                },
                scanMessage: 'scan_src',
            });
            checkState(currentViewState);
            const $lineFromPicking1 = helper.getLines({index: 1});
            const $linesFromPicking2 = helper.getLines({from: 2, to: 3});
            const $linesFromPickingSN = helper.getLines({index: 4});
            helper.assertLineBelongTo($lineFromPicking1, 'picking_delivery_1');
            helper.assertLinesBelongTo($linesFromPicking2, 'picking_delivery_2');
            helper.assertLinesBelongTo($linesFromPickingSN, 'picking_delivery_sn');
            helper.assert($linesFromPickingSN.find('.o_line_lot_name').text(), 'sn1');
        },
    },
    // Scan product1 x2, product4 x1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product4'
    },

    // Scan wrong SN.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2'
    },

    {
        trigger: '.o_next_page.btn-primary',
        run: function () {
            currentViewState.next.isHighlighted = true;
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
            const $linesFromPickingSN = helper.getLines({index: 4});
            helper.assert($linesFromPickingSN.find('.o_line_lot_name').text(), 'sn2');
        },
    },

    // Change the location
    {
        trigger: '.o_next_page.btn-primary',
    },
    {
        trigger: '.o_next_page:not(.btn-primary)',
        run: function () {
            currentViewState.pageSummary = 'From WH/Stock/Section 2';
            currentViewState.linesCount = 1;
            currentViewState.next.isHighlighted = false;
            currentViewState.pager = '2/5';
            currentViewState.scanMessage = 'scan_src';
            checkState(currentViewState);
        },
    },

    // Scan product2 x2
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2' // Must complete the existing line.
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2' // Must create a new line with same picking.
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: function () {
            currentViewState.linesCount = 2;
            helper.assert($('.o_barcode_line:nth-child(1) .o_picking_label').text(), 'picking_delivery_1');
            helper.assert($('.o_barcode_line:nth-child(2) .o_picking_label').text(), 'picking_delivery_1');
            currentViewState.next.isHighlighted = true;
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
        },
    },

    // Change the location
    {
        trigger: '.o_next_page.btn-primary',
    },
    {
        trigger: '.o_next_page:not(.btn-primary)',
        run: function () {
            currentViewState.pageSummary = 'From WH/Stock/Section 3';
            currentViewState.linesCount = 2;
            currentViewState.next.isHighlighted = false;
            currentViewState.pager = '3/5';
            currentViewState.scanMessage = 'scan_src';
            checkState(currentViewState);
        },
    },

    // Scan product2 x1, product3 x2
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3'
    },

    {
        trigger: '.o_next_page.btn-primary',
        run: function () {
            currentViewState.next.isHighlighted = true;
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
        },
    },

    // Change the location for shelf 4.
    {
        trigger: '.o_next_page.btn-primary',
    },
    {
        trigger: '.o_next_page:not(.btn-primary)',
        run: function () {
            currentViewState.pageSummary = 'From WH/Stock/Section 4';
            currentViewState.linesCount = 1;
            currentViewState.next.isHighlighted = false;
            currentViewState.pager = '4/5';
            currentViewState.scanMessage = 'scan_src';
            checkState(currentViewState);
        },
    },

    // Scan product4 x1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product4'
    },
    {
        trigger: '.o_next_page.btn-primary',
        run: function () {
            currentViewState.next.isHighlighted = true;
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
        },
    },

    // Change the location (shelf 5 is the last page).
    {
        trigger: '.o_next_page.btn-primary',
    },
    {
        trigger: '.o_validate_page',
        run: function () {
            currentViewState.pageSummary = 'From WH/Stock/Section 5';
            currentViewState.linesCount = 2;
            currentViewState.next.isEnabled = false;
            currentViewState.next.isHighlighted = false;
            currentViewState.next.isVisible = false;
            currentViewState.validate.isEnabled = true;
            currentViewState.validate.isVisible = true;
            currentViewState.pager = '5/5';
            currentViewState.scanMessage = 'scan_src';
            checkState(currentViewState);
        },
    },

    // Scan p5pack01 which is attended.
        {
            trigger: '.o_barcode_client_action',
            run: 'scan p5pack01'
        },
    // Scan p5pack02 which isn't attended.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan p5pack02'
    },

    {
        trigger: '.o_barcode_line:contains("p5pack02")',
        run: function () {
            currentViewState.linesCount = 3;
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
            const $packagedLines = helper.getLines();
            const $line1 = $($packagedLines[0]); // p5pack02, qty 4
            const $line2 = $($packagedLines[1]); // no pack, qty 0/4
            const $line3 = $($packagedLines[2]); // p5pack01, qty 4/4
            helper.assertLineQty($line1, '4');
            helper.assertLineQty($line2, '0');
            helper.assertLineQty($line3, '4');
            helper.assert($line1.find('div[name="package"]:contains("p5pack02")').length, 1);
            helper.assert($line2.find('div[name="package"]:contains("p5pack01 ?")').length, 1);
            helper.assert($line3.find('div[name="package"]:contains("p5pack01")').length, 1);
        },
    },
    {
        trigger: '.o_validate_page',
    },
]);

tour.register('test_batch_create', {test: true}, [
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },

    {
        trigger: '.button_batch_transfer',
    },

    {
        trigger: '.o-kanban-button-new',
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
           const $pickingTypes = $('.o_barcode_picking_type');
           helper.assert($pickingTypes.length, 2, "Should contain Delivery Orders and Receipts");
        },
    },
    // select picking type
    {
        trigger: '.o_barcode_line_title:contains("Delivery Orders")'
    },

    {
        trigger: '.o_confirm:not([disabled])'
    },

    // select 2 delivery orders
    {
        trigger: '.o_barcode_line_title:contains("picking_delivery_1")',
    },

    {
        extra_trigger: '.o_highlight .o_barcode_line_title:contains("picking_delivery_1")',
        trigger: '.o_barcode_line_title:contains("picking_delivery_2")',
    },

    {
        extra_trigger: '.o_highlight .o_barcode_line_title:contains("picking_delivery_2")',
        trigger: '.o_confirm'
    },

    // from here should be the same as test_barcode_batch_delivery_1 => just check that it initially looks the same
    {
        trigger: '.o_picking_label',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 3,
                pager: '1/4',
                pageSummary: 'From WH/Stock/Section 1',
                next: {
                    isEnabled: true,
                    isVisible: true,
                },
                previous: {
                    isEnabled: true,
                    isVisible: true
                },
                scanMessage: 'scan_src',
            });
            checkState(currentViewState);
            const $lineFromPicking1 = helper.getLines({index: 1});
            const $linesFromPicking2 = helper.getLines({from: 2});
            helper.assertLineBelongTo($lineFromPicking1, 'picking_delivery_1');
            helper.assertLinesBelongTo($linesFromPicking2, 'picking_delivery_2');
        },
    },
]);

tour.register('test_put_in_pack_scan_suggested_package', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 3,
                pager: '1/2',
                pageSummary: 'From WH/Stock/Section 1',
                next: {
                    isEnabled: true,
                    isVisible: true,
                },
                previous: {
                    isEnabled: true,
                    isVisible: true
                },
                scanMessage: 'scan_src',
            });
            checkState(currentViewState);
            const $linesFromPicking1 = helper.getLines({index: [1, 3]});
            const $linesFromPicking2 = helper.getLines({index: 2});
            helper.assertLineBelongTo($($linesFromPicking1[0]), 'test_delivery_1');
            helper.assertLineBelongTo($($linesFromPicking1[1]), 'test_delivery_1');
            helper.assertLinesBelongTo($linesFromPicking2, 'test_delivery_2');
        },
    },

    // Scans the delivery 1 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.pack',
    },
    {
        trigger: '.o_barcode_line:contains("test_delivery_1"):contains("PACK")',
        run: function() {
            const product1_package = $('.o_selected div[name="package"]').text().trim();
            const product3_package = $('[data-barcode="product3"] [name="package"]').text().trim();
            helper.assert(product1_package, 'PACK0000001');
            helper.assert(product3_package, 'PACK0000001 ?'); // Display suggested package.
        }
    },
    // Selects product3's line then scans PACK0000001 and product3.
    { trigger: '.o_barcode_line[data-barcode="product3"]' },
    { trigger: '.o_selected[data-barcode="product3"]', run: 'scan PACK0000001' },
    { trigger: '.o_barcode_client_action', run: 'scan product3' },
    {
        trigger: '.o_line_completed[data-barcode="product3"]',
        run: function() {
            const product1_package = $('[data-barcode="product1"] [name="package"]').text().trim();
            const product3_package = $('.o_selected div[name="package"]').text().trim();
            helper.assert(product1_package, 'PACK0000001');
            helper.assert(product3_package, 'PACK0000001'); // Display suggested package.
        }
    },

    // Scans the delivery 2 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.pack',
    },
    {
        trigger: '.o_barcode_line:contains("test_delivery_2"):contains("PACK")',
        run: function() {
            const $lineFromPicking2 = $('.o_barcode_line:contains("test_delivery_2")');
            const product2_package = $lineFromPicking2.find('div[name="package"]').text().trim();
            helper.assert(product2_package, 'PACK0000002');
        }
    },

    // Goes to next page and checks the lines have the right package suggestion.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-CMD.NEXT',
    },
    {
        trigger: '.btn.o_validate_page',
        run: function() {
            const $lineFromPicking1 = $('.o_barcode_line:contains("test_delivery_1")');
            const $lineFromPicking2 = $('.o_barcode_line:contains("test_delivery_2")');
            const package_suggestion1 = $lineFromPicking1.find('div[name="package"]').text().trim();
            const package_suggestion2 = $lineFromPicking2.find('div[name="package"]').text().trim();
            helper.assert(package_suggestion1, 'PACK0000001 ?');
            helper.assert(package_suggestion2, 'PACK0000002 ?');
        }
    },

    // Scans the delivery 1 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK0000001',
    },
    {
        trigger: '.o_barcode_line:contains("test_delivery_1"):contains("PACK0000001"):not(:contains("?"))',
        run: function() {
            const $lineFromPicking1 = $('.o_barcode_line:contains("test_delivery_1")');
            const product1_package = $lineFromPicking1.find('div[name="package"]').text().trim();
            helper.assert(product1_package, 'PACK0000001');
        }
    },

    // Scans the delivery 2 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK0000002',
    },
    {
        trigger: '.o_barcode_line:contains("test_delivery_2"):contains("PACK0000002"):not(:contains("?"))',
        run: function() {
            const $lineFromPicking2 = $('.o_barcode_line:contains("test_delivery_2")');
            const product2_package = $lineFromPicking2.find('div[name="package"]').text().trim();
            helper.assert(product2_package, 'PACK0000002');
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.validate',
    },
    {
        trigger: '.o_notification.bg-success',
    },
]);

});
