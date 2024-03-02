from django.urls import path
from .views import home_view, account_view, GentokenView, LoginView, logout_view, CouponView, PayView, download_config_view

urlpatterns = [
    path("", home_view, name="home"),
    path("account/", account_view, name="account"),
    path("gentoken/", GentokenView.as_view(), name="gentoken"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("coupon/activate/<str:coupon>", CouponView.set, name="coupon-clear"),
    path("coupon/clear/", CouponView.clear, name="coupon-clear"),
    path("invoice/", PayView.create, name="invoice-create"),
    path("invoice/<str:payment_hex>", PayView.get, name="invoice-get"),
    path("download/conf/<str:filename>.zip", download_config_view, name="download-conf"),
]
