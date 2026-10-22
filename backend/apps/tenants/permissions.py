from rest_framework.permissions import BasePermission

from .models import Salon, Xodim


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, Xodim)


class IsRahbar(IsStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Xodim.Rol.RAHBAR


class SalonYozishRuxsati(IsStaff):
    """«Faqat ko'rish» holatidagi salonda yozish mumkin emas (FT-22.8)."""
    SAFE = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in self.SAFE:
            return True
        return salon_yoza_oladimi(request.salon)


def salon_yoza_oladimi(salon):
    """Salon yozishga ochiqmi (FT-22.8). GET ichidagi yon yozuvlar (qoralama, avto-bekor) ham shunga qaraydi."""
    return salon.holat in (Salon.Holat.SINOV, Salon.Holat.FAOL)
