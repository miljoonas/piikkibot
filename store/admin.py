from django.contrib import admin
from .models import Item, TelegramUser, Transaction
# Register your models here.

class ItemAdmin(admin.ModelAdmin):
  list_display = ('name', 'price', 'amount')

class TelegramUserAdmin(admin.ModelAdmin):
  list_display = ('name', 'username', 'balance')

class TransactionAdmin(admin.ModelAdmin):
  list_display = ('type','amount','user_name','date')

admin.site.register(Item, ItemAdmin)
admin.site.register(TelegramUser, TelegramUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
