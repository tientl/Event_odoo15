odoo.define('sign.views_custo', function(require) {
    'use strict';

    var config = require('web.config');
    var core = require('web.core');
    var KanbanController = require("web.KanbanController");
    var KanbanColumn = require("web.KanbanColumn");
    var KanbanRecord = require("web.KanbanRecord");
    var ListController = require("web.ListController");
    var utils = require('web.utils');
    var session = require('web.session');
    var multiFileUpload = require('sign.multiFileUpload')

    var _t = core._t;

    KanbanController.include(_make_custo("button.o-kanban-button-new"));
    KanbanColumn.include({
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            if (this.modelName === "sign.request") {
                this.draggable = false;
            }
        },
    });
    KanbanRecord.include({
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * On click of kanban open send signature wizard
         * @override
         * @private
         */
        _openRecord: function () {
            var self = this;
            if (this.modelName === 'sign.template' && this.$el.parents('.o_sign_template_kanban').length) {
                // don't allow edit on mobile
                if (config.device.isMobile) {
                    return;
                }
                self._rpc({
                    model: 'sign.template',
                    method: 'go_to_custom_template',
                    args: [self.recordData.id],
                }).then(function(action) {
                    self.do_action(action);
                });
            } else if (this.modelName === 'sign.request' && this.$el.parents('.o_sign_request_kanban').length) {
                this._rpc({
                    model: 'sign.request',
                    method: 'go_to_document',
                    args: [self.recordData.id],
                }).then(function(action) {
                    self.do_action(action);
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
        async _render() {
            await this._super(...arguments);
            if (config.device.isMobile &&
                (this.modelName === "sign.template" || this.modelName === "sign.request")) {
                // LPE to APP: data-mobile feature has been deprecated and removed
                // the dialog feature in mobile should be rethought with something like https://material.io/components/sheets-bottom
                this.$('.o_kanban_record_bottom .oe_kanban_bottom_left button:not(.o_kanban_sign_directly)')
                    .attr('data-mobile', '{"fullscreen": true}');
            }
        }
    });

    ListController.include(_make_custo(".o_list_button_add"));

    function _make_custo(selector_button) {
        return {
            renderButtons: function () {
                this._super.apply(this, arguments);
                if (!this.$buttons) {
                    return; // lists in modal don't have buttons
                }
                if (this.modelName === "sign.template") {
                    this._sign_upload_file_button();

                } else if (this.modelName === "sign.request") {
                    if (this.$buttons) {
                        this._sign_create_request_button();
                    }
                }
            },

            _sign_upload_file_button: function () {
                var self = this;
                this.$buttons.find(selector_button).text(_t('UPLOAD A PDF TO SIGN')).off("click").on("click", function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    _sign_upload_file.call(self, true, false, 'sign_send_request');
                });
                // don't allow template creation on mobile devices
                if (config.device.isMobile) {
                    this.$buttons.find(selector_button).hide();
                    return;
                }

                session.user_has_group('sign.group_sign_user').then(function (has_group) {
                    if (has_group) {
                        self.$buttons.find(selector_button).after(
                            $('<button class="btn btn-link o-kanban-button-new ml8" type="button">'+ _t('UPLOAD A PDF TEMPLATE') +'</button>').off('click')
                              .on('click', function (e) {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  _sign_upload_file.call(self, false, false, 'sign_template_edit');
                              }));
                    }
                });
            },

            _sign_create_request_button: function () {
                var self = this;
                this.$buttons.find(selector_button).text(_t('UPLOAD A PDF TO SIGN')).off("click").on("click", function (e) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    _sign_upload_file.call(self, true, false, 'sign_send_request');
                });
                if (config.device.isMobile) {
                    this.$buttons.find(selector_button).hide();
                    return;
                }
            },
        };
    }

    function _sign_upload_file(inactive, sign_directly_without_mail, sign_edit_context) {
        var self = this;
        var sign_directly_without_mail =  sign_directly_without_mail || false;
        var $upload_input = $('<input type="file" name="files[]" accept="application/pdf, application/x-pdf, application/vnd.cups-pdf" multiple="true"/>');
        $upload_input.on('change', function (e) {
            let files = e.target.files;
            Promise.all(
                Array.from(files).map((file) => {
                    return utils.getDataURLFromFile(file).then((result) => {
                        const args = [file.name, result, !inactive]

                        return self._rpc({
                            model: 'sign.template',
                            method: 'upload_template',
                            args: args,
                        });
                    });
                })
            ).then(uploadedTemplateData => {
                let templates = uploadedTemplateData.map((template, index) => {
                    return {
                        template: template.template,
                        name: files[index].name
                    }
                })
                const file = templates.shift();
                if(templates.length) {
                    multiFileUpload.addNewFiles(templates);
                }

                self.do_action({
                    type: "ir.actions.client",
                    tag: 'sign.Template',
                    name: _.str.sprintf(_t('Template "%s"'), file.name),
                    context: {
                        sign_edit_call: sign_edit_context,
                        id: file.template,
                        sign_directly_without_mail: sign_directly_without_mail,
                    }
                });
            }).then(() => {
                $upload_input.removeAttr('disabled');
                $upload_input.val("");
            });
        });

        $upload_input.click();
    }

});

odoo.define('sign.template', function(require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var config = require('web.config');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var PDFIframe = require('sign.PDFIframe');
    var sign_utils = require('sign.utils');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var FormFieldMany2ManyTags = require('web.relational_fields').FormFieldMany2ManyTags;
    const SmoothScrollOnDrag = require('web/static/src/js/core/smooth_scroll_on_drag.js');
    var FormFieldSelection = require('web.relational_fields').FieldSelection;
    var multiFileUpload = require('sign.multiFileUpload')

    var _t = core._t;

    PDFIframe.include({
        enableSignTemplateEdition: async function () {
            const self = this;
            self._rpc({
                model: 'sign.request',
                method: 'check_request_edit_during_sign',
                args: [self.getParent().requestID],
            }).then(function(allowEdit) {
                if (!allowEdit) {
                    return;
                }
                self.$('.page').off('click').on('click', function (e) {
                    if(e.ctrlKey) {
                        self.handleControlClick(e)
                    }
                })
            })
        },
        handleControlClick: function (e) {
            const self = this;
            const editModeDropdown = $(core.qweb.render('sign.edit_mode_dropdown'))
            const $pageElement = $(e.currentTarget)

            $pageElement.find('.o_edit_mode_dropdown').remove()
            const targetPage = $pageElement.attr('data-page-number')
            const $dropdown = $(editModeDropdown).appendTo($pageElement).css({
                top: e.pageY - $pageElement.offset().top,
                left: e.pageX - $pageElement.offset().left
            })

            $dropdown.find('.dropdown_close_icon').on('click', function (e) {
                $dropdown.remove();
            })

            $dropdown.find('.o_edit_mode_dropdown_item').on('click', function (e) {
                function getSignItemSize (type) {
                    const signatureWidth = 0.15;
                    const defaultWidth = 0.1;
                    const defaultHeight = 0.05
                    return type === 'signature' || type === 'text' ? [signatureWidth, defaultHeight] : [defaultWidth, defaultHeight]
                }
                const posX = ($(e.target).offset().left - $pageElement.find('.textLayer').offset().left) / $pageElement.innerWidth();
                const posY = ($(e.target).offset().top - $pageElement.find('.textLayer').offset().top) / $pageElement.innerHeight();
                const type = $(e.target).attr('type');
                const [width, height] = getSignItemSize(self.types[type].item_type);
                const signItem = self.createSignItem(self.types[type], true, self.role, posX, posY, width, height, '', [], '', '', '', true);

                const defineOrder = (pageElements) => {
                    return pageElements.length ? pageElements.slice(-1)[0].data('order') + 1 : 1
                };

                signItem.data({
                    'data-page-number': targetPage,
                    posx: posX,
                    posy: posY,
                    'isEditMode': true,
                    itemId: Math.min(...Object.keys(self.signatureItems), 0) - 1,
                    order: defineOrder(self.configuration[targetPage])
                });
                self.signatureItems[signItem.data('item-id')] = signItem.data()

                self.configuration[targetPage].push(signItem);
                self.updateSignItem(signItem);
                self.refreshSignItems();

                signItem.prop('field-type', self.types[signItem.data('type')].item_type);
                signItem.prop('field-name', self.types[signItem.data('type')].name);
                const smoothScrollOptions = {
                    scrollBoundaries: {
                        right: false,
                        left: false
                    },
                    jQueryDraggableOptions: {
                        containment: "parent",
                        distance: 0,
                        handle: ".o_sign_config_handle",
                        scroll: false,
                    }
                };
                self.signItemsDraggableComponent = new SmoothScrollOnDrag(self, signItem, self.$('#viewerContainer'), smoothScrollOptions);
                signItem.resizable({
                    containment: "parent"
                }).css('position', 'absolute');
    
                signItem.off('dragstart resizestart').on('dragstart resizestart', function(e, ui) {
                    if(!e.ctrlKey) {
                        self.$('.o_sign_sign_item').removeClass('ui-selected');
                    }
                    signItem.addClass('ui-selected');
                });
    
                signItem.off('dragstop').on('dragstop', function(e, ui) {
                    signItem.data({
                        posx: Math.round((ui.position.left / signItem.parent().innerWidth())*1000)/1000,
                        posy: Math.round((ui.position.top / signItem.parent().innerHeight())*1000)/1000,
                    });
                    signItem.removeClass('ui-selected');
                });
    
                signItem.off('resizestop').on('resizestop', function(e, ui) {
                    signItem.data({
                        width: Math.round(ui.size.width / signItem.parent().innerWidth() * 1000) / 1000,
                        height: Math.round(ui.size.height / signItem.parent().innerHeight() * 1000) / 1000,
                    });

                    self.updateSignItem(signItem);
                    signItem.removeClass('ui-selected');
                });

                signItem.find('.o_sign_config_area .fa-times').on('click', () => {
                    delete self.signatureItems[signItem.data('item-id')];
                    self.deleteSignItem(signItem);
                    self.checkSignItemsCompletion();
                });
                $dropdown.remove();
                self.checkSignItemsCompletion();
            })
        }
    })

    var SignItemCustomPopover = Widget.extend({
        template: 'sign.sign_item_custom_popover',
        events: {
            'click .o_sign_delete_field_button': function(e) {
                this.$currentTarget.popover("hide");
                this.$currentTarget.trigger('itemDelete');
            },
            'click .o_sign_align_button': function (e) {
                this.$('.o_sign_field_align_group .o_sign_align_button').removeClass("btn-primary");
                e.target.classList.add("btn-primary");
            },
            'click .o_sign_validate_field_button': function (e) {
                this.hide();
            }
        },

        init: function(parent, parties, options, select_options) {
            options = options || {};
            this._super(parent, options);
            //TODO: Add buttons for save, discard and remove.
            this.parties = parties;
            this.select_options = select_options;
            this.debug = config.isDebug();

        },

        start: function() {
            this.$responsibleSelect = this.$('.o_sign_responsible_select');
            this.$optionsSelect = this.$('.o_sign_options_select');
            sign_utils.resetResponsibleSelectConfiguration();
            sign_utils.resetOptionsSelectConfiguration();

            var self = this;
            return this._super().then(function() {
                const fieldType = self.$currentTarget.prop('field-type');
                if (['text', 'textarea'].includes(fieldType)) {
                    self.$('.o_sign_field_align_group button[data-align="'+ self.$currentTarget.data('alignment') +'"]').addClass("btn-primary");
                } else {
                    self.$('.o_sign_field_align_group').hide();
                }
                sign_utils.setAsResponsibleSelect(self.$responsibleSelect.find('select'), self.$currentTarget.data('responsible'), self.parties);
                sign_utils.setAsOptionsSelect(self.$optionsSelect.find('input'), self.$currentTarget.data('itemId'), self.$currentTarget.data('option_ids'), self.select_options);
                self.$('input[type="checkbox"]').prop('checked', self.$currentTarget.data('required'));

                self.$('#o_sign_name').val(self.$currentTarget.data('name') || "");
                self.title = self.$currentTarget.prop('field-name');
                if (fieldType !== 'selection') {
                    self.$('.o_sign_options_group').hide();
                }
            });
        },

        create: function($targetEl) {
            var self = this;
            this.$currentTarget = $targetEl;
            this.$elPopover = $("<div class='o_sign_item_popover'/>");
            var buttonClose = '<button class="o_sign_close_button">&times;</button>';
            var isRTL = _t.database.parameters.direction === "rtl";

            this.appendTo(this.$elPopover).then(function() {
                var options = {
                    title: self.title + buttonClose,
                    content: function () {
                        return self.$el;
                    },
                    html: true,
                    placement: isRTL ? 'left': 'right',
                    trigger:'focus',
                    container: '.o_sign_template',
                };
                self.$currentTarget.popover(options).one('inserted.bs.popover', function (e) {
                    $('.popover').addClass('o_popover_offset');
                    $('.o_sign_close_button').on('click', function (e) {
                        self.$currentTarget.popover("hide");
                    });
                });
                self.$currentTarget.popover("toggle");
                //  Don't display placeholders of checkboxes: empty element
                if (self.$currentTarget.prop('field-type') === 'checkbox') {
                    $('.o_popover_placeholder').text('');
                }
            });
        },
        hide: function() {
            var self = this;
            var resp = parseInt(this.$responsibleSelect.find('select').val());
            var selected_options = this.$optionsSelect.find('#o_sign_options_select_input').data('item_options');
            var required = this.$('input[type="checkbox"]').prop('checked');
            const alignment = this.$('.o_sign_field_align_group .o_sign_align_button.btn-primary').data('align');
            var name = this.$('#o_sign_name').val();
            this.getParent().currentRole = resp;
            if (! name) {
                name = self.$currentTarget.prop('field-name');
            }
            if (self.$currentTarget.prop('field-type') != "checkbox") {
                this.$currentTarget.find(".o_placeholder").text(name);
            }
            this.$currentTarget.data({responsible: resp, alignment: alignment, required: required, name: name, option_ids: selected_options}).trigger('itemChange');
            this.$currentTarget.popover("hide");
        }
    });

    var InitialAllPagesDialog = Dialog.extend({
        template: 'sign.initial_all_pages_dialog',

        init: function(parent, parties, options) {
            options = options || {};

            options.title = options.title || _t("Add Initials");
            options.size = options.size || "medium";

            if(!options.buttons) {
                options.buttons = [];
                options.buttons.push({text: _t('Add once'), classes: 'btn-primary', close: true, click: function(e) {
                    this.updateTargetResponsible();
                    this.$currentTarget.trigger('itemChange');
                }});
                options.buttons.push({text: _t('Add to all pages'), classes: 'btn-secondary', close: true, click: function(e) {
                    this.updateTargetResponsible();
                    this.$currentTarget.draggable('destroy').resizable('destroy');
                    this.$currentTarget.trigger('itemClone');
                }});
            }

            this._super(parent, options);

            this.parties = parties;
        },

        start: function() {
            this.$responsibleSelect = this.$('.o_sign_responsible_select_initials');

            var self = this;
            return this._super.apply(this, arguments).then(function() {
                sign_utils.setAsResponsibleSelect(self.$responsibleSelect.find('select'), self.getParent().currentRole, self.parties);
            });
        },

        open: function($signatureItem) {
            this.$currentTarget = $signatureItem;
            this._super.apply(this, arguments);
        },

        updateTargetResponsible: function() {
            var resp = parseInt(this.$responsibleSelect.find('select').val());
            this.getParent().currentRole = resp;
            this.$currentTarget.data('responsible', resp);
        },
    });

    var EditablePDFIframe = PDFIframe.extend({
        init: function() {
            this._super.apply(this, arguments);
            if (this.editMode) {
                document.body.classList.add('o_block_scroll');
            }
            this.customPopovers = {};
            this.events = _.extend(this.events || {}, {
                'itemChange .o_sign_sign_item': function (e) {
                    this.updateSignItem($(e.target));
                    this.$iframe.trigger('templateChange');
                },

                'itemDelete .o_sign_sign_item': function (e) {
                    this.deleteSignItem($(e.target));
                    this.$iframe.trigger('templateChange');
                },

                'itemClone .o_sign_sign_item': function (e) {
                    var $target = $(e.target);
                    this.updateSignItem($target);

                    page_loop:
                    for (var i = 1; i <= this.nbPages; i++) {
                        for (var j = 0; j < this.configuration[i].length; j++) {
                            // Add initials only if there is no Signature on the page.
                            if (this.types[this.configuration[i][j].data('type')].item_type === 'signature') {
                                continue page_loop;
                            }
                        }

                        var $newElem = $target.clone(true);
                        this.enableCustom($newElem);
                        this.configuration[i].push($newElem);
                    }

                    this.deleteSignItem($target);
                    this.refreshSignItems();
                    this.$iframe.trigger('templateChange');
                },
            });
        },

        destroy: function() {
            this._super(...arguments);
            if (this.editMode) {
                document.body.classList.remove('o_block_scroll');
            }
        },

        doPDFPostLoad: function() {
            var self = this;
            this.fullyLoaded.then(function() {
                if(self.editMode) {
                    if(self.$iframe.prop('disabled')) {
                        var $div = $('<div/>').css({
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "100%",
                            height: "100%",
                            'z-index': 110,
                            opacity: 0.75
                        });
                        self.$('#viewer').css('position', 'relative').prepend($div);
                        $div.on('click mousedown mouseup mouveover mouseout', function(e) {
                            return false;
                        });
                    } else {
                        // In the edit mode, a side bar will be added to the left of the pdfviewer
                        // "margin-left:14rem" will be added to the pdfviewer to leave space for the sidebar
                        // So, a "resize" must be triggered for the pdfviewer after its new css is added.
                        // If not, when a pdf is opened with "page-width" there might be a horizontal scrollbar on the bottom of the pdfviewer
                        // Unfortunately, it is hard to know when the css will be added.
                        // So we manually add the css here and trigger the "resize"
                        // css in iframe.css:
                        // #outerContainer.o_sign_field_type_toolbar_visible {
                        //     margin-left: 14rem;
                        //     width: auto;
                        // }
                        self.$('#outerContainer').css('width', 'auto');
                        self.$('#outerContainer').css('margin-left', '14rem');
                        self.$iframe.get(0).contentWindow.dispatchEvent(new Event('resize'));

                        var rotateText = _t("Rotate Clockwise");
                        var rotateButton = $("<button id='rotateCw' class='toolbarButton o_sign_rotate rotateCw' title='" + rotateText + "'/>");
                        rotateButton.insertBefore(self.$('#print'));
                        rotateButton.on('click', function(e) {
                            rotateButton.prepend('<i class="fa fa-spin fa-circle-o-notch"/>');
                            rotateButton.attr('disabled', true);
                            self._rotateDocument();
                        });
                        self.$hBarTop = $('<div/>');
                        self.$hBarBottom = $('<div/>');
                        self.$hBarTop.add(self.$hBarBottom).css({
                            position: 'fixed',
                            "border-top": "1px dashed orange",
                            width: "100%",
                            height: 0,
                            "z-index": 103,
                            left: 0
                        });
                        self.$vBarLeft = $('<div/>');
                        self.$vBarRight = $('<div/>');
                        self.$vBarLeft.add(self.$vBarRight).css({
                            position: 'fixed',
                            "border-left": "1px dashed orange",
                            width: 0,
                            height: "100%",
                            "z-index": 103,
                            top: 0
                        });

                        var typesArr = _.toArray(self.types);
                        var $fieldTypeButtons = $(core.qweb.render('sign.type_buttons', {sign_item_types: typesArr}));
                        self.$fieldTypeToolbar = $('<div/>').addClass('o_sign_field_type_toolbar d-flex flex-column');
                        self.$fieldTypeToolbar.prependTo(self.$('body'));
                        self.$('#outerContainer').addClass('o_sign_field_type_toolbar_visible');
                        const smoothScrollOptions = {
                            scrollBoundaries: {
                                right: false,
                                left: false
                            },
                            jQueryDraggableOptions: {
                                cancel: false,
                                distance: 0,
                                cursorAt: {top:5, left:5},
                                helper: function(e) {
                                    var type = self.types[$(this).data('item-type-id')];
                                    var $signatureItem = self.createSignItem(type, true, self.currentRole, 0, 0, type.default_width, type.default_height, '', []);
                                    if(!e.ctrlKey) {
                                        self.$('.o_sign_sign_item').removeClass('ui-selected');
                                    }
                                    $signatureItem.addClass('o_sign_sign_item_to_add ui-selected');

                                    self.$('.page').first().append($signatureItem);
                                    self.updateSignItem($signatureItem);
                                    $signatureItem.css('width', $signatureItem.css('width')).css('height', $signatureItem.css('height')); // Convert % to px
                                    self.updateSignItemFontSize($signatureItem, self.normalSize());
                                    $signatureItem.detach();

                                    return $signatureItem;
                                }
                            }
                        };
                        $fieldTypeButtons.appendTo(self.$fieldTypeToolbar)
                        var $fieldTypeButtonItems = $fieldTypeButtons.children('.o_sign_field_type_button')
                        self.buttonsDraggableComponent = new SmoothScrollOnDrag(this, $fieldTypeButtonItems, self.$('#viewerContainer'), smoothScrollOptions);
                        $fieldTypeButtonItems.each(function(i, el) {
                            self.enableCustomBar($(el));
                        });

                        self.$('.page').droppable({
                            accept: '*',
                            tolerance: 'touch',
                            drop: function(e, ui) {
                                // the 'o_sign_sign_item_to_add' is added once a sign item is dragged.
                                // two consecutive pages have overlaps borders,
                                // we remove the o_sign_sign_item_to_add once the sign item is dropped
                                // to make sure ths sign item will not be dropped into multiple pages
                                if(!ui.helper.hasClass('o_sign_sign_item_to_add')) {
                                    return true;
                                }
                                ui.helper.removeClass('o_sign_sign_item_to_add');

                                const $parent = $(e.target);
                                const pageNo = parseInt($parent.data('page-number'));

                                let $signatureItem;
                                if (ui.draggable.hasClass('o_sign_sign_item')){
                                    let pageNoOri = parseInt($(ui.draggable).parent().attr('data-page-number'));
                                    if (pageNoOri === pageNo){ // if sign_item is dragged to its previous page
                                        return true;
                                    }
                                    $signatureItem = $(ui.draggable);
                                    self.detachSignItem($signatureItem);
                                }
                                else{
                                    $signatureItem = ui.helper.clone(true).removeClass().addClass('o_sign_sign_item o_sign_sign_item_required');
                                }
                                var posX = (ui.offset.left - $parent.find('.textLayer').offset().left) / $parent.innerWidth();
                                var posY = (ui.offset.top - $parent.find('.textLayer').offset().top) / $parent.innerHeight();
                                $signatureItem.data({posx: posX, posy: posY});

                                self.configuration[pageNo].push($signatureItem);
                                self.refreshSignItems();
                                self.enableCustom($signatureItem);

                                // updateSignItem and trigger('templateChange') are done in "dragstop" for sign_items
                                // trigger('tempateChange)' twice may cause 'concurrent update' for server
                                if(!ui.draggable.hasClass('o_sign_sign_item')) {
                                    self.updateSignItem($signatureItem);
                                    self.$iframe.trigger('templateChange');

                                    if (self.types[$signatureItem.data('type')].item_type === 'initial'){
                                         (new InitialAllPagesDialog(self, self.parties)).open($signatureItem);
                                    }
                                }

                                return false;
                            }
                        });

                        self.$('#viewer').selectable({
                            appendTo: self.$('body'),
                            filter: '.o_sign_sign_item',
                        });

                        $(document).add(self.$el).on('keyup', function(e) {
                            if(e.which !== 46) {
                                return true;
                            }

                            self.$('.ui-selected').each(function(i, el) {
                                self.deleteSignItem($(el));
                                // delete the associated popovers. At this point, there should only be one popover
                                var popovers = window.document.querySelectorAll('[id^="popover"]');
                                for (let i = 0; i < popovers.length; i += 1) {
                                     document.getElementById(popovers[i].id).remove();
                                }
                            });
                            self.$iframe.trigger('templateChange');
                        });
                    }

                    self.$('.o_sign_sign_item').each(function(i, el) {
                        self.enableCustom($(el));
                    });
                }
            });

            this._super.apply(this, arguments);
        },

        enableCustom: function($signatureItem) {
            var self = this;

            $signatureItem.prop('field-type', this.types[$signatureItem.data('type')].item_type);
            $signatureItem.prop('field-name', this.types[$signatureItem.data('type')].name);
            var itemId = $signatureItem.data('itemId');
            var $configArea = $signatureItem.find('.o_sign_config_area');
            $configArea.find('.o_sign_item_display').off('mousedown').on('mousedown', function(e) {
                e.stopPropagation();
                self.$('.ui-selected').removeClass('ui-selected');
                $signatureItem.addClass('ui-selected');

                _.each(_.keys(self.customPopovers), function(keyId) {
                    if (keyId != itemId && self.customPopovers[keyId] && ((keyId && itemId) || (keyId != 'undefined' && !itemId))) {
                        self.customPopovers[keyId].$currentTarget.popover('hide');
                        self.customPopovers[keyId] = false;
                    }
                });
                if (self.customPopovers[itemId]) {
                    self._closePopover(itemId);
                } else {
                    self.customPopovers[itemId] = new SignItemCustomPopover(self, self.parties, {'field_name': $signatureItem[0]['field-name'], 'field_type': $signatureItem[0]['field-type']}, self.select_options);
                    self.customPopovers[itemId].create($signatureItem);
                }
            });

            $configArea.find('.o_sign_config_handle').off('mouseup').on('mouseup', function(e) {
                if(!e.ctrlKey) {
                    self.$('.o_sign_sign_item').filter(function(i) {
                        return (this !== $signatureItem[0]);
                    }).removeClass('ui-selected');
                }
                $signatureItem.toggleClass('ui-selected');
            });
            const smoothScrollOptions = {
                scrollBoundaries: {
                    right: false,
                    left: false
                },
                jQueryDraggableOptions: {
                    containment: $('#viewerContainer'),
                    distance: 0,
                    classes: {"ui-draggable-dragging": "o_sign_sign_item_to_add"},
                    handle: ".o_sign_config_handle",
                    scroll: false,
                }
            };
            if (!$signatureItem.hasClass("ui-draggable")){
                this.signItemsDraggableComponent = new SmoothScrollOnDrag(this, $signatureItem, self.$('#viewerContainer'), smoothScrollOptions);
            }
            if (!$signatureItem.hasClass("ui-resizable")){
                    $signatureItem.resizable({
                    containment: "parent"
                }).css('position', 'absolute');
            }

            $signatureItem.off('dragstart resizestart').on('dragstart resizestart', function(e, ui) {
                if(!e.ctrlKey) {
                    self.$('.o_sign_sign_item').removeClass('ui-selected');
                }
                $signatureItem.addClass('ui-selected');
            });

            $signatureItem.off('dragstop').on('dragstop', function(e, ui) {
                const $parent = $(e.target).parent();
                $signatureItem.data({
                    posx: Math.round((ui.offset.left - $parent.find('.textLayer').offset().left) / $parent.innerWidth()*1000)/1000,
                    posy: Math.round(((ui.offset.top - $parent.find('.textLayer').offset().top) / $parent.innerHeight())*1000)/1000,
                });
            });

            $signatureItem.off('resizestop').on('resizestop', function(e, ui) {
                $signatureItem.data({
                    width: Math.round(ui.size.width/$signatureItem.parent().innerWidth()*1000)/1000,
                    height: Math.round(ui.size.height/$signatureItem.parent().innerHeight()*1000)/1000,
                });
            });

            $signatureItem.on('dragstop resizestop', function(e, ui) {
                self.updateSignItem($signatureItem);
                self.$iframe.trigger('templateChange');
                $signatureItem.removeClass('ui-selected');
            });

            this.enableCustomBar($signatureItem);
        },

        enableCustomBar: function($item) {
            var self = this;

            const itemId = $item.data('itemId');
            $item.on('dragstart resizestart', function(e, ui) {
                var $target = $(e.target);
                if (!$target.hasClass('ui-draggable') && !$target.hasClass('ui-resizable')) {
                    // The element itself is not draggable or resizable
                    // Let the event propagate to its parents
                    return;
                }
                if(self.customPopovers[itemId]) {
                    self._closePopover(itemId);
                }
                start.call(self, ui.helper);
            });
            $item.find('.o_sign_config_area .o_sign_config_handle').on('mousedown', function(e) {
                if(self.customPopovers[itemId]) {
                    self._closePopover(itemId);
                }
                start.call(self, $item);
                process.call(self, $item);
            });
            $item.on('drag resize', function(e, ui) {
                var $target = $(e.target);
                if (!$target.hasClass('ui-draggable') && !$target.hasClass('ui-resizable')) {
                    // The element itself is not draggable or resizable
                    // Let the event propagate to its parents
                    return;
                }
                process.call(self, ui.helper);
            });
            $item.on('dragstop resizestop', function(e, ui) {
                end.call(self);
            });
            $item.find('.o_sign_config_area .o_sign_config_handle').on('mouseup', function(e) {
                end.call(self);
            });

            function start($helper) {
                this.$hBarTop.detach().insertAfter($helper).show();
                this.$hBarBottom.detach().insertAfter($helper).show();
                this.$vBarLeft.detach().insertAfter($helper).show();
                this.$vBarRight.detach().insertAfter($helper).show();
            }
            function process($helper) {
                const helperBoundingClientRect = $helper.get(0).getBoundingClientRect();
                this.$hBarTop.css('top', helperBoundingClientRect.top);
                this.$hBarBottom.css(
                    'top',
                    helperBoundingClientRect.top + parseFloat($helper.css('height')) - 1
                );
                this.$vBarLeft.css('left', helperBoundingClientRect.left);
                this.$vBarRight.css(
                    'left',
                    helperBoundingClientRect.left + parseFloat($helper.css('width')) - 1
                );
            }
            function end() {
                this.$hBarTop.hide();
                this.$hBarBottom.hide();
                this.$vBarLeft.hide();
                this.$vBarRight.hide();
            }
        },

        _closePopover(itemId) {
            this.customPopovers[itemId].$currentTarget.popover('hide');
            this.customPopovers[itemId] = false;
        },

        updateSignItem: function($signatureItem) {
            this._super.apply(this, arguments);

            if(this.editMode) {
                var responsibleName = this.parties[$signatureItem.data('responsible')].name;
                const colorIndex = this.parties[$signatureItem.data('responsible')].color;
                const currentColor = $signatureItem.attr('class').match(/o_color_responsible_\d+/);
                $signatureItem.removeClass((currentColor && currentColor[0]));
                $signatureItem.addClass("o_color_responsible_" + colorIndex);
                $signatureItem.find('.o_sign_responsible_display').text(responsibleName).prop('title', responsibleName);
                var option_ids = $signatureItem.data('option_ids') || [];
                var $options_display = $signatureItem.find('.o_sign_select_options_display');
                this.display_select_options($options_display, this.select_options, option_ids);
            }
        },

        _rotateDocument: function () {
            var self = this;
            this._rpc({
                model: 'sign.template',
                method: 'rotate_pdf',
                args: [this.getParent().templateID],
            })
            .then(function (response) {
                if (response) {
                    self.$('#pageRotateCw').click();
                    self.$('#rotateCw').text('');
                    self.$('#rotateCw').attr('disabled', false);
                    self.refreshSignItems();
                } else {
                    Dialog.alert(self, _t('Somebody is already filling a document which uses this template'), {
                        confirm_callback: function () {
                            self.getParent().go_back_to_kanban();
                        },
                    });
                }
            });
        },
    });

    var Template = AbstractAction.extend(StandaloneFieldManagerMixin, {
        hasControlPanel: true,
        events: {
            'click .fa-pencil': function(e) {
                this.$templateNameInput.focus().select();
            },

            'input .o_sign_template_name_input': function(e) {
                this.$templateNameInput.attr('size', this.$templateNameInput.val().length + 1);
            },

            'change .o_sign_template_name_input': function(e) {
                this.saveTemplate();
                if(this.$templateNameInput.val() === "") {
                    this.$templateNameInput.val(this.initialTemplateName);
                }
            },

            'keydown .o_sign_template_name_input': function (e) {
                if (e.keyCode === 13) {
                    this.$templateNameInput.blur();
                }
            },

            'templateChange iframe.o_sign_pdf_iframe': function(e) {
                this.saveTemplate();
            },

            'click .o_sign_template_send' : function (e) {
                this.do_action('sign.action_sign_send_request', {
                    additional_context: {
                        'active_id': this.templateID,
                        'sign_directly_without_mail': false,
                    },
                });
            },

            'click .o_sign_template_sign_now' : function (e) {
                this.do_action('sign.action_sign_send_request', {
                    additional_context: {
                        'active_id': this.templateID,
                        'sign_directly_without_mail': true,
                    },
                });
            },

            'click .o_sign_template_share' : function (e) {
                this.do_action('sign.action_sign_template_share', {
                    additional_context: {
                        active_id: this.templateID,
                    },
                });
            },

            'click .o_sign_template_save' : function (e) {
                return this.do_action('sign.sign_template_action', {
                    clear_breadcrumbs: true
                });
            },

            'click .o_sign_template_next' : function (e) {
                const templateName = e.target.getAttribute('template-name');
                const templateId = parseInt(e.target.getAttribute('template-id'));
                multiFileUpload.removeFile(templateId);
                this.do_action({
                    type: "ir.actions.client",
                    tag: 'sign.Template',
                    name: _.str.sprintf(_t('Template "%s"'), templateName),
                    context: {
                        sign_edit_call: 'sign_template_edit',
                        id: templateId,
                        sign_directly_without_mail: false,
                    }
                });
            },

            'click .o_sign_template_duplicate' : function (e) {
                this.saveTemplate(true);
            },

        },
        custom_events: Object.assign({}, StandaloneFieldManagerMixin.custom_events, {
            field_changed: '_onFieldChanged',
        }),


        go_back_to_kanban: function() {
            return this.do_action("sign.sign_template_action", {
                clear_breadcrumbs: true,
            });
        },

        init: function(parent, options) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);

            if (options.context.id === undefined) {
                return;
            }

            this.templateID = options.context.id;
            this.actionType = options.context.sign_edit_call ? options.context.sign_edit_call : '';
            this.rolesToChoose = {};

            const nextTemplate = multiFileUpload.getNext();
            this.nextTemplate = nextTemplate ? nextTemplate : false;

        },

        renderButtons: function () {
            this.$buttons = $(core.qweb.render("sign.template_cp_buttons", {'widget':this, 'action_type':this.actionType}));
        },

        willStart: function() {
            if(this.templateID === undefined) {
                return this._super.apply(this, arguments);
            }
            return Promise.all([this._super(), this.perform_rpc()]);
        },

        createTemplateTagsField: function () {
            var self = this;
            var params = {
                modelName: 'sign.template',
                res_id: self.templateID,
                fields : {
                    id: {
                        type: 'integer',
                    },
                    name: {
                        type: 'char',
                    },
                    tag_ids: {
                        relation: 'sign.template.tag',
                        type: 'many2many',
                        relatedFields: {
                                id : {
                                    type: 'integer',
                                },
                                display_name : {
                                    type: 'char',
                                },
                                color : {
                                    type: 'integer',
                                }
                        },
                        fields: {
                            id: {
                                type: 'integer',
                            },
                            display_name: {
                                type: 'char',
                            },
                            color: {
                                type: 'integer',
                            }
                        },
                    },
                    group_ids: {
                        relation: 'res.groups',
                        type: 'many2many',
                        relatedFields: {
                            id : {
                                type: 'integer',
                            },
                            display_name : {
                                type: 'char',
                            },
                            color : {
                                type: 'integer',
                            }
                        },
                        fields: {
                            id: {
                                type: 'integer',
                            },
                            display_name: {
                                type: 'char',
                            },
                            color: {
                                type: 'integer',
                            }
                        },
                    },
                    privacy: {
                        type: 'selection',
                        selection: [['employee', _t('All Users')], ['invite', _t('On Invitation')]]
                    }
                },
                fieldsInfo : {
                    default : {
                        id : {
                            type: 'integer',
                        },
                        name : {
                            type: 'char',
                        },
                        tag_ids : {
                            relatedFields: {
                                    id : {
                                        type: 'integer',
                                    },
                                    display_name : {
                                        type: 'char',
                                    },
                                    color : {
                                        type: 'integer',
                                    }
                            },
                            fieldsInfo : {
                                default : {
                                    id : {
                                        type: 'integer',
                                    },
                                    display_name : {
                                        type: 'char',
                                    },
                                    color : {
                                        type: 'integer',
                                    }
                                }
                            },
                            viewType: 'default'
                        },
                        group_ids: {
                            relatedFields: {
                                id : {
                                    type: 'integer',
                                },
                                display_name : {
                                    type: 'char',
                                },
                                color : {
                                    type: 'integer',
                                }
                            },
                            fieldsInfo : {
                                default : {
                                    id : {
                                        type: 'integer',
                                    },
                                    display_name : {
                                        type: 'char',
                                    },
                                    color : {
                                        type: 'integer',
                                    }
                                }
                            },
                            viewType: 'default'
                        },
                        privacy : {
                            relatedFields: {
                                id : {
                                    type: 'selection',
                                },
                                display_name : {
                                    type: 'char',
                                }
                            },
                            fieldsInfo : {
                                default : {
                                    id : {
                                        type: 'selection',
                                    },
                                    display_name : {
                                        type: 'char',
                                    }
                                }
                            },
                            viewType: 'default'
                        }
                    },
                },
            };

            return this.model.load(params).then(function (recordId) {
                self.handleRecordId = recordId;
                self.record = self.model.get(self.handleRecordId);

                self.tag_idsMany2Many = new FormFieldMany2ManyTags(self, 'tag_ids', self.record, {mode: 'edit', create: true, attrs: {options:{color_field: 'color'}}});
                self._registerWidget(self.handleRecordId, 'tag_ids', self.tag_idsMany2Many);
                self.tag_idsMany2Many.appendTo(self.$('.o_sign_template_tags'));

                if (config.isDebug()) {
                    self.privacy = new FormFieldSelection(self, 'privacy', self.record, {mode: 'edit'});
                    self._registerWidget(self.handleRecordId, 'privacy', self.privacy);
                    self.privacy.appendTo(self.$('.o_sign_template_privacy'));

                    self.group_idsMany2many = new FormFieldMany2ManyTags(self, 'group_ids', self.record, {mode: 'edit', create: false, attrs: {options:{color_field: 'color'}}});
                    self._registerWidget(self.handleRecordId, 'group_ids', self.group_idsMany2many);
                    self.group_idsMany2many.appendTo(self.$('.o_sign_template_group_id'));
                }
            });
        },

        _onFieldChanged: function (event) {
            var self = this;
            var $majInfo = this.$(event.target.$el).parent().next('.o_sign_template_saved_info');
            StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
            this.model.save(this.handleRecordId, {reload:true}).then(function (fieldNames) {
                self.record = self.model.get(self.handleRecordId);
                self.tag_idsMany2Many.reset(self.record);
                $majInfo.stop().css('opacity', 1).animate({'opacity': 0}, 1500);
            });
        },

        perform_rpc: function() {
            var self = this;

            var defTemplates = this._rpc({
                    model: 'sign.template',
                    method: 'read',
                    args: [[this.templateID]],
                })
                .then(function prepare_template(template) {
                    if (template.length === 0) {
                        self.templateID = undefined;
                        self.displayNotification({ title: _t("Warning"), message: _t("The template doesn't exist anymore.") });
                        return Promise.resolve();
                    }
                    template = template[0];
                    self.sign_template = template;
                    var defHasSignRequests = self._rpc({
                        model: 'sign.template',
                        method: 'has_sign_requests',
                        args: [[template.id],],
                        kwargs: {context: session.user_context},
                        })
                        .then(function (has_sign_requests){
                            self.has_sign_requests = has_sign_requests;
                        });

                    var defSignItems = self._rpc({
                            model: 'sign.item',
                            method: 'search_read',
                            args: [[['template_id', '=', template.id]]],
                            kwargs: {context: session.user_context},
                        })
                        .then(function (sign_items) {
                            self.sign_items = sign_items;
                            return self._rpc({
                                model: 'sign.item.option',
                                method: 'search_read',
                                args: [[],['id', 'value']],
                                kwargs: {context: session.user_context},
                            });
                        });
                    var defIrAttachments = self._rpc({
                            model: 'ir.attachment',
                            method: 'read',
                            args: [[template.attachment_id[0]], ['mimetype', 'name']],
                            kwargs: {context: session.user_context},
                        })
                        .then(function(attachment) {
                            attachment = attachment[0];
                            self.sign_template.attachment_id = attachment;
                            self.isPDF = (attachment.mimetype.indexOf('pdf') > -1);
                        });

                    return Promise.all([defSignItems, defIrAttachments, defHasSignRequests]);
                });

            var defSelectOptions = this._rpc({
                    model: 'sign.item.option',
                    method: 'search_read',
                    args: [[]],
                    kwargs: {context: session.user_context},
                })
                .then(function (options) {
                    self.sign_item_options = options;
                });

            var defParties = this._rpc({
                    model: 'sign.item.role',
                    method: 'search_read',
                    kwargs: {context: session.user_context},
                })
                .then(function(parties) {
                    self.sign_item_parties = parties;
                });

            var defItemTypes = this._rpc({
                    model: 'sign.item.type',
                    method: 'search_read',
                    kwargs: {context: session.user_context},
                })
                .then(function(types) {
                    self.sign_item_types = types;
                });

            return Promise.all([defTemplates, defParties, defItemTypes, defSelectOptions]);
        },

        start: function() {
            var self = this;
            if(this.templateID === undefined) {
                return this.go_back_to_kanban();
            }
            return this._super().then(function () {
                self.renderButtons();
                var status = {
                    cp_content: {$buttons: self.$buttons},
                };
                return self.updateControlPanel(status);
            }).then(function () {
                self.initialize_content();


                self.createTemplateTagsField();
                if(self.$('iframe').length) {
                    core.bus.on('DOM_updated', self, init_iframe);
                }

                self.$('.o_content').addClass('o_sign_template');

            });
            function init_iframe() {
                if(this.$el.parents('html').length && !this.$el.parents('html').find('.modal-dialog').length) {
                    var self = this;
                    framework.blockUI({overlayCSS: {opacity: 0}, blockMsgClass: 'o_hidden'});
                    this.iframeWidget = new EditablePDFIframe(this,
                                                              '/web/content/' + this.sign_template.attachment_id.id,
                                                              true,
                                                              {
                                                                  parties: this.sign_item_parties,
                                                                  types: this.sign_item_types,
                                                                  signatureItems: this.sign_items,
                                                                  select_options: this.sign_item_options,
                                                              });
                    return this.iframeWidget.attachTo(this.$('iframe')).then(function() {
                        framework.unblockUI();
                        self.iframeWidget.currentRole = self.sign_item_parties[0].id;
                    });
                }
            }
        },

        initialize_content: function() {
            this.$('.o_content').empty();
            this.debug = config.isDebug();
            this.$('.o_content').append(core.qweb.render('sign.template', {widget: this}));

            this.$('iframe,.o_sign_template_name_input').prop('disabled', this.has_sign_requests);

            this.$templateNameInput = this.$('.o_sign_template_name_input').first();
            this.$templateNameInput.trigger('input');
            this.initialTemplateName = this.$templateNameInput.val();
        },

        do_show: function() {
            this._super();

            // the iframe cannot be detached normally
            // we have to reload it entirely and re-apply the sign items on it
            var self = this;
            return this.perform_rpc().then(function() {
                if(self.iframeWidget) {
                    self.iframeWidget.destroy();
                    self.iframeWidget = undefined;
                }
                self.$('iframe').remove();
                self.initialize_content();
            });
        },

        prepareTemplateData: function() {
            this.rolesToChoose = {};
            var data = {}, newId = 0;
            var configuration = (this.iframeWidget)? this.iframeWidget.configuration : {};
            for(var page in configuration) {
                for(var i = 0 ; i < configuration[page].length ; i++) {
                    var id = configuration[page][i].data('item-id') || (newId--);
                    var resp = configuration[page][i].data('responsible');
                    data[id] = {
                        'type_id': configuration[page][i].data('type'),
                        'required': configuration[page][i].data('required'),
                        'name': configuration[page][i].data('name'),
                        'alignment': configuration[page][i].data('alignment'),
                        'option_ids': configuration[page][i].data('option_ids'),
                        'responsible_id': resp,
                        'page': page,
                        'posX': configuration[page][i].data('posx'),
                        'posY': configuration[page][i].data('posy'),
                        'width': configuration[page][i].data('width'),
                        'height': configuration[page][i].data('height'),
                    };

                    this.rolesToChoose[resp] = this.iframeWidget.parties[resp];
                }
            }
            return data;
        },

        saveTemplate: function(duplicate) {
            duplicate = (duplicate === undefined)? false : duplicate;

            var data = this.prepareTemplateData();
            var $majInfo = this.$('.o_sign_template_saved_info').first();

            var self = this;
            this._rpc({
                    model: 'sign.template',
                    method: 'update_from_pdfviewer',
                    args: [this.templateID, !!duplicate, data, this.$templateNameInput.val() || this.initialTemplateName],
                })
                .then(function(templateID) {
                    if(!templateID) {
                        Dialog.alert(self, _t('Somebody is already filling a document which uses this template'), {
                            confirm_callback: function() {
                                self.go_back_to_kanban();
                            },
                        });
                    }

                    if(duplicate) {
                        self.do_action({
                            type: "ir.actions.client",
                            tag: 'sign.Template',
                            name: _t("Duplicated Template"),
                            context: {
                                id: templateID,
                            },
                        });
                    } else {
                        $majInfo.stop().css('opacity', 1).animate({'opacity': 0}, 1500);
                    }
                });
        },
    });

    core.action_registry.add('sign.Template', Template);
});

