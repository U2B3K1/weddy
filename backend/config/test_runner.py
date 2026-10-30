"""Test runner: «virtual bugun» va testlarga xalaqit beradigan umumiy sozlamalar.

Ko'p testlar qattiq sanalarni ishlatadi (masalan, zakaz `2026-11-20` da olib ketiladi). Haqiqiy kun o'sha sanadan
o'tsa, «o'tgan sanaga zakaz ochib bo'lmaydi» kabi qoidalar testlarni yiqitardi — kod emas, kalendar buzardi.
Shuning uchun testlarda soat ortga suriladi: bugungi sana doim `TEST_BUGUN`, kun ichidagi vaqt esa odatdagidek oqadi.
Ilova vaqtni faqat `django.utils.timezone.now()` / `localdate()` orqali oladi (bazadagi `Now()` ishlatilmaydi),
shuning uchun `timezone.now` ni almashtirish yetarli.

`TEST_BUGUN` muhit o'zgaruvchisi bilan boshqa kunni sinash mumkin: `TEST_BUGUN=2027-03-01 python manage.py test`.
"""
import datetime
import logging
import os

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings
from django.utils import timezone

STANDART_BUGUN = datetime.date(2026, 10, 30)  # testlar shu kunda yozilgan va to'liq o'tgan


class SobitBugunRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        bugun = datetime.date.fromisoformat(os.environ['TEST_BUGUN']) if os.environ.get('TEST_BUGUN') else STANDART_BUGUN
        self._asl_now = asl_now = timezone.now
        siljish = datetime.timedelta(days=(timezone.localdate() - bugun).days)
        timezone.now = lambda: asl_now() - siljish
        # Umumiy so'rov chegarasi (DRF throttle) testlarda o'chiq: hisob testlar orasida saqlanib, ketma-ket
        # testlarni tasodifan 429 bilan yiqitardi. Faqat `chegara` keshi o'chiriladi (standart kesh — SMS tokeni
        # va boshqalar — odatdagidek ishlaydi). Chegaraning o'zi alohida testda yoqib tekshiriladi.
        from django.conf import settings
        self._chegarasiz = override_settings(CACHES={
            **settings.CACHES, 'chegara': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
        self._chegarasiz.enable()
        logging.disable(logging.INFO)  # ilova INFO loglari test natijasini to'ldirib yubormasin

    def teardown_test_environment(self, **kwargs):
        logging.disable(logging.NOTSET)
        self._chegarasiz.disable()
        timezone.now = self._asl_now
        super().teardown_test_environment(**kwargs)
