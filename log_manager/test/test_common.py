from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory
from log_manager.models import Logs


class TestCommon(APITestCase):
    user = None
    tkn = ""
    factory = APIRequestFactory()

    @classmethod
    def setUpClass(cls):
        # creating admin user for testing
        cls.user = User.objects.create(
            **{
                "username": "test_admin",
                "email": "test_admin@gmail.com",
                "first_name": "first_name",
                "last_name": "last_name",
                "password": make_password("test@123"),
                "is_staff": True
            }
        )
        cls.cls_atomics = cls._enter_atomics()
        return cls

    def setUp(self):
        resp = self.client.post(
            "/auth/login", {
                "username": "test_admin",
                "password": "test@123"
            }
        )
        assert resp.status_code == 200
        self.tkn = f"Token {resp.json()['token']}"
        self.client.credentials(HTTP_AUTHORIZATION=self.tkn)
        return self

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        Logs.objects.all().delete()
        return cls
