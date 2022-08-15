/** @odoo-module **/

import config from 'web.config';
import dom from 'web.dom';
import pyUtils from 'web.py_utils';
import FormRenderer from 'web.FormRenderer';
import AttachmentViewer from '@mail_enterprise/js/attachment_viewer';

// ensure `.include()` on `mail` is applied before `mail_enterprise`
import '@mail/widgets/form_renderer/form_renderer';

/**
 * Display attachment preview on side of form view for large screen devices.
 *
 * To use this simply add div with class o_attachment_preview in format
 *     <div class="o_attachment_preview"/>
 *
 * Some options can be passed to change its behavior:
 *     types: ['image', 'pdf']
 *     order: 'asc' or 'desc'
 *
 * For example, if you want to display only pdf type attachment and the latest
 * one then use:
 *     <div class="o_attachment_preview" options="{'types': ['pdf'], 'order': 'desc'}"/>
**/

FormRenderer.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this.$attachmentPreview = undefined;
        this.attachmentPreviewResID = undefined;
        this.attachmentViewer = undefined;
        /**
         * Tracked thread of rendered attachments by attachment viewer.
         *
         * Useful for updating attachment viewer in case the thread linked to
         * the attachments has been changed.
         *
         * Note that attachment viewer only requires attachments, but attachment
         * viewer is not that well designed to update its content solely based
         * on provided list attachments (until rewritten using OWL).
         *
         * In the meantime, it updates its content on change of thread and on
         * change of amount of attachments. This doesn't cover some corner cases
         * (like new list with same length and same thread), but it's good enough
         * for the time being.
         */
        this._attachmentViewerThread = undefined;
        this._isChatterInFormSheetBg = false;
        this._onResizeWindow = _.debounce(this._onResizeWindow.bind(this), 200);
    },
    /**
     * @override
     */
    destroy() {
        window.removeEventListener('resize', this._onResizeWindow);
        this._super();
    },
    /**
     * @override
     */
    start() {
        window.addEventListener('resize',  this._onResizeWindow);
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {boolean}
     */
    _isChatterAside() {
        const parent = this._chatterContainerTarget && this._chatterContainerTarget.parentNode;
        return (
            config.device.size_class >= config.device.SIZES.XXL &&
            !this.attachmentViewer &&
            // We also test the existance of parent.classList. At start of the
            // form_renderer, parent is a DocumentFragment and not the parent of
            // the chatter. DocumentFragment doesn't have a classList property.
            !(parent && parent.classList && parent.classList.contains('o_form_sheet'))
        );
    },
    /**
     * Interchange the position of the chatter and the attachment preview.
     *
     * @private
     * @param {boolean} enablePreview
     */
     _interchangeChatter(enablePreview) {
        if (config.device.size_class < config.device.SIZES.XXL) {
            return;
        }
        if (!this.$attachmentPreview) {
            return;
        }
        const $sheet = this.$('.o_form_sheet_bg');

        this._updateChatterContainerTarget();
        if (enablePreview) {
            this.$attachmentPreview.insertAfter($sheet);
            dom.append($sheet, $(this._chatterContainerTarget), {
                callbacks: [{ widget: this.chatter }],
                in_DOM: this._isInDom,
            });
            this._chatterContainerTarget.classList.add('o-isInFormSheetBg');
            this._isChatterInFormSheetBg = true;
        } else {
            $(this._chatterContainerTarget).insertAfter($sheet);
            dom.append($sheet, this.$attachmentPreview, {
                callbacks: [],
                in_DOM: this._isInDom,
            });
            this._chatterContainerTarget.classList.remove('o-isInFormSheetBg');
            this._isChatterInFormSheetBg = false;
        }
        this._updateChatterContainerComponent();
    },
    /**
     * @override
     */
    _makeChatterContainerProps() {
        const props = this._super(...arguments);
        const isChatterAside = this._isChatterAside();
        return Object.assign(props, {
            hasExternalBorder: !isChatterAside,
            hasMessageListScrollAdjust: isChatterAside,
            isInFormSheetBg: this._isChatterInFormSheetBg,
        });
    },
    /**
     * Add a class to allow styling of chatter depending on the fact is is
     * printed aside or underneath the form sheet.
     *
     * @override
     */
    _makeChatterContainerTarget() {
        const $el = this._super(...arguments);
        this._updateChatterContainerTarget();
        return $el;
    },
    /**
     * Overrides the function that renders the nodes to return the preview's $el
     * for the `o_attachment_preview` div node.
     *
     * @override
     */
    _renderNode: function (node) {
        if (node.tag === 'div' && node.attrs.class === 'o_attachment_preview') {
            if (this.attachmentViewer) {
                if (this.attachmentPreviewResID !== this.state.res_id) {
                    this.attachmentViewer.destroy();
                    this.attachmentViewer = undefined;
                }
            } else {
                this.$attachmentPreview = $('<div>', {class: 'o_attachment_preview'});
            }
            this._handleAttributes(this.$attachmentPreview, node);
            this._registerModifiers(node, this.state, this.$attachmentPreview);
            if (node.attrs.options) {
                this.$attachmentPreview.data(pyUtils.py_eval(node.attrs.options));
            }
            if (this.attachmentPreviewWidth) {
                this.$attachmentPreview.css('width', this.attachmentPreviewWidth);
            }
            return this.$attachmentPreview;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides the function to interchange the chatter and the preview once
     * the chatter is in the dom.
     *
     * @override
     */
    async _renderView() {
        await this._super(...arguments);
        if (!this._hasChatter()) {
            return;
        }
        this._updateChatterContainerTarget();

        // for cached messages, `preview_attachment` will be triggered
        // before the view rendering where the chatter is replaced ; in this
        // case, we need to interchange its position if needed
        const enablePreview = this.attachmentPreviewResID &&
            this.attachmentPreviewResID === this.state.res_id &&
            this.$attachmentPreview &&
            !this.$attachmentPreview.hasClass('o_invisible_modifier');
        this._interchangeChatter(enablePreview);
    },
    /**
     * @private
     */
    _updateChatterContainerTarget() {
        if (this._isChatterAside()) {
            $(this._chatterContainerTarget).addClass('o-aside');
        } else {
            $(this._chatterContainerTarget).removeClass('o-aside');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Triggered from the mail chatter, send attachments data for preview
     *
     * @override
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {mail.attachment[]} ev.data.attachments
     * @param {mail.thread} ev.data.thread
     */
    _onChatterRendered(ev) {
        if (config.device.size_class < config.device.SIZES.XXL) {
            return;
        }
        if (!this.$attachmentPreview || this.$attachmentPreview.hasClass('o_invisible_modifier')) {
            return;
        }
        var self = this;
        var options = _.defaults(this.$attachmentPreview.data(), {
            types: ['pdf', 'image'],
            order: 'asc'
        });
        var attachments = $.extend(true, {}, ev.data.attachments);  // clone array
        attachments = _.filter(attachments, function (attachment) {
            var match = attachment.mimetype.match(options.types.join('|'));
            attachment.update({ type: match ? match[0] : false });
            return match && !attachment.isUploading;
        });
        const thread = ev.data.thread;
        // most recent attachment is first in attachment list, so default order is 'desc'
        if (options.order === 'asc') {
            attachments.reverse();
        }
        if (attachments.length || this.attachmentViewer) {
            if (this.attachmentViewer) {
                // FIXME should be improved : what if somehow an attachment is replaced in a thread ?
                if (
                    this._attachmentViewerThread !== thread ||
                    this.attachmentViewer.attachments.length !== attachments.length
                ) {
                    if (!attachments.length) {
                        this.attachmentViewer.destroy();
                        this.attachmentViewer = undefined;
                        this.attachmentPreviewResID = undefined;
                        this._interchangeChatter(false);
                    }
                    else {
                        this.attachmentViewer.updateContents(attachments, options.order);
                    }
                } else {
                    // The attachmentViewer lose its event listeners when it is reused,
                    // we just need to reregister them.
                    if (this.attachmentViewer.$el) {
                        this.attachmentViewer._undelegateEvents();
                        this.attachmentViewer._delegateEvents();
                    }
                }
                this.trigger_up('preview_attachment_validation');
                this._updateChatterContainerTarget();
            } else {
                this.attachmentPreviewResID = this.state.res_id;
                this.attachmentViewer = new AttachmentViewer(this, attachments);
                this.attachmentViewer.appendTo(this.$attachmentPreview).then(function() {
                    self.trigger_up('preview_attachment_validation');
                    self.$attachmentPreview.resizable({
                        handles: 'w',
                        minWidth: 400,
                        maxWidth: 900,
                        resize: function (event, ui) {
                            self.attachmentPreviewWidth = ui.size.width;
                        },
                    });
                    self._interchangeChatter(true);
                });
            }
        }
        this._attachmentViewerThread = thread;
    },
    /**
     * Reflects the move of chatter (from aside to underneath of form sheet or
     * the other way around) into classes and component props to allow theming
     * to be adapted
     *
     * @private
     * @param {Event} ev
     */
    _onResizeWindow(ev) {
        if (this._chatterContainerComponent) {
            this._updateChatterContainerComponent();
            this._updateChatterContainerTarget();
        }
        this._applyFormSizeClass();
    }

});
