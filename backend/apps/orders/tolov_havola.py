"""Click va Payme to'lov havolalari (salon merchant ma'lumotlari «Integratsiyalar»da kiritilgan bo'lsa).

Havola mijozga ko'rsatiladi yoki yuboriladi; to'lov tushgach sotuvchi uni kassada odatdagidek (usul: Click/Payme)
qabul qiladi. To'lovni avtomatik tasdiqlash (webhook) yo'q — merchant kabinetida tekshiriladi.
Merchant ma'lumotlari kiritilmagan bo'lsa havola chiqmaydi va tizim avvalgidek ishlaydi.
"""
import base64
from urllib.parse import urlencode

from apps.tenants.models import integratsiya


def havolalar(zakaz, summa):
    """{'click': url, 'payme': url} — faqat sozlangan tizimlar. `summa` so'mda."""
    i = integratsiya(zakaz.salon)
    natija = {}
    if summa <= 0:
        return natija
    if i.click_service_id and i.click_merchant_id:
        natija['click'] = 'https://my.click.uz/services/pay?' + urlencode({
            'service_id': i.click_service_id, 'merchant_id': i.click_merchant_id, 'amount': summa,
            'transaction_param': zakaz.raqam})
    if i.payme_merchant_id:
        # Payme summani tiyinda oladi
        satr = f'm={i.payme_merchant_id};ac.order_id={zakaz.raqam};a={summa * 100}'
        natija['payme'] = 'https://checkout.paycom.uz/' + base64.b64encode(satr.encode()).decode()
    return natija
