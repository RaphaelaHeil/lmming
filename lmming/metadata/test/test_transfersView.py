from django.test import TestCase
from django.urls import reverse

from metadata.models import Page
from metadata.test.utils import initDummyTransfer


class TransfersView(TestCase):

    def tearDown(self):
        for page in Page.objects.all():
            page.delete()

    def test_noTransfer(self):
        response = self.client.get(reverse("metadata:transfer_table"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["jobs"]), 0)

    def test_transfer(self):
        initDummyTransfer()
        response = self.client.get(reverse("metadata:transfer_table"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["jobs"]), 1)
