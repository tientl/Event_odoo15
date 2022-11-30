from this import d
import odoo
import logging
import json
from odoo.http import request
_logger = logging.getLogger(__name__)
URL = 'https://event-tienlt-final.ims-online.com.vn'


class EventController(odoo.http.Controller):
    @odoo.http.route('/hi', auth='public')
    def hi_handler(self):
        return "Welcome to My API!"

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
                state_user = event.registration_ids.filtered(
                    lambda e: e.partner_id == user).state
                if state_user == 'draft':
                    state = False
                elif state_user == 'open':
                    state = True

                data_event = {
                    'id': event.id,
                    'name': event.name,
                    'date_begin': event.date_begin,
                    'date_end': event.date_end,
                    'company_name': event.organizer_id.name,
                    'is_confirm': state,
                    'address': event.address_id.contact_address_complete,
                    'map_image': self._get_url_image(
                        event._name, event.id, 'map_image'),
                    'event_description': event.event_description,
                    'event_image': self._get_url_image(
                        event._name, event.id, 'event_image'),
                    'schedules': self._get_schedule_event(event),
                    'sponsors': self._get_sponsors_event(event),
                    'registrations': self._get_registrations_event(event),
                    'speakers': self._get_speakers_event(event)
                }
                data_event = self._delete_key_null(data_event)
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

    def _delete_key_null(self, Dictionary):
        Dict_copy = Dictionary.copy()
        for key, value in Dict_copy.items():
            if not value:
                Dictionary.pop(key)
        return Dictionary

    def _get_sponsors_event(self, EventObj):
        Sponsors = []
        if EventObj:
            sponsors = request.env['event.sponsor'].sudo().search([
                ('event_id', '=', EventObj.id),
            ])
            for sponsor in sponsors:
                detail = {
                    'id': sponsor.id,
                    'name': sponsor.name or False,
                    'company': sponsor.partner_id.name or False,
                    'sponsor_type': sponsor.sponsor_type_id.name or False,
                    'slogan': sponsor.subtitle or False,
                    'email': sponsor.email or False,
                    'mobile': sponsor.mobile or False,
                    'url': sponsor.url,
                    'image_url': self._get_url_image(
                        'event.sponsor', sponsor.id, 'image_512'),
                    'function': sponsor.partner_id.function or False
                }
                detail = self._delete_key_null(detail)
                Sponsors.append(detail)
        return Sponsors

    def _get_registrations_event(self, EventObj):
        Registrations = []
        if EventObj:
            for reg in EventObj.registration_ids:
                resgistration = {
                    'id': reg.id,
                    'name': reg.name or False,
                    'mobile': reg.mobile or False,
                    'email': reg.email or False,
                    'image_url': self._get_url_image(
                        'res.partner', reg.partner_id.id, 'image_1920'),
                    'company': reg.partner_id.parent_id.name or False,
                    'ticket': reg.event_ticket_id.name or False,
                    'function': reg.partner_id.function or False
                }
                resgistration = self._delete_key_null(resgistration)
                Registrations.append(resgistration)
        return Registrations

    def _get_speakers_event(self, EventObj):
        Speakers = []
        if EventObj:
            speakers = \
                EventObj.event_schedul_ids.schedule_detail_ids.speaker_id
            for sp in speakers:
                speaker = {
                    'id': sp.id,
                    'name': sp.name or False,
                    'mobile': sp.mobile or False,
                    'email': sp.email or False,
                    'image_url': self._get_url_image(
                        'res.partner', sp.partner_id.id, 'image_1920'),
                    'company': sp.partner_id.parent_id.name or False,
                    'function': sp.partner_id.function or False
                }
                Speakers.append(speaker)
        return Speakers

    def _get_speaker_event_for_schedule(self, DetailSchedule):
        speaker = False
        if DetailSchedule:
            speaker = {
                    'id': DetailSchedule.id,
                    'name': DetailSchedule.name or False,
                    'mobile': DetailSchedule.mobile or False,
                    'email': DetailSchedule.email or False,
                    'image_url': self._get_url_image(
                        'res.partner', DetailSchedule.partner_id.id,
                        'image_1920'),
                    'company':
                    DetailSchedule.partner_id.parent_id.name or False,
                    'function': DetailSchedule.partner_id.function or False
                }
        return speaker

    def _get_url_image(self, model_name, res_id, field):
        Model = request.env[model_name].sudo().browse(res_id)
        image_url = False
        if getattr(Model, field):
            image_url = \
                f'{URL}/web/image?model={model_name}&id={res_id}&field={field}'
        return image_url

    def _get_schedule_event(self, EventObj):
        schedules = []
        if EventObj:
            for schedule in EventObj.event_schedule_ids:
                schedule_details = []
                for det in schedule.schedule_detail_ids:
                    details = {
                        'name': det.name or False,
                        'hour_start': det.hour_start or False,
                        'hour_end': det.hour_end or False,
                        'total_hour': det.total_hour or False,
                        'detail': det.detail or False,
                        'room': det.room_id.name or False,
                        'track': det.event_track_id.name or False,
                        'speaker': self._get_speaker_event_for_schedule(det)
                    }
                    schedule_details.append(details)
                schedule_info = {
                    'name': schedule.name,
                    'time_schedule': schedule.time_schedule,
                    'detail': schedule.detail,
                    'schedule_details': schedule_details or False
                }
                schedule_info = self._delete_key_null(schedule_info)
                schedules.append(schedule_info)
        return schedules

    @odoo.http.route(['/users/search'], type='http', auth="user",
                     sitemap=False, cors='*', csrf=False)
    def get_event(self, **kw):
        if kw['name']:
            domain = [('name', 'ilike', kw['name'])]
            event = request.env['event.event'].sudo().search(domain)
            if event:
                response = {
                    "code": "200",
                    "message": "Get event info Successfuly!",
                    "content": {
                        'id': event.id,
                        "name": event.name
                        }
                }
                return json.dumps(response)
        return "Request params not valid"

    @odoo.http.route(['/users/confirm'], method=['POST'], type='json',
                     auth="public", sitemap=False, cors='*', csrf=False)
    def confirm_event(self):
        data = request.jsonrequest
        event = request.env['event.event'].sudo().browse(data.get('event_id'))
        if event:
            registration = event.registration_ids.filtered(
                lambda r: r.partner_id.id == data.get('user_id'))
            if registration:
                registration.write({'state': 'open'})

                return {
                    'is_confirmed': True,
                    'code': 200,
                    'message': 'Xác nhận thành công'
                }
        return {
            'is_confirmed': False,
            'code': 404,
            'message': 'Xác nhận không thành công'}
