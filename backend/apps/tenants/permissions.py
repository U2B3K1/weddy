from rest_framework.permissions import BasePermission

from .models import Salon, Xodim

# «Faqat ko'rish» (obuna tugagan) salonida yozish rad etilganda xodim ko'radigan matn (C-12)
FAQAT_KORISH_XABARI = ("Obuna muddati tugagan: yangi zakaz, katalog va sozlamalar yopiq. "
                       "Boshlangan zakazlarni yakunlash mumkin.")


class IsStaff(BasePermission):
    # QA-18: DRF ning inglizcha «You do not have permission…» o'rniga
    message = "Bu amal faqat salon xodimlariga ruxsat etilgan."

    def has_permission(self, request, view):
        return isinstance(request.user, Xodim)


class IsRahbar(IsStaff):
    message = "Bu amal faqat rahbarga ruxsat etilgan."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Xodim.Rol.RAHBAR


class SalonYozishRuxsati(IsStaff):
    """«Faqat ko'rish» holatidagi salonda yozish mumkin emas (FT-22.8).

    Foydalanuvchi qarori (2026-11-07, C-12 → b): obuna tugaganda yangi zakaz, katalog, sozlamalar va xarajat to'xtaydi,
    lekin **boshlangan zakazni yakunlash** ishlaydi — to'lov, berish, qaytarish, zalogni qaytarish, smena va pul topshirish.
    Bunday view'da `faqat_korishda_ruxsat = True` belgisi qo'yiladi. Bloklangan salonda hech qanday yozuv yo'q.
    Rad etilganda DRF ning inglizcha «You do not have permission…» o'rniga o'zbekcha sabab qaytadi.
    """
    SAFE = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in self.SAFE:
            return True
        if salon_yoza_oladimi(request.salon):
            return True
        if request.salon.holat == Salon.Holat.FAQAT_KORISH and getattr(view, 'faqat_korishda_ruxsat', False):
            return True
        # Xabar faqat salon holati sabab bo'lganda (boshqa rad etishlarda DRF standart matni qoladi)
        self.message = (FAQAT_KORISH_XABARI if request.salon.holat == Salon.Holat.FAQAT_KORISH
                        else "Salon bloklangan: o'zgartirish mumkin emas. Platforma bilan bog'laning.")
        return False


def salon_yoza_oladimi(salon):
    """Salon yozishga ochiqmi (FT-22.8). GET ichidagi yon yozuvlar (qoralama, avto-bekor) ham shunga qaraydi."""
    return salon.holat in (Salon.Holat.SINOV, Salon.Holat.FAOL)


def yozish_taqiqi(request, view):
    """GET va yozuv bitta view'da bo'lsa, qo'lda tekshirish uchun: ruxsat yo'q — o'zbekcha sababli 403 javob, bor — None.
    Ishlatish: `if (rad := yozish_taqiqi(request, self)): return rad`."""
    from rest_framework.response import Response
    p = SalonYozishRuxsati()
    if p.has_permission(request, view):
        return None
    return Response({'detail': getattr(p, 'message', None) or FAQAT_KORISH_XABARI}, status=403)
