odoo.define('account_followup.FollowupFormRenderer', function (require) {
"use strict";

var core = require('web.core');
var datepicker = require('web.datepicker');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var FormRenderer = require('web.FormRenderer');
var SystrayMenu = require('web.SystrayMenu');

var QWeb = core.qweb;
var _t = core._t;

var FollowupFormRenderer = FormRenderer.extend({
    events: _.extend({}, FormRenderer.prototype.events, {
        'input .o_account_reports_next_action_date_picker input': '_onReminderDate',
        'change *[name="blocked"]': '_onChangeBlocked',
        'click .o_change_expected_date': '_onChangeExpectedDate',
        'click .o_change_trust': '_onChangeTrust',
        'click .o_account_reports_no_print .o_account_reports_summary': '_onEditSummary',
        'click .o_account_reports_no_print .o_account_reports_email_subject': '_onEditEmailSubject',
        'click .js_account_report_save_summary': '_onSaveSummary',
        'click .js_account_report_save_email_subject': '_onSaveEmailSubject',
        'click [action]': '_onTriggerAction',
        'click .o_account_reports_contact_info_call': '_onClickCall',
    }),
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.nextActionDatePicker = new datepicker.DateWidget(this);
        this.nextActionDatePicker.on('datetime_changed', this, function (){
            this.trigger_up('next_action_date_changed', {
                newDate: this.nextActionDatePicker.getValue()
            });
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Remove the mail alert above the report.
     */
    removeMailAlert: function () {
        owl.Component.env.services.messaging.get().then(messaging => {
            const thread = messaging.models['mail.thread'].findFromIdentifyingData({
                id: this.state.res_id,
                model: this.state.model,
            });
            if (thread) {
                thread.refresh();
                thread.refreshActivities();
                thread.refreshFollowers();
            }
        });
        this.$('div.alert.alert-info.alert-dismissible').remove();
    },
    /**
     * Render the summary in 'edit' mode.
     */
    renderEditSummary: function () {
        dom.autoresize(this.$('textarea[name="summary"]'));
        this.$('.o_account_reports_summary_edit').show();
        this.$('.o_account_reports_no_print .o_account_reports_summary').hide();
        this.$('textarea[name="summary"]').focus();
    },
    /**
     * Render the email subject in 'edit' mode.
     */
    renderEditEmailSubject: function () {
        this.$('.o_account_reports_email_subject_edit').show();
        this.$('.o_account_reports_no_print .o_account_reports_email_subject').hide();
        this.$('input[name="email_subject"]').focus();
    },
    /**
     * Render an alert to indicate that an email has been sent.
     */
    renderMailAlert: function () {
        this.$('.o_form_sheet_bg div.o_account_reports_page').prepend(QWeb.render("CustomerStatements.send_mail"));
    },
    /**
     * Render an alert to indicate that an sms has been sent.
     */
    renderSMSAlert: function () {
        this.$('div.o_account_reports_page').prepend(QWeb.render("CustomerStatements.send_sms"));
    },
    /**
     * Render the summary in 'non-edit' mode.
     *
     * @param {string} text Summary content
     */
    renderSavedSummary: function (text) {
        this.$('.o_account_reports_summary_edit').hide();
        this.$('.o_account_reports_no_print .o_account_reports_summary').show();
        var span_content = this.$('.o_account_report_summary_content');
        var span_placeholder = this.$('.o_account_report_summary_placeholder');
        if(text)
        {
            span_placeholder.hide();
            span_content.text(text);
            span_content.html(span_content.html().replace(/\n/g, '<br>'))
            span_content.show();
        }
        else
        {
            span_placeholder.show();
            span_content.hide();
        }
    },
    /**
     * Render the email_subject in 'non-edit' mode.
     *
     * @param {string} text Email Subject content
     */
    renderSavedEmailSubject: function (text) {
        this.$('.o_account_reports_email_subject_edit').hide();
        this.$('.o_account_reports_no_print .o_account_reports_email_subject').show();
        var span_content = this.$('.o_account_report_email_subject_content');
        var span_placeholder = this.$('.o_account_report_email_subject_placeholder');
        if(text)
        {
            span_placeholder.hide();
            span_content.text(text);
            span_content.show();
        }
        else
        {
            span_placeholder.show();
            span_content.hide();
        }
    },
    /**
     * Render the bullet next to the name of customer according to the trust.
     *
     * @param {string} newTrust The new trust to assign to the partner.
     */
    renderTrust: function (newTrust) {
        var colorMap = {
            good: 'green',
            normal: 'grey',
            bad: 'red',

        };
        var color = colorMap[newTrust];
        this.$('i.oe-account_followup-trust').attr('style', 'color: ' + color + '; font-size: 0.8em;');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create JQueryElement which contains the customer statement.
     *
     * @private
     * @returns {jQueryElement} Element rendered
     */
    _renderTagFollowup: function () {
        var self = this;
        var $element = $('<div>');
        $element.html(this.state.data.followup_html);
        $element.find('.o_account_reports_summary_edit').hide();
        $element.find('.o_account_reports_email_subject_edit').hide();
        this.nextActionDatePicker.appendTo($element.find('div.o_account_reports_next_action_date_picker')).then(function() {
            self.nextActionDatePicker.setValue(new moment(self.state.data.next_action_date));
        });

        return $element;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When a move line is blocked or unblocked, trigger an event to the
     * controller to write it in DB and reload the HTML to update the total
     * due and total overdue.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onChangeBlocked: function (event) {
        var checkbox = $(event.target).is(":checked");
        var targetID = $(event.target).parents('tr').find('td[data-id]').data('id');
        this.trigger_up('on_change_block', {
            checkbox: checkbox,
            targetID: targetID
        });
    },
    /**
     * When the user click on 'Change expected date', it opens a dialog
     * to allow the user to choose a new date for an account.move.line.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onChangeExpectedDate: function (event) {
        var self = this;
        var targetID = parseInt($(event.target).attr('data-id'));
        var $content = $(QWeb.render("paymentDateForm", {target_id: targetID}));
        var paymentDatePicker = new datepicker.DateWidget(this);
        paymentDatePicker.appendTo($content.find('div.o_account_reports_payment_date_picker'));
        var save = function () {
            self.trigger_up('expected_date_changed', {
                newDate: paymentDatePicker.getValue(),
                moveLineID: parseInt($content.find("#target_id").val())
            });
        };
        new Dialog(this, {
            title: 'Odoo',
            size: 'medium',
            $content: $content,
            buttons: [{
                text: 'Save',
                classes: 'btn-primary',
                close: true,
                click: save
            },
            {
                text: 'Cancel',
                close: true
            }]
        }).open();
    },
    /**
     * When the trust of a partner is changed, trigger an event to write it in
     * DB.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onChangeTrust: function (event) {
        var newTrust = $(event.target).data("new-trust");
        if (!newTrust) {
            newTrust = $(event.target).parents('a.o_change_trust').data("new-trust");
        }
        this.trigger_up('on_change_trust', {
            newTrust: newTrust
        });
    },
    /**
     * When the user click on phone, trigger an event to make voip call if voip installed.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClickCall: function (ev) {
        ev.preventDefault();
        var $el = $(ev.currentTarget);
        this.trigger_up('voip_call', {
            resModel: $el.data('model'),
            resId: $el.data('id'),
            number: $el.data('number').toString(),
        });
    },
    /**
     * When the user click on the summary, he can edit it.
     *
     * @private
     */
    _onEditSummary: function () {
        this.renderEditSummary();
    },
    /**
     * When the user click on the email_subject, he can edit it.
     *
     * @private
     */
    _onEditEmailSubject: function () {
        this.renderEditEmailSubject();
    },
    /**
     * When changing the reminder date, change it in db
     *
     * @private
     */
    _onReminderDate: function () {
        this.trigger_up('on_change_reminder_date');
    },
    /**
     * When the user save the summary, trigger an event to the controller to
     * save the new summary.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onSaveSummary: function (event) {
        var text = $(event.target).siblings().val().replace(/[ \t]+/g, ' ');
        this.trigger_up('on_save_summary', {
            text: text
        });
    },
    /**
     * When the user save the email_subject, trigger an event to the controller to
     * save the new email_subject.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onSaveEmailSubject: function (event) {
        var text = $(event.target).siblings('input[name="email_subject"]').val().replace(/[ \t]+/g, ' ');
        this.trigger_up('on_save_email_subject', {
            text: text
        });
    },
    /**
     * Trigger an event to the controller to execute an action.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onTriggerAction: function (event) {
        event.stopPropagation();
        var actionName = $(event.target).attr('action');
        var resId = parseInt($(event.target).attr('data-id'));
        var view = parseInt($(event.target).attr('view-id'));
        this.trigger_up('on_trigger_action', {
            actionName: actionName,
            resId: resId,
            view: view
        });
    },
});
return FollowupFormRenderer;
});
