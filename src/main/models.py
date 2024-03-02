from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.core.validators import RegexValidator
import secrets
import uuid
import math
from django.conf import settings
from monero.address import Address
import celery


class UserManager(BaseUserManager):
    def create_user(self, username, password):
        user = self.model(username=username)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        user = self.create_user(username, password)
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username = models.CharField(max_length=8, unique=True)
    balance_halfdays = models.IntegerField(default=0)
    @property
    def balance(self):
        return math.ceil(self.balance_halfdays / 2)
    @balance.setter
    def balance(self, value):
        self.balance_halfdays = value * 2

    class Status(models.IntegerChoices):
        INACTIVE = 0
        ACTIVATING = 1
        ACTIVE = 2

    status = models.IntegerField(choices=Status.choices, default=Status.INACTIVE)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    last_login = None

    objects = UserManager()

    USERNAME_FIELD = "username"

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        return self.is_admin

    def __str__(self):
        if self.status == self.Status.ACTIVE:
            return   f'User {self.username} (active), balance {self.balance} days'
        else: return f'User {self.username}, balance {self.balance} days'


class Coupon(models.Model):
    id = models.AutoField(primary_key=True)
    text = models.CharField(max_length=10, unique=True, db_index=True)
    total_count = models.IntegerField(default=0)
    used_count = models.IntegerField(default=0, editable=False)
    is_unlimited = models.BooleanField(default=False)

    @property
    def is_usable(self):
        return self.is_unlimited or (self.used_count < self.total_count)

    def used(self):
        self.used_count += 1
        self.save()

    def __str__(self):
        if self.is_unlimited:
            return f"Coupon '{self.text}' - {self.used_count} used"
        else:
            return f"Coupon '{self.text}' - {self.used_count}/{self.total_count} used"


class Plan(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_DEFAULT, default=1)
    n_days = models.IntegerField()
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def days(self):
        if self.n_days == 1:
            return f"{self.n_days} day"
        else:
            return f"{self.n_days} days"

    def __str__(self):
        return f"Plan #{self.id}: ${self.price_usd} - {self.days}"


class Invoice(models.Model):
    # Wallet address + 64-bit payment_id -> Integrated wallet
    id = models.AutoField(primary_key=True)

    def gen_payment_id():
        return secrets.token_bytes(8)

    payment_id = models.BinaryField(
        default=gen_payment_id, unique=True, editable=False, db_index=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    price_xmr = models.DecimalField(max_digits=20, decimal_places=12, default=0)
    created = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    @property
    def created_str(self):
        return self.created.isoformat(sep=' ', timespec='seconds')

    @property
    def address(self):
        return Address(settings.MONERO_WALLET_ADDR).with_payment_id(self.payment_id.hex())

    def set_paid(self):
        self.is_paid = True
        self.save()
        self.plan.coupon.used()
        self.user.balance += self.plan.n_days
        self.user.status = User.Status.ACTIVATING
        self.user.save()
        celery.execute.send_task('main.tasks.activate_service', args=[self.user.id])

    def __str__(self):
        paid_str = 'PAID' if self.is_paid else 'UNPAID'
        return f"Invoice {paid_str} for {self.user.username} - ${self.plan.price_usd} - {self.created_str} #{self.id}:{self.payment_id.hex()} "

class VPNServer(models.Model):
    id = models.AutoField(primary_key=True)
    ip = models.GenericIPAddressField(protocol='IPv4', unique=True)
    visible_name = models.CharField(max_length=32, unique=True)
    ssh_user = models.CharField(max_length=32, default='virbox', validators=[RegexValidator('^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$')])
    ssh_port = models.PositiveIntegerField(default=22)
    def __str__(self):
        return f'{self.visible_name} - {self.ssh_user}@{self.ip}:{self.ssh_port}'

