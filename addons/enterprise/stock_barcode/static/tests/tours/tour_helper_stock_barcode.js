odoo.define('stock_barcode.tourHelper', function (require) {
'use strict';

var tour = require('web_tour.tour');

function fail (errorMessage) {
    tour._consume_tour(tour.running_tour, errorMessage);
}

function getLine (description) {
    var $res;
    $('.o_barcode_lines > .o_barcode_line').each(function () {
        var $line = $(this);
        const barcode = $line[0].dataset.barcode.trim();
        if (description.barcode === barcode) {
            if ($res) {
                $res = $res.add($line);
            } else {
                $res = $line;
            }
        }
    });
    if (! $res) {
        fail('cannot get the line with the barcode ' + description.barcode);
    }
    return $res;
}

function triggerKeydown(eventKey, shiftkey=false) {
    document.querySelector('.o_barcode_client_action')
        .dispatchEvent(new window.KeyboardEvent('keydown', { bubbles: true, key: eventKey, shiftKey: shiftkey}));
}

function assert (current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

/**
 * Checks if a button on the given line is visible.
 *
 * @param {jQuerryElement} $line the line where we test the button visibility.
 * @param {string} buttonName could be 'add_quantity' or 'remove_unit'.
 * @param {boolean} [isVisible=true]
 */
function assertButtonIsVisible($line, buttonName, isVisible=true) {
    const $button = $line.find(`.o_${buttonName}`);
    assert($button.length, isVisible ? 1 : 0,
        isVisible ? `Buttons should be in the DOM` : "Button shouldn't be in the DOM");
}

/**
 * Checks if a button on the given line is invisible.
 *
 * @param {jQuerryElement} $line the line where we test the button visibility.
 * @param {string} buttonName could be 'add_quantity' or 'remove_unit'.
 */
function assertButtonIsNotVisible ($line, buttonName) {
    assertButtonIsVisible($line, buttonName, false);
}

/**
 * Checks if both "Add unit" and "Add reserved remaining quantity" buttons are
 * displayed or not on the given line.
 *
 * @param {integer} lineIndex
 * @param {boolean} isVisible
 */
function assertLineButtonsAreVisible(lineIndex, isVisible, cssSelector='.o_line_button') {
    const $buttonAddQty = $(`.o_barcode_line:eq(${lineIndex}) ${cssSelector}`);
    const message = `Buttons must be ${(isVisible ? 'visible' : 'hidden')}`;
    assert($buttonAddQty.length > 0, isVisible, message);
}

function assertPageSummary (expected) {
    // FIXME sle: fix the tests instead of fixing the assert method
    let res = '';
    const $src = $('.o_current_location');
    if ($src.length) {
        res = "From " + $src.text() + " ";
    }
    const $dest = $('.o_current_dest_location');
    if ($dest.length) {
        res += "To " + $dest.text();
    }
    assert(res.trim(), expected.trim(), 'Page summary');
}

function assertPreviousVisible (expected) {
    var $previousButton = $('.o_previous_page');
    var current = (!$previousButton.length && !expected) || $previousButton.hasClass('o_hidden');
    assert(!current, expected, 'Previous visible');
}

function assertPreviousEnabled (expected) {
    var $previousButton = $('.o_previous_page');
    var current = (!$previousButton.length && !expected) || $previousButton.prop('disabled');
    assert(!current, expected, 'Previous button enabled');
}

function assertNextVisible (expected) {
    var $nextButton = $('.o_next_page');
    var current = (!$nextButton.length && !expected) || $nextButton.hasClass('o_hidden');
    assert(!current, expected, 'Next visible');
}

function assertNextEnabled (expected) {
    var $nextButton = $('.o_next_page');
    var current = (!$nextButton.length && !expected) || $nextButton.prop('disabled');
    assert(!current, expected, 'Next button enabled');
}

function assertNextIsHighlighted (expected) {
    var $nextButton = $('.o_next_page');
    var current = $nextButton.hasClass('btn-primary');
    assert(current, expected, 'Next button is highlighted');
}

function assertValidateVisible (expected) {
    var $validate = $('.o_validate_page');
    var current = (!$validate.length && !expected) || $validate.hasClass('o_hidden');
    assert(!current, expected, 'Validate visible');
}

function assertValidateEnabled (expected) {
    var $validate = $('.o_validate_page');
    var current = (!$validate.length && !expected) || $validate.prop('disabled');
    assert(!current, expected, 'Validate enabled');
}

function assertValidateIsHighlighted (expected) {
    var $validate = $('.o_validate_page');
    var current = $validate.hasClass('btn-success');
    assert(current, expected, 'Validate button is highlighted');
}

function assertLinesCount(expected) {
    const current = document.querySelectorAll('.o_barcode_lines > .o_barcode_line').length;
    assert(current, expected, `Should have ${expected} line(s)`);
}

function assertScanMessage (expected) {
    var $helps = $('.o_scan_message');
    var $help = $helps.filter('.o_scan_message_' + expected);
    if (! $help.length || $help.hasClass('o_hidden')) {
        fail('assertScanMessage: "' + expected + '" is not displayed');
    }
}

function assertSublinesCount(expected) {
    const current = document.querySelectorAll('.o_sublines > .o_barcode_line').length;
    assert(current, expected, `Should have ${expected} subline(s), found ${current}`);
}

function assertLocationHighlight (expected) {
    var $locationElem = $('.o_barcode_summary_location_src');
    assert($locationElem.hasClass('o_strong'), expected, 'Location source is not bold');
}

function assertDestinationLocationHighlight (expected) {
    var $locationElem = $('.o_barcode_summary_location_dest');
    assert($locationElem.hasClass('o_strong'), expected, 'Location destination is not bold');
}

function assertPager (expected) {
    var $pager = $('.o_barcode_move_number');
    assert($pager.text(), expected, 'Pager is wrong');
}

function assertLineIsHighlighted ($line, expected) {
    assert($line.hasClass('o_highlight'), expected, 'line should be highlighted');
}

function assertLineQty($line, qty) {
    assert($line[0].querySelector('.qty-done,.inventory_quantity').innerText, qty, 'line quantity is wrong');
}

/**
 * Checks the done quantity on the reserved quantity is what is expected.
 *
 * @param {integer} lineIndex
 * @param {string} textQty quantity on the line, formatted as "n / N"
 */
function assertLineQuantityOnReservedQty (lineIndex, textQty) {
    const $line = $('.o_barcode_line').eq(lineIndex);
    const qty = $line.find('.qty-done').text();
    const reserved = $line.find('.qty-done').next().text();
    assert(qty + ' ' + reserved, textQty, 'Something wrong with the quantities');
}

function assertFormLocationSrc(expected) {
    var $location = $('.o_field_widget[name="location_id"] input');
    assert($location.val(), expected, 'Wrong source location');
}

function assertFormLocationDest(expected) {
    var $location = $('.o_field_widget[name="location_dest_id"] input');
    assert($location.val(), expected, 'Wrong destination location');
}
function assertFormQuantity(expected) {
    var $location = $('.o_field_widget[name="qty_done"]');
    assert($location.val(), expected, 'Wrong destination location');

}

function assertInventoryFormQuantity(expected) {
    var $location = $('.o_field_widget[name="inventory_quantity"]');
    assert($location.val(), expected, 'Wrong quantity');

}

function assertErrorMessage(expected) {
    var $errorMessage = $('.o_notification_content').eq(-1);
    assert($errorMessage[0].innerText, expected, 'wrong or absent error message');
}

function assertQuantsCount(expected) {
    var $quantity = $('.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length;
    assert($quantity, expected, 'Wrong number of cards');
}

function pressShift() {
    document.querySelector('.o_barcode_client_action').dispatchEvent(
        new window.KeyboardEvent(
            'keydown', { bubbles: true, key: 'Shift' },
        )
    );
}

function releaseShift() {
    document.querySelector('.o_barcode_client_action').dispatchEvent(
        new window.KeyboardEvent(
            'keyup', { bubbles: true, key: 'Shift' },
        )
    );
}

return {
    assert: assert,
    assertButtonIsVisible: assertButtonIsVisible,
    assertButtonIsNotVisible: assertButtonIsNotVisible,
    assertLineButtonsAreVisible: assertLineButtonsAreVisible,
    assertDestinationLocationHighlight: assertDestinationLocationHighlight,
    assertErrorMessage: assertErrorMessage,
    assertFormLocationDest: assertFormLocationDest,
    assertFormLocationSrc: assertFormLocationSrc,
    assertFormQuantity: assertFormQuantity,
    assertInventoryFormQuantity: assertInventoryFormQuantity,
    assertLinesCount: assertLinesCount,
    assertLineIsHighlighted: assertLineIsHighlighted,
    assertLineQty: assertLineQty,
    assertLineQuantityOnReservedQty: assertLineQuantityOnReservedQty,
    assertLocationHighlight: assertLocationHighlight,
    assertNextEnabled: assertNextEnabled,
    assertNextIsHighlighted: assertNextIsHighlighted,
    assertNextVisible: assertNextVisible,
    assertPager: assertPager,
    assertPageSummary: assertPageSummary,
    assertPreviousEnabled: assertPreviousEnabled,
    assertPreviousVisible: assertPreviousVisible,
    assertQuantsCount: assertQuantsCount,
    assertScanMessage: assertScanMessage,
    assertSublinesCount,
    assertValidateEnabled: assertValidateEnabled,
    assertValidateIsHighlighted: assertValidateIsHighlighted,
    assertValidateVisible: assertValidateVisible,
    fail: fail,
    getLine: getLine,
    pressShift: pressShift,
    releaseShift: releaseShift,
    triggerKeydown: triggerKeydown,
};

});
