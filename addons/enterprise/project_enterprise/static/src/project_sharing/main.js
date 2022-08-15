/** @odoo-module  **/

import { prepareFavoriteMenuRegister } from '@project/project_sharing/components/favorite_menu_registry';
import { startWebClient } from '@web/start';
import { ProjectSharingWebClientEnterprise } from './project_sharing';
import { removeServices } from './remove_services';

prepareFavoriteMenuRegister();
removeServices();
startWebClient(ProjectSharingWebClientEnterprise);