odoo.define('sign.DocumentBackend', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var Document = require('sign.Document');
    var framework = require('web.framework');

    var _t = core._t;

    var DocumentBackend = AbstractAction.extend({
        hasControlPanel: true,

        destroy: function () {
            core.bus.off('DOM_updated', this, this._init_page);
            return this._super.apply(this, arguments);
        },
        go_back_to_kanban: function () {
            return this.do_action("sign.sign_request_action", {
                clear_breadcrumbs: true,
            });
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            var context = action.context;
            if(context.id === undefined) {
                return;
            }

            this.documentID = context.id;
            this.token = context.token;
            this.create_uid = context.create_uid;
            this.state = context.state;
            this.requestStates = context.request_item_states;

            this.current_name = context.current_signor_name;
            this.token_list = context.token_list;
            this.name_list = context.name_list;
            this.cp_content = {};
        },
        /**
         * Callback to react to DOM_updated events. Loads the iframe and its contents
         * just after it is really in the DOM.
         *
         * @private
         * @returns {Promise|undefined}
         */
        _init_page: function () {
            var self = this;
            if(this.$el.parents('html').length) {
                return this.refresh_cp().then(function () {
                    framework.blockUI({overlayCSS: {opacity: 0}, blockMsgClass: 'o_hidden'});
                    if (!self.documentPage) {
                        self.documentPage = new (self.get_document_class())(self);
                        return self.documentPage.attachTo(self.$el);
                    } else {
                        return self.documentPage.initialize_iframe();
                    }
                }).then(function () {
                    framework.unblockUI();
                });
            }
        },
        start: function () {
            var self = this;
            if(this.documentID === undefined) {
                return this.go_back_to_kanban();
            }
            var def = this._rpc({
                route: '/sign/get_document/' + this.documentID + '/' + this.token,
                params: {message: this.message}
            }).then(function(html) {

                var $html = $(html.trim());
                var $signDocumentButton = $html.find('.o_sign_sign_document_button').detach();

                self.$('.o_content').append($html);
                self.$('.o_content').addClass('o_sign_document');

                var $cols = self.$('.col-lg-4');
                var $buttonsContainer = $cols.first().remove();
                $cols.eq(1).toggleClass( 'col-lg-3 col-lg-4');
                $cols.eq(1).find('.o_sign_request_from').removeClass('d-flex justify-content-center flex-wrap');
                $cols.eq(2).toggleClass( 'col-lg-9 col-lg-4');

                var url = $buttonsContainer.find('.o_sign_download_document_button').attr('href');
                var logUrl = $buttonsContainer.find('.o_sign_download_log_button').attr('href');
                self.$buttons = (self.cp_content && self.cp_content.$buttons && self.cp_content.$buttons.length) ? self.cp_content.$buttons : $('');
                if (url) {
                    self.$downloadButton = $('<a/>', {html: _t("Download Document")}).addClass('btn btn-primary mr-2');
                    self.$downloadButton.attr('href', url);
                    self.$buttons = self.$buttons.add(self.$downloadButton);
                }
                if (logUrl) {
                    self.$downloadLogButton = $('<a/>', {html: _t("Certificate")}).addClass(url ? 'btn btn-secondary' : 'btn btn-primary');
                    self.$downloadLogButton.attr('href', logUrl);
                    self.$buttons = self.$buttons.add(self.$downloadLogButton);
                }
                if ($signDocumentButton)
                    self.$buttons = $signDocumentButton.add(self.$buttons);

                if (self.$buttons.length){
                    self.cp_content = {$buttons: self.$buttons};
                }
                core.bus.on('DOM_updated', self, self._init_page);
            });
            return Promise.all([this._super(), def]);
        },

        get_document_class: function () {
            return Document;
        },

        refresh_cp: function () {
            return this.updateControlPanel({
                cp_content: this.cp_content,
            });
        },
    });

    return DocumentBackend;
});

