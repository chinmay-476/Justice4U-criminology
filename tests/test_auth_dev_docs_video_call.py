import os
import tempfile
import unittest
from datetime import date

TEST_DB_FILE = os.path.join(tempfile.gettempdir(), 'criminology_test.sqlite')
os.environ['DATABASE_URL'] = f"sqlite:///{TEST_DB_FILE.replace(os.sep, '/')}"

from app import create_app
from db_init import ensure_master_auth_seed
from extensions import db
from models import Accused, ComplaintDescription, JudgeDecision, MeetingLink
from routes import video_call_routes
from security import _LOGIN_ATTEMPTS


class AuthDevDocsVideoCallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app.config['VIDEO_SIGNALING_INTERNAL_TOKEN'] = 'test-internal-token'
        cls.app.config['VIDEO_TURN_URLS'] = ['turn:turn.example.com:3478']
        cls.app.config['VIDEO_TURN_USERNAME'] = 'turn-user'
        cls.app.config['VIDEO_TURN_CREDENTIAL'] = 'turn-pass'
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

        token_inactive = self.client.post('/api/video-call/inactive-room/token', json={})
        self.assertEqual(token_inactive.status_code, 404)

        join_one = self.client.post(f'/api/video-call/{room_id}/join')
        self.assertEqual(join_one.status_code, 200)
        one_data = join_one.get_json()
        self.assertTrue(one_data['success'])
        client_one = one_data['client_id']
        self.assertTrue(one_data['is_initiator'])

        token_ok = self.client.post(f'/api/video-call/{room_id}/token', json={'display_name': 'Judge A'})
        self.assertEqual(token_ok.status_code, 200)
        token_data = token_ok.get_json()
        self.assertTrue(token_data['success'])
        self.assertTrue(bool(token_data['token']))
        self.assertEqual(token_data['room_id'], room_id)
        self.assertEqual(token_data['ws_path'], self.app.config['VIDEO_WS_PATH'])

        ice_ok = self.client.get(f'/api/video-call/{room_id}/ice-config')
        self.assertEqual(ice_ok.status_code, 200)
        ice_data = ice_ok.get_json()
        self.assertTrue(ice_data['success'])
        self.assertTrue(any('turn:turn.example.com:3478' in server['urls'] for server in ice_data['ice_servers']))

        status_unauth = self.client.get(f'/internal/video-call/{room_id}/status')
        self.assertEqual(status_unauth.status_code, 401)

        status_ok = self.client.get(
            f'/internal/video-call/{room_id}/status',
            headers={'X-Internal-Token': 'test-internal-token'},
        )
        self.assertEqual(status_ok.status_code, 200)
        self.assertTrue(status_ok.get_json()['active'])

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

        terminate_ok = self.client.post(
            f'/internal/video-call/{room_id}/terminate',
            headers={'X-Internal-Token': 'test-internal-token'},
            json={'reason': 'unit_test'},
        )
        self.assertEqual(terminate_ok.status_code, 200)
        self.assertTrue(terminate_ok.get_json()['success'])

        status_after = self.client.get(
            f'/internal/video-call/{room_id}/status',
            headers={'X-Internal-Token': 'test-internal-token'},
        )
        self.assertEqual(status_after.status_code, 200)
        self.assertFalse(status_after.get_json()['active'])

    def test_complaint_submission_creates_pending_judge_record(self):
        with self.app.app_context():
            db.session.add(
                Accused(
                    username='Test Accused',
                    relative_name='Relative',
                    relation='Father',
                    dob=date(2000, 1, 1),
                    gender='Male',
                    nationality='Indian',
                    occupation='Worker',
                    education='Graduate',
                    permanent_address='Some Address',
                    temporary_address='',
                    mobile='9999999999',
                    email_id='accused@example.com',
                    case_no='CASE-2026-500',
                    fir_no='FIR-500',
                    case_type='Criminal',
                    ps='Station',
                )
            )
            db.session.commit()

        response = self.client.post(
            '/complaints',
            data={
                'complain_type': 'Crime',
                'description': 'Initial complaint from victim family.',
                'case_no': 'CASE-2026-500',
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            complaint = ComplaintDescription.query.filter_by(case_no='CASE-2026-500').first()
            decision = JudgeDecision.query.filter_by(case_no='CASE-2026-500').first()
            self.assertIsNotNone(complaint)
            self.assertIsNotNone(decision)
            self.assertEqual(decision.status, 'Pending')
            self.assertEqual(decision.workflow_stage, 'Complaint Registered')

    def test_judge_submit_decision_persists_structured_notes(self):
        with self.app.app_context():
            db.session.add(
                Accused(
                    username='Decision Test',
                    relative_name='Relative',
                    relation='Mother',
                    dob=date(1999, 2, 2),
                    gender='Female',
                    nationality='Indian',
                    occupation='Teacher',
                    education='Graduate',
                    permanent_address='Address',
                    temporary_address='',
                    mobile='8888888888',
                    email_id='decision@example.com',
                    case_no='CASE-2026-600',
                    fir_no='FIR-600',
                    case_type='Criminal',
                    ps='Station',
                )
            )
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['judge_logged_in'] = True
            sess['judge_username'] = 'Judge'

        response = self.client.post(
            '/judge/submit-decision',
            data={
                'case_no': 'CASE-2026-600',
                'decision': 'Pending',
                'total_fine': '5000',
                'imprisonment': '1 year',
                'hearing_summary': 'Witness examined and adjourned for document verification.',
                'evidence_review': 'Medical report and call detail records reviewed.',
                'order_notes': 'Matter kept pending for final order after next hearing.',
                'family_update_note': 'Family informed that the matter is still under judicial review.',
                'next_hearing_at': '2026-03-30T11:30',
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/judge/pending', response.headers.get('Location', ''))

        with self.app.app_context():
            decision = JudgeDecision.query.filter_by(case_no='CASE-2026-600').first()
            self.assertIsNotNone(decision)
            self.assertEqual(decision.status, 'Pending')
            self.assertEqual(decision.workflow_stage, 'Pending Judge Review')
            self.assertEqual(decision.total_fine, '5000')
            self.assertEqual(decision.imprisonment, '1 year')
            self.assertIn('Witness examined', decision.hearing_summary)
            self.assertIn('Medical report', decision.evidence_review)
            self.assertIn('judicial review', decision.family_update_note)


if __name__ == '__main__':
    unittest.main()
