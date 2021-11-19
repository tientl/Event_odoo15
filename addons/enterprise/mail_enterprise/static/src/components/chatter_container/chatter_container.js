/** @odoo-module **/

import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';

Object.assign(ChatterContainer, {
    defaultProps: Object.assign(ChatterContainer.defaultProps || {}, {
        isInFormSheetBg: false,
    }),
    props: Object.assign(ChatterContainer.props, {
        isInFormSheetBg: {
            type: Boolean,
        },
    })
});
