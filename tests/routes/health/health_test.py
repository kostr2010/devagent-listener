import unittest

from app.routes.health.endpoint import endpoint_health, Response


class RouteHealthTest(unittest.TestCase):
    def test_health(self) -> None:
        response = endpoint_health()
        self.assertEqual(response.status, "healthy")
