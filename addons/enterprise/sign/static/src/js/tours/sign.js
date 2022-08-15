odoo.define('sign.tour', function(require) {
"use strict";

var core = require('web.core');
const {Markup} = require('web.utils');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('sign_tour', {
    url: "/web",
    rainbowManMessage: "<b>Congratulations</b>, your first document is fully signed!",
    sequence: 150,
},  [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
    content: Markup(_t("Let's <b>prepare & sign</b> our first document.")),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: '.o_nocontent_help p a:contains("' + _t('start with our sample template') + '")',
    content: _t("Try out this sample contract."),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Name') + '")',
    content: Markup(_t("<b>Drag & drop “Name”</b> into the document.")),
    position: "right",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Date') + '")',
    content: Markup(_t("<b>Drag & drop “Date”</b> into the document.")),
    position: "right",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Signature') + '")',
    content: Markup(_t("And finally, <b>drag & drop “Signature”</b> into the bottom of the document.")),
    position: "right",
}, {
    trigger: '.o_control_panel .o_sign_template_sign_now',
    content: Markup(_t("Well done, your document is ready!<br>Let's sign it directly.")),
    position: "bottom",
}, {
    trigger: '.modal-dialog button[name="sign_directly_without_mail"]',
    content: _t("Ok, let’s sign the document now."),
    position: "left",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    content: _t("Go to the first area you have to fill in."),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    alt_trigger: "iframe .o_sign_sign_item[placeholder='" + _t("Date") + "']",
    content: _t("Your name has been auto-completed. Let’s continue!"),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    content: _t("Let’s sign the document!"),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    alt_trigger: 'iframe .o_sign_sign_item[data-signature]',
    content: Markup(_t("Draw your most beautiful signature!<br>You can also create one automatically or load a signature from your computer.")),
    position: "bottom",
}, {
    trigger: '.modal-dialog button:contains("' + _t('Adopt and Sign') + '")',
    content: _t("Confirm and continue."),
    position: "bottom",
}, {
    trigger: '.o_sign_validate_banner button.o_validate_button',
    content: Markup(_t("Great, the document is signed!<br>Let’s validate it.")),
    position: "top",
}, {
    trigger: '.modal-dialog button:contains("' + _t('View Document') + '")',
    content: _t("Let's view the document you have just signed!"),
    position: "bottom",
},
]);

tour.register('sign_tour_with_multiple_signatures', {
    url: "/web",
    rainbowManMessage: "<b>Congratulations</b>, your first document is fully signed!",
    sequence: 150,
},  [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
    content: Markup(_t("Let's <b>prepare & sign</b> our first document.")),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: '.o_nocontent_help p a:contains("' + _t('start with our sample template') + '")',
    content: _t("Try out this sample contract."),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Name') + '")',
    content: Markup(_t("<b>Drag & drop “Name”</b> into the document.")),
    position: "right",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Date') + '")',
    content: Markup(_t("<b>Drag & drop “Date”</b> into the document.")),
    position: "right",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Signature') + '")',
    content: Markup(_t("And finally, <b>drag & drop “Signature”</b> into the bottom of the document.")),
    position: "right",
}, {
    trigger: 'iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' + _t('Signature') + '")',
    content: Markup(_t("Let's add another signature, <b>drag & drop “Signature”</b> into the bottom of the document.")),
    position: "right",
}, {
    trigger: '.o_control_panel .o_sign_template_sign_now',
    content: Markup(_t("Well done, your document is ready!<br>Let's sign it directly.")),
    position: "bottom",
}, {
    trigger: '.modal-dialog button[name="sign_directly_without_mail"]',
    content: _t("Ok, let’s sign the document now."),
    position: "left",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    content: _t("Go to the first area you have to fill in."),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    alt_trigger: "iframe .o_sign_sign_item[placeholder='" + _t("Date") + "']",
    content: _t("Your name has been auto-completed. Let’s continue!"),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    content: _t("Let’s sign the document!"),
    position: "bottom",
}, {
    trigger: 'iframe .o_sign_sign_item_navigator',
    alt_trigger: 'iframe .o_sign_sign_item[data-signature]',
    content: Markup(_t("Draw your most beautiful signature!<br>You can also create one automatically or load a signature from your computer.")),
    position: "bottom",
}, {
    trigger: '.modal-dialog button:contains("' + _t('Sign All') + '")',
    content: _t("Confirm and continue."),
    position: "bottom",
}, {
    trigger: '.o_sign_validate_banner button.o_validate_button',
    content: Markup(_t("Great, the document is signed!<br>Let’s validate it.")),
    position: "top",
}, {
    trigger: '.modal-dialog button:contains("' + _t('View Document') + '")',
    content: _t("Let's view the document you have just signed!"),
    position: "bottom",
},
]);

});
