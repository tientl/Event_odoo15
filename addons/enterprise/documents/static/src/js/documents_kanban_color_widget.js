odoo.define('documents.Many2ManyColorWidget', function (require) {
    'use strict';

    const fieldRegistry = require('web.field_registry');

    const { KanbanFieldMany2ManyTags, FieldMany2ManyTags } = require('web.relational_fields');

    const Many2ManyColorMixin = {
        /**
         * @override
         */
        async start() {
            this.tags = [];
            this.trigger_up('get_search_panel_tags', {callback: val => {this.tags = val;}});
            await this._super(...arguments);
        },
        /**
         * @override
         * @private
         */
        _render() {
            // In studio mode searchPanel will not be rendered and we will not have
            // tags here, in that case render standard many2many tags widget for kanban
            if (!this.tags.length) {
                return this._super(...arguments);
            }
            this.$el.empty().addClass('o_field_many2manytags o_kanban_tags');
            const tagIDs = this.value.data.map(m2m => m2m.data.id);
            for (const tag of this.tags) {
                if (tagIDs.includes(tag.id)) {
                    const color = tag.group_hex_color || '#00000022';
                    $('<span>', {
                        class: 'o_tag',
                        text: tag.display_name,
                        title: tag.group_name + ' > ' + tag.name,
                    })
                    .prepend($('<span>', {
                        style: 'color: ' + color + ';',
                        text: '●',
                    }))
                    .appendTo(this.$el);
                }
            }
        },
    };

    const Many2ManyColorWidget = KanbanFieldMany2ManyTags.extend(Many2ManyColorMixin);
    const ListMany2ManyColorWidget = FieldMany2ManyTags.extend(Many2ManyColorMixin);

    fieldRegistry.add('documents_many2many_tags', Many2ManyColorWidget);
    fieldRegistry.add('documents_tree_many2many_tags', ListMany2ManyColorWidget);

});
