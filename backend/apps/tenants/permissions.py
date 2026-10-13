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
        return request.salon.holat in (Salon.Holat.SINOV, Salon.Holat.FAOL)
