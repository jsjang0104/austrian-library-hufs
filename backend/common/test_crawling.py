from urllib.robotparser import RobotFileParser

from django.test import SimpleTestCase, TestCase

from library.models import Notice


class RobotsPolicyTests(SimpleTestCase):
    def test_crawlers_can_render_public_content_but_not_private_or_ai_endpoints(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/plain'))
        parser = RobotFileParser()
        parser.parse(response.content.decode().splitlines())
        for agent in ('Googlebot', 'bingbot', 'SomeCrawler'):
            for path, allowed in (
                ('/api/notices/', True),
                ('/api/notices/7/', True),
                ('/api/books/?search=Kafka', True),
                ('/static/admin/css/base.css', True),
                ('/media/notice.jpg', True),
                ('/admin/', False),
                ('/manager/managers/', False),
                ('/api/members/', False),
                ('/api/members/token/', False),
                ('/api/loans/', False),
                ('/api/token/refresh/', False),
                ('/api/books/smart_search/?q=Kafka', False),
            ):
                with self.subTest(agent=agent, path=path):
                    self.assertEqual(parser.can_fetch(agent, path), allowed)

    def test_private_responses_remain_protected_and_carry_noindex(self):
        for path, status in (
            ('/api/loans/', 401),
            ('/api/members/', 401),
            ('/manager/managers/', 401),
            ('/admin/', 302),
            ('/api/not-a-route/', 404),
            ('/api/token/', 405),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status)
                self.assertIn('noindex', response.get('X-Robots-Tag', ''))


class PublicAPICrawlingTests(TestCase):
    def test_public_json_is_readable_but_not_indexable(self):
        notice = Notice.objects.create(title='운영 안내', content='공개 공지')
        for path in ('/api/notices/', f'/api/notices/{notice.pk}/', '/api/books/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/json')
                self.assertIn('noindex', response.get('X-Robots-Tag', ''))
        self.assertEqual(self.client.get(f'/api/notices/{notice.pk}/').json()['content'], '공개 공지')
