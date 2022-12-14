from datetime import datetime
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
            if not user.is_receptionist:
                data_events = []
                events = request.env['event.event'].sudo().search([
                    ('registration_ids.partner_id', 'child_of', user.ids)
                ])
                for event in events:
                    state_user = event.registration_ids.filtered(
                        lambda e: e.partner_id == user).state
                    state = False
                    if state_user != 'draft':
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
                        'sub_schedules': self._get_schedule_event(event),
                        'sponsors': self._get_sponsors_event(event),
                        'registrations': self._get_registrations_event(event),
                        'speakers': self._get_speakers_event(event),
                        'booths': self._get_booths_event(event)
                    }
                    data_event = self._delete_key_null(data_event)
                    data_events.append(data_event)
                data_user = {
                    'id': user.id,
                    'full_name': user.name,
                    'user_name': user.user_name,
                    'password': user.password,
                    'mobile': user.mobile,
                    'email': user.email,
                    'avatar_url': self._get_url_image(
                        user._name, user.id, 'image_1920'),
                    'is_admin': user.is_receptionist,
                    'events': data_events
                }
            else:
                all_event = request.env['event.event'].sudo().search([])
                events = []
                for event in all_event:
                    value = {
                        'id': event.id,
                        'name': event.name,
                        'date_begin': event.date_begin,
                        'date_end': event.date_end,
                        'company_name': event.organizer_id.name,
                        'address': event.address_id.contact_address_complete,
                        'map_image': self._get_url_image(
                            event._name, event.id, 'map_image'),
                        'event_description': event.event_description,
                        'event_image': self._get_url_image(
                            event._name, event.id, 'event_image'),
                        'registrations': self._get_registrations_event(event),
                    }
                    events.append(self._delete_key_null(value))
                data_user = {
                    'is_admin': user.is_receptionist,
                    'events': events
                }
            data_user = self._delete_key_null(data_user)
            response = {
                'data': data_user,
                'code': 200
            }
        else:
            response = {
                'code': 401,
                'message': 'T??i kho???n ho???c m???t kh???u kh??ng ????ng'}
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
                    'function': reg.partner_id.function or False,
                    'is_check_in': reg.date_closed and True or False,
                    'checkin_time': reg.date_closed or False
                }
                resgistration = self._delete_key_null(resgistration)
                Registrations.append(resgistration)
        return Registrations

    def _get_speakers_event(self, EventObj):
        Speakers = []
        if EventObj:
            speakers = \
                EventObj.event_schedule_ids.schedule_detail_ids.speaker_id
            for sp in speakers:
                speaker = {
                    'id': sp.id,
                    'name': sp.name or False,
                    'mobile': sp.mobile or False,
                    'email': sp.email or False,
                    'image_url': self._get_url_image(
                        'res.partner', sp.id, 'image_1920'),
                    'company': sp.parent_id.name or False,
                    'function': sp.function or False
                }
                delete = self._delete_key_null(speaker)
                Speakers.append(delete)
        return Speakers

    def _get_speaker_event_for_schedule(self, DetailSchedule):
        speaker = False
        if DetailSchedule:
            speakerObj = DetailSchedule.speaker_id
            speaker_info = {
                    'id': speakerObj.id or False,
                    'name': speakerObj.name or False,
                    'mobile': speakerObj.mobile or False,
                    'email': speakerObj.email or False,
                    'image_url': self._get_url_image(
                        'res.partner', speakerObj.id,
                        'image_1920'),
                    'company':
                    speakerObj.parent_id.name or False,
                    'function': speakerObj.function or False
                }
            if self._delete_key_null(speaker_info):
                speaker = [self._delete_key_null(speaker_info)]
        return speaker

    def _get_url_image(self, model_name, res_id, field):
        image_url = False
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_id', '=', res_id),
            ('res_model', '=', model_name),
            ('res_field', '=', field)
        ])
        if attachment:
            image_url = \
                f'{URL}/web/image/{attachment.id}?access_token={attachment.access_token}'
        return image_url

    def _get_booths_event(self, EventObj):
        booths = []
        if EventObj:
            for booth in EventObj.event_booth_ids:
                value_booth = {
                    'id': booth.id,
                    'name': booth.contact_name or False,
                    'email': booth.contact_email or False,
                    'img_url': self._get_url_image(
                        booth._name, booth.id, 'image_booth') or False,
                    'company': booth.partner_id.name or False,
                    'level': booth.booth_category_id.name or False,
                    'desc': booth.description or False,
                }
                if self._delete_key_null(value_booth):
                    booths.append(self._delete_key_null(value_booth))
        return booths

    def _get_schedule_event(self, EventObj):
        schedules = []
        if EventObj:
            for schedule in EventObj.event_schedule_ids:
                for det in schedule.schedule_detail_ids:
                    presentation_info = {
                        'name': det.event_track_id.name or False,
                        'description':
                        det.event_track_id.track_description or False,
                        'speaker': self._get_speaker_event_for_schedule(det)
                    }
                    presentation_info = self._delete_key_null(
                        presentation_info)
                    details = {
                        'id': det.id,
                        'name': det.name or False,
                        'time_schedule': schedule.time_schedule or False,
                        'hour_start': self._format_float_to_datetime(
                            det.hour_start, schedule.time_schedule) or False,
                        'hour_end': self._format_float_to_datetime(
                            det.hour_end, schedule.time_schedule) or False,
                        'total_hour': det.total_hour or False,
                        'detail': det.detail or False,
                        'location': det.room_id.name or False,
                        'presentation': presentation_info or False
                    }
                    schedule_info = self._delete_key_null(details)
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
                    'message': 'X??c nh???n th??nh c??ng'
                }
        return {
            'is_confirmed': False,
            'code': 404,
            'message': 'X??c nh???n kh??ng th??nh c??ng'}

    def _format_float_to_datetime(self, float_time, date):
        minutes = float_time * 60
        hours, minutes = divmod(minutes, 60)
        return "%s %02d:%02d:00" % (date, hours, minutes)

    @odoo.http.route(['/users/rating'], method=['POST'], type='json',
                     auth="public", sitemap=False, cors='*', csrf=False)
    def rating_event(self):
        data = request.jsonrequest
        event = request.env['event.event'].sudo().browse(data.get('event_id'))
        if event:
            value = {
                'partner_id': data.get('partner_id', False),
                'event_id': data.get('event_id', False),
                'is_event': data.get('is_event', False),
                'is_schedule': data.get('is_schedule', False),
                'rating': data.get('rating', 0),
                'evaluate': data.get('evaluate', False),
                'schedule_detail_id': data.get('sub_schedule_id', False)
            }
            request.env['event.rating'].sudo().create(value)
            return {'code': 200}
        return {
            'code': 500,
            'message': 'H??? th???ng ??ang x???y ra l???i, vui l??ng th??? l???i sau'}

    @odoo.http.route(['/users/change_password'], method=['POST'], type='json',
                     auth="public", sitemap=False, cors='*', csrf=False)
    def change_password(self):
        data = request.jsonrequest
        user = request.env['res.partner'].sudo().browse(data.get('user_id'))
        new_pass = data.get('new_pass', False)
        if user and new_pass:
            user.write({'password': new_pass})
            return {'code': 200, 'message': '?????i m???t kh???u th??nh c??ng'}
        return {'code': 402, 'message': '?????i m???t kh???u th???t b???i'}

    @odoo.http.route(['/users/scan_qr'], method=['POST'], type='json',
                     auth="public", sitemap=False, cors='*', csrf=False)
    def scan_qr(self):
        data = request.jsonrequest
        event = request.env['event.event'].sudo().search([
            ('id', '=', data.get('event_id'))])
        if event:
            user = event.registration_ids.filtered(
                lambda u: u.partner_id.id == data.get('user_id'))
            if user:
                user.write({'state': 'done', 'date_closed': datetime.now()})
                info = {
                    'full_name': user.partner_id.name,
                    'position': user.partner_id.function,
                    'company': user.partner_id.parent_id.name
                }
                info = self._delete_key_null(info)
                info.update({'code': 200, 'message': 'Qu??t m?? th??nh c??ng'})
                return info
        return {'code': 402,
                'message': 'Qu??t m?? th???t b???i'}
