from .models import Coupon
from django.contrib import messages
from django.shortcuts import redirect, reverse


class CouponMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/':
            if request.COOKIES.get("coupon") is not None:
                coupon = Coupon.objects.filter(text=request.COOKIES.get("coupon"))
                if not coupon.exists() or not coupon.first().is_usable:
                    messages.info(request, "Coupon has expired.")
                    return redirect("coupon-clear")
        return self.get_response(request)
