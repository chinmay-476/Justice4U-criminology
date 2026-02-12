import unittest

from security import is_valid_case_no, is_valid_meeting_link


class SecurityUtilsTests(unittest.TestCase):
    def test_valid_case_number(self):
        self.assertTrue(is_valid_case_no('CASE-2025-001'))
        self.assertTrue(is_valid_case_no('A_123/45'))

    def test_invalid_case_number(self):
        self.assertFalse(is_valid_case_no(''))
        self.assertFalse(is_valid_case_no('../etc/passwd'))
        self.assertFalse(is_valid_case_no('case number with spaces'))

    def test_meeting_link_validation(self):
        self.assertTrue(is_valid_meeting_link('https://meet.example.com/room/123'))
        self.assertTrue(is_valid_meeting_link('http://localhost:8080/test'))
        self.assertFalse(is_valid_meeting_link('javascript:alert(1)'))
        self.assertFalse(is_valid_meeting_link(''))


if __name__ == '__main__':
    unittest.main()
