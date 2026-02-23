import os
import tempfile
import unittest

TEST_DB_FILE = os.path.join(tempfile.gettempdir(), 'criminology_test.sqlite')
os.environ['DATABASE_URL'] = f"sqlite:///{TEST_DB_FILE.replace(os.sep, '/')}"

from app import create_app
from db_init import ensure_master_auth_seed
from extensions import db
from models import MeetingLink
from routes import video_call_routes
from security import _LOGIN_ATTEMPTS


class AuthDevDocsVideoCallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
            ensure_master_auth_seed()

    def setUp(self):
        _LOGIN_ATTEMPTS.clear()
        video_call_routes._VIDEO_ROOMS.clear()
        with self.app.app_context():
            MeetingLink.query.delete()
            db.session.commit()

    def test_master_admin_login_success_and_failure(self):
        ok = self.client.post(
            '/admin-login',
            data={'email': 'chinmaysahoo63715@gmail.com', 'password': 'chin1987'},
            follow_redirects=False,
        )
        self.assertEqual(ok.status_code, 302)
        self.assertIn('/admin-dashboard', ok.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('admin_logged_in'))

        self.client.get('/admin-logout')

        bad = self.client.post(
            '/admin-login',
            data={'email': 'chinmaysahoo63715@gmail.com', 'password': 'wrong'},
            follow_redirects=False,
        )
        self.assertEqual(bad.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertFalse(bool(sess.get('admin_logged_in')))

    def test_master_super_admin_login_success_and_failure(self):
        ok = self.client.post(
            '/super_admin_login',
            data={'email': 'chinmaysahoo63715@gmail.com', 'password': 'chin1987'},
            follow_redirects=False,
        )
        self.assertEqual(ok.status_code, 302)
        self.assertIn('/super-admin-dashboard', ok.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('super_admin_logged_in'))

        self.client.get('/super_admin_logout')

        bad = self.client.post(
            '/super_admin_login',
            data={'email': 'chinmaysahoo63715@gmail.com', 'password': 'wrong'},
            follow_redirects=False,
        )
        self.assertEqual(bad.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertFalse(bool(sess.get('super_admin_logged_in')))

    def test_dev_guide_auth_and_gate(self):
        unauth = self.client.get('/admin/dev-guide', follow_redirects=False)
        self.assertEqual(unauth.status_code, 302)
        self.assertIn('/admin-login', unauth.headers.get('Location', ''))

        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True
            sess['admin_username'] = 'admin'

        self.app.config['ENABLE_DEV_DOCS'] = False
        disabled = self.client.get('/admin/dev-guide')
        self.assertEqual(disabled.status_code, 404)

        self.app.config['ENABLE_DEV_DOCS'] = True
        enabled = self.client.get('/admin/dev-guide')
        self.assertEqual(enabled.status_code, 200)
        self.assertIn(b'Developer Guide', enabled.data)

    def test_video_call_api_smoke(self):
        room_id = 'case-room-test'
        with self.app.app_context():
            db.session.add(
                MeetingLink(
                    case_no='CASE-2026-001',
                    link=f'http://localhost/video-call/{room_id}',
                    status='Ongoing',
                )
            )
            db.session.commit()

        inactive = self.client.post('/api/video-call/inactive-room/join')
        self.assertEqual(inactive.status_code, 404)

        join_one = self.client.post(f'/api/video-call/{room_id}/join')
        self.assertEqual(join_one.status_code, 200)
        one_data = join_one.get_json()
        self.assertTrue(one_data['success'])
        client_one = one_data['client_id']
        self.assertTrue(one_data['is_initiator'])

        join_two = self.client.post(f'/api/video-call/{room_id}/join')
        self.assertEqual(join_two.status_code, 200)
        two_data = join_two.get_json()
        self.assertTrue(two_data['success'])
        client_two = two_data['client_id']
        self.assertFalse(two_data['is_initiator'])

        events_one = self.client.get(
            f'/api/video-call/{room_id}/events?client_id={client_one}&last_event_id=0'
        ).get_json()
        self.assertTrue(any(event['type'] == 'participant_joined' for event in events_one['events']))

        offer_ok = self.client.post(
            f'/api/video-call/{room_id}/signal',
            json={'client_id': client_one, 'type': 'offer', 'payload': {'sdp': 'x', 'type': 'offer'}},
        )
        self.assertEqual(offer_ok.status_code, 200)

        events_two = self.client.get(
            f'/api/video-call/{room_id}/events?client_id={client_two}&last_event_id={two_data["last_event_id"]}'
        ).get_json()
        self.assertTrue(any(event['type'] == 'offer' for event in events_two['events']))

        chat_text_ok = self.client.post(
            f'/api/video-call/{room_id}/signal',
            json={'client_id': client_two, 'type': 'chat_text', 'payload': {'message': 'hello'}},
        )
        self.assertEqual(chat_text_ok.status_code, 200)

        chat_image_ok = self.client.post(
            f'/api/video-call/{room_id}/signal',
            json={'client_id': client_two, 'type': 'chat_image', 'payload': {'image_data': 'data:image/png;base64,iVBORw0KGgo='}},
        )
        self.assertEqual(chat_image_ok.status_code, 200)

        chat_image_bad = self.client.post(
            f'/api/video-call/{room_id}/signal',
            json={'client_id': client_two, 'type': 'chat_image', 'payload': {'image_data': 'bad-image'}},
        )
        self.assertEqual(chat_image_bad.status_code, 400)

        leave_ok = self.client.post(
            f'/api/video-call/{room_id}/leave',
            json={'client_id': client_two},
        )
        self.assertEqual(leave_ok.status_code, 200)

        events_after_leave = self.client.get(
            f'/api/video-call/{room_id}/events?client_id={client_one}&last_event_id={events_one["last_event_id"]}'
        ).get_json()
        self.assertTrue(
            any(event['type'] in {'chat_text', 'chat_image', 'participant_left'} for event in events_after_leave['events'])
        )


if __name__ == '__main__':
    unittest.main()
