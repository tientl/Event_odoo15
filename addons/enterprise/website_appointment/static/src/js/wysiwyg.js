/** @odoo-module **/

import Wysiwyg from 'web_editor.wysiwyg'
import dialogs from 'web.view_dialogs'

Wysiwyg.include({
    _getCommands: function () {
        const commands = this._super.apply(this, arguments);
        commands.push(...[
            {
                groupName: 'Basic blocks',
                title: 'Appointment',
                description: 'Add a specific appointment.',
                fontawesome: 'fa-calendar',
                callback: async () => {
                    const dialog = new dialogs.FormViewDialog(this, {
                        res_model: 'calendar.appointment.share',
                        res_id: 0,
                        res_ids: [],
                        res_IDs: [],
                        resIDs: [],
                        context: {
                            form_view_ref: "appointment.calendar_appointment_insert_share_view_form",
                            default_appointment_type_ids: [],
                            default_employee_ids: [],
                        },
                        title: "Insert Appointment Link",
                        readonly: false,
                    });
                    dialog.open();
                    await dialog.opened();
                    const $dialog = $(dialog.el.closest('.modal-dialog'));
                    dialog.on('dialog_form_loaded', this, () => {
                        $dialog.find('.o_share_link_save').on('click', () => {
                            const url = $dialog.find('.o_appointement_share_link').text();
                            dialog.destroy();
                            const link = `<a href="${url}">Schedule an Appointment</a>`;
                            this.focus();
                            this.odooEditor.execCommand('insertHTML', link);
                        });
                        $dialog.find('.o_share_link_discard').on('click', () => {
                            dialog.destroy();
                        });
                    });
                },
            },
            {
                groupName: 'Basic blocks',
                title: 'Calendar',
                description: 'Schedule an appointment.',
                fontawesome: 'fa-calendar',
                callback: () => {
                    const link = `<a href="${window.location.origin}/calendar">Our Appointment Types</a>`;
                    this.odooEditor.execCommand('insertHTML', link);
                },
            },
        ]);
        return commands;
    }
});
