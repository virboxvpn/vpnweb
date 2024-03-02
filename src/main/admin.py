from django.contrib import admin

from .models import User, Coupon, Plan, Invoice, VPNServer

admin.site.register(User)
admin.site.register(Coupon)
admin.site.register(Plan)
admin.site.register(Invoice)
admin.site.register(VPNServer)