odoo.define('sign.document_edition', function(require) {
    'use strict';

    var core = require('web.core');
    var session = require('web.session');
    var DocumentBackend = require('sign.DocumentBackend');
    var multiFileUpload = require('sign.multiFileUpload');

    var _t = core._t;

    var EditableDocumentBackend = DocumentBackend.extend({
        events: {
            'click .o_sign_resend_access_button': function(e) {
                var $envelope = $(e.target);
                this._rpc({
                        model: 'sign.request.item',
                        method: 'resend_access',
                        args: [parseInt($envelope.parent('.o_sign_signer_status').data('id'))],
                        context: session.user_context,
                    })
                    .then(function() { $envelope.html(_t("Resent !")); });
            },
        },

        init: function(parent, action, options) {
            this._super.apply(this, arguments);

            var self = this;

            this.is_author = (this.create_uid === session.uid);
            this.is_sent = (this.state === 'sent');

            if (action && action.context && action.context.sign_token) {
                var $signButton = $('<button/>', {html: _t("Sign Document"), type: "button", 'class': 'btn btn-primary mr-2'});
                $signButton.on('click', function () {
                    self.do_action({
                        type: "ir.actions.client",
                        tag: 'sign.SignableDocument',
                        name: _t('Sign'),
                    }, {
                        additional_context: _.extend({}, action.context, {
                            token: action.context.sign_token,
                        }),
                    });
                });
                if (this.cp_content) {
                    this.cp_content.$buttons = $signButton.add(this.cp_content.$buttons);
                }
            }
        },

        start: function() {
            var self = this;
            const nextTemplate = multiFileUpload.getNext();

            if (nextTemplate && nextTemplate.template) {
                let nextDocumentButton = $('<button/>', {html: _t("Next Document"), type: "button", 'class': 'btn btn-primary mr-2'});
                nextDocumentButton.on('click', function () {
                    multiFileUpload.removeFile(nextTemplate.template);
                    self.do_action({
                        type: "ir.actions.client",
                        tag: 'sign.Template',
                        name: _.str.sprintf(_t('Template "%s"'), nextTemplate.name),
                        context: {
                            sign_edit_call: 'sign_send_request',
                            id: nextTemplate.template,
                            sign_directly_without_mail: false,
                        }
                    }, {clear_breadcrumbs: true});
                });
                if (self.cp_content) {
                    self.cp_content.$buttons = nextDocumentButton.add(self.cp_content.$buttons);
                }
            }

            return this._super.apply(this, arguments).then(function () {
                if(self.is_author && self.is_sent) {
                    self.$('.o_sign_signer_status').not('.o_sign_signer_signed').each(function(i, el) {
                        $(el).append($('<button/>', {
                            type: 'button',
                            title: (self.requestStates && self.requestStates[this.dataset.id]) ? _t("Resend the invitation"): _t("Send the invitation"),
                            text: (self.requestStates && self.requestStates[this.dataset.id]) ? _t("Resend"): _t("Send"),
                            class: 'o_sign_resend_access_button btn btn-link ml-2 mr-2',
                            style: 'vertical-align: baseline;',
                        }));
                    });
                }
            });
        },
    });

    core.action_registry.add('sign.Document', EditableDocumentBackend);
});

