from django.views import View

from .models import User, Coupon, Plan, Invoice
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.core.exceptions import SuspiciousOperation
from django.http import FileResponse, HttpResponseForbidden

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings

from django.utils.crypto import get_random_string

from django.contrib import messages

from .utils import fetch_usd_xmr
import decimal


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def home_view(request):
    return render(request, "home.html")

class GentokenView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/')
        return render(request, "gentoken.html")

    def post(self, request):
        username = get_random_string(8)
        password = get_random_string(16)
        new_user = User(username=username)
        new_user.set_password(password)
        new_user.save()
        login(request, new_user)
        return render(request, "generated.html", {"token": f"{username}:{password}"})


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        if request.POST.get("token") is None:
            messages.error(request, "No credentails supplied")
            return render(request, self.template_name)
        if not ":" in request.POST.get("token"):
            messages.error(
                request,
                "Invalid format. Insert your username:password pair, or create new account instead",
            )
            return render(request, self.template_name)
        username, password = request.POST.get("token").split(":", 1)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            messages.error(request, "Invalid credentails")
            return render(request, self.template_name)


def logout_view(request):
    logout(request)
    messages.info(request, "You've logged out")
    return redirect("/")


def account_view(request):
    plans = CouponView.list_plans(request)

    return render(
        request, "account.html", {"token": request.POST.get("token"), "plans": plans}
    )

class CouponView:
    def set(request, coupon=None):
        resp = redirect("/")
        if coupon is not None:
            c = Coupon.objects.filter(text=coupon)
            resp.set_cookie("coupon", coupon)
        return resp

    def clear(request):
        resp = redirect("/")
        resp.delete_cookie("coupon")
        return resp

    def list_plans(request):
        coupon = 1
        if request.COOKIES.get("coupon") is not None:
            coupon_obj = Coupon.objects.get(text=request.COOKIES.get("coupon"))
            if coupon_obj.is_usable:
                coupon = coupon_obj.id
        plans = Plan.objects.filter(coupon=coupon)
        return plans


class PayView:
    @login_required
    def get(request, payment_hex):
        payment_id = bytes.fromhex(payment_hex)
        invoice = get_object_or_404(Invoice, payment_id=payment_id)
        return render(request, "invoice.html", {"invoice": invoice})

    @login_required
    def create(request):
        if request.method != "POST":
            return redirect("/")
        plan = get_object_or_404(Plan, uuid__exact=request.POST.get("plan"))
        if not plan.coupon.is_usable:
            raise SuspiciousOperation("Attempt to use plan from expired coupon")

        invoice = create_invoice(request.user, plan)
        return redirect("invoice-get", payment_hex=invoice.payment_id.hex())


def create_invoice(user, plan):
    if plan.price_usd == 0:
        new_invoice = Invoice(user=user, plan=plan)
        new_invoice.save()
        new_invoice.set_paid()
        return new_invoice
    usd_per_xmr = fetch_usd_xmr()
    price_xmr = round(
        decimal.Decimal(plan.price_usd) / decimal.Decimal(usd_per_xmr), 12
    )
    new_invoice = Invoice(user=user, plan=plan, price_xmr=price_xmr)
    new_invoice.save()
    return new_invoice

@login_required
def download_config_view(request, filename):
    if request.user.username != filename:
        return HttpResponseForbidden()
    confpath = (settings.VPN_USERZIP / request.user.username).with_suffix('.zip')
    if request.user.status != User.Status.ACTIVE:
        messages.info(request, "Your account isn't activated yet")
        return redirect('account')
    try:
        return FileResponse(open(confpath, 'rb'))
    except FileNotFoundError:
        messages.error(request, "ZIP archive was not found on the server. Please try again later. If the issue persists, please contact the support.")
        return redirect('account')

