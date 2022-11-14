import odoo
import logging
import json
from odoo.http import request
_logger = logging.getLogger(__name__)


class EventController(odoo.http.Controller):
    @odoo.http.route('/hi', auth='public')
    def hi_handler(self):
        return "Welcome to My API!"

    @odoo.http.route('/sg', auth='public')
    def sg_handler(self):
        return json.dumps({
            "code": "200",
            "message": "OK",
            "data": [1, 2, 3, 4, 5, 6]
        })

    @odoo.http.route('/home', auth='public')
    def home_handler(self):
        return request.redirect('web#action=307&model=medical.patient&view_type=list&cids=1&menu_id=178')

    @odoo.http.route(['/users/<dbname>/<id>'], type='http', auth="none",
                     sitemap=False, cors='*', csrf=False)
    def get_one_user_handler(self, dbname, id, **kw):
        model_name = "res.users"
        try:
            registry = odoo.modules.registry.Registry(dbname)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                rec = env[model_name].search([('id', '=', int(id))], limit=1)

                response = {
                    "code": "200",
                    "message": "Get user info successful!",
                    "content": {
                        "employee_name": rec.name,
                        "previous_wage": rec.email,
                        "current_wage": rec.phone}
                }
        except Exception:
            response = {
                "code": "400",
                "message": "User NOT FOUND!"
            }
        return json.dumps(response)

    @odoo.http.route(['/users/all'], type='http', auth="public",
                     sitemap=False, cors='*', csrf=False)
    def get_all_user_handler(self):
        # model_name = "payroll.wage.history"
        all_users = request.env['res.users'].sudo().search([])

        content = []
        for rec in all_users:
            temp = {"name": rec.name,
                    "email": rec.email,
                    "phone": rec.phone,
                    }
            content.append(temp)
        response = {
            "code": "200",
            "message": "Get all users Successfuly!",
            "count": len(content),
            "data": content,
            }
        return json.dumps(response)

    @odoo.http.route(['/users/<id>'], type='http', auth="user",
                     sitemap=False, cors='*', csrf=False)
    def get_one_user_handler_2(self, id):
        domain = [('id', '=', int(id))]
        user = request.env['res.users'].sudo().search(domain)
        response = {
            "code": "200",
            "message": "Get user info Successfuly!",
            "content": {"name": user.name,
                        "email": user.email,
                        "phone": user.phone,
                        }
        }
        return json.dumps(response)

    @odoo.http.route(['/users/'], type='http', auth="user",
                     sitemap=False, cors='*', csrf=False)
    def get_one_user_by_name(self, **kw):
        print(request.session)
        print(request.httprequest.headers.get('cookie'))
        if kw['name']:
            domain = [('name', '=', kw['name'])]
            user = request.env['res.users'].sudo().search(domain)
            response = {
                "code": "200",
                "message": "Get user info Successfuly!",
                "content": {"name": user.name,
                            "email": user.email,
                            "phone": user.phone,
                            }
            }
            return json.dumps(response)
        return "Request params not valid"

    @odoo.http.route(['/users/del/<id>'], type='http', auth="user",
                     sitemap=False, cors='*', csrf=False)
    def del_handler(self, id):
        domain = [('id', '=', int(id))]
        payroll = request.env['payroll.wage.history'].sudo().search(domain)
        payroll.unlink()
        return request.redirect('/web#cids=1&menu_id=246&action=382\
            &model=payroll.wage.history&view_type=list')

    @odoo.http.route('/users/create', type='json', method=['POST'], auth="public", csrf=False)
    def create_user(self, **kw):
        data = request.jsonrequest['data']
        print(data)
        request.env['res.users'].sudo().create([{
            'login': '123',
            'name': 'Sangdg',
        }])
        return {
            "code": "200",
            "message": "Create user Successfuly!",
        }

    @odoo.http.route('/users/edit/<login>', method=['POST'], type='json', auth="public", csrf=False)
    def edit_user(self, login, **kw):
        data = request.jsonrequest['data']
        domain = [('login', '=', login)]
        user = request.env['res.users'].sudo().search(domain)
        user.sudo().write({
            'name': data['name'],
        })
        return "Cập nhật thành công"

    @odoo.http.route(['/users/login'], method=['POST'], type='json',
                     auth="public", sitemap=False, cors='*', csrf=False)
    def get_info_login(self):
        data = request.jsonrequest
        user = request.env['res.partner'].sudo().search([
            ('user_name', '=', data['user_name']),
            ('password', '=', data['password'])])
        if user:
            data_events = []
            events = request.env['event.event'].sudo().search([
                ('registration_ids.partner_id', 'child_of', user.ids)
            ])
            for event in events:
                data_event = {
                    'id': event.id,
                    'name': event.name,
                    'date_begin': event.date_begin,
                    'date_end': event.date_end,
                }
                data_events.append(data_event)
            data_user = {
                'id': user.id,
                'user_name': user.user_name,
                'password': user.password,
                'events': data_events
            }
            response = {
                'data': data_user,
                'code': 200
            }
        else:
            response = {
                'code': 404,
                'message': 'Tài khoản hoặc mật khẩu không đúng'}
        return response