odoo.define('sign.document_signing_backend', function(require) {
    'use strict';

    var core = require('web.core');
    var DocumentBackend = require('sign.DocumentBackend');
    var document_signing = require('sign.document_signing');
    const config = require('web.config');

    var _t = core._t;
    const qweb = core.qweb;

    var NoPubThankYouDialog = document_signing.ThankYouDialog.extend({
        template: "sign.no_pub_thank_you_dialog",
        init: function (parent, RedirectURL, RedirectURLText, requestID, options) {
            options = (options || {});
            if (!options.buttons) {
                options.buttons = [{text: _t("Ok"), close: true}];
            }
            this._super(parent, RedirectURL, RedirectURLText, requestID, options);
        },

        on_closed: function () {
            var self = this;
            self._rpc({
                model: 'sign.request',
                method: 'go_to_document',
                args: [self.requestID],
            }).then(function(action) {
                self.do_action(action);
                self.destroy();
            });
        },
    });

    var SignableDocument2 = document_signing.SignableDocument.extend({
        get_thankyoudialog_class: function () {
            return NoPubThankYouDialog;
        },
    });

    var SignableDocumentBackend = DocumentBackend.extend({
        get_document_class: function () {
            return SignableDocument2;
        },
        async start () {
            const [_, allowEdit] = await Promise.all([
                this._super(),
                this._rpc({
                    model: 'sign.request',
                    method: 'check_request_edit_during_sign',
                    args: [this.documentID],
                })
            ])
            if(allowEdit && !config.device.isMobile) {
                this.$buttons.push($(qweb.render('sign.edit_mode_info'))[0]);
                this.updateControlPanel({cp_content: {$buttons: this.$buttons}});
            }
        }
    });

    core.action_registry.add('sign.SignableDocument', SignableDocumentBackend);
});
