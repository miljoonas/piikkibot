from django.db import models

# Create your models here.
class Item(models.Model):
  name = models.CharField(max_length=18)
  price = models.DecimalField(max_digits=28, decimal_places=2)
  amount = models.IntegerField(default=0)

class TelegramUser(models.Model):
  username = models.CharField(max_length=32)
  name = models.CharField(max_length=100)
  chat_id = models.CharField(max_length=50)
  balance = models.DecimalField(max_digits=28, decimal_places=2, default=0)
  
  def __str__(self):
    return self.name

class Transaction(models.Model):
  user_id = models.CharField(max_length=50)
  user_name = models.CharField(max_length=100, default="")
  type = models.CharField(max_length=18)
  date = models.DateTimeField()
  amount = models.DecimalField(max_digits=28, decimal_places=2)

  def __str__(self):
    return self.type