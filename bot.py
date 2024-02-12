from typing import Final
from telegram import (
  Update, 
  ReplyKeyboardMarkup, 
  InlineKeyboardButton, 
  InlineKeyboardMarkup,
  ReplyKeyboardRemove,
  )
from telegram.ext import (
  Application, 
  CommandHandler, 
  MessageHandler, 
  filters, 
  ContextTypes, 
  ConversationHandler, 
  CallbackQueryHandler,
  )

from django.utils import timezone 
from django.db.models import F

# setup django
import os
import django
import decimal

import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'askipiikkibot.settings')
django.setup()

from store.models import Item, TelegramUser, Transaction

BEGINNING, ADD, REDIRECT, UNDO = range(4)
balance_keywords = ["Show balance", "Add balance", "Cancel"]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # reply_keyboard = [
  #   ["/prices"],
  #   ["/help"],
  # ]
  await update.message.reply_text('Welcome to ASki Piikkibot \ntype /help to get started')
  # await update.message.reply_text('Starting bot... type /help to get started', reply_markup=ReplyKeyboardMarkup(reply_keyboard, ))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text((
    "ASki Piikkibot has the following commands:\n\n"
    "/register\n Register as a bot user before gaining access to it's features.\n\n"
    "/prices\n Prints a list of the products and their prices.\n\n"
    "/store\n With this command you can buy items from the store. When you select a product it's price is deducted from your account balance\n\n"
    "/balance\nView and modify your account balance, remember to pay to *MobilePay* [94903]({}) the amount you have added to your balance.\n\n"
    "/undo\n If you make a mistake this command undoes your last transaction. This can be used consecutively many times if needed."
    ).format('https://qr.mobilepay.fi/box/9bb325e0-ac14-472e-b9dc-deedb170af7b/pay-in'), parse_mode="MARKDOWN", disable_web_page_preview=True)


async def is_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  try:
    await TelegramUser.objects.aget(chat_id=user.id)
    return True
  except TelegramUser.DoesNotExist:
    await update.message.reply_text("You need to /register to use this feature")
    return False


async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = "```\nPrices:\n"
  async for item in Item.objects.all():
    text += "{:_<18.18} {:.2f}€\n".format(item.name.strip() + " ", item.price)
  await update.message.reply_text(text + "```", parse_mode="MARKDOWN")


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  
  try:
    user_exists = await TelegramUser.objects.aget(chat_id=user.id)
    print(user_exists)
    await update.message.reply_text("You have already registered")
  except TelegramUser.DoesNotExist:
    # print("Creating a new user")
    name = ""
    if user.first_name and user.last_name:
      name = "{} {}".format(user.first_name, user.last_name)
    else:
      name = user.first_name
    username = ""
    if user.username:
      username = user.username
    new_user = TelegramUser(name=name, username=username, chat_id=user.id)
    await new_user.asave()
    await update.message.reply_text("New user registered. Welcome to use ASki Piikkibot!")

async def store(update: Update, context: ContextTypes.DEFAULT_TYPE):
  
  if not await is_registered(update, context):
    return
  
  keyboard = []
  buttons_per_row = 2

  buttons = [InlineKeyboardButton("{} {:.2f}€".format(product.name, product.price), callback_data=product.name) async for product in Item.objects.all()]

  for i in range(0, len(buttons), buttons_per_row):
    keyboard.append(buttons[i:i+buttons_per_row])

  keyboard.append([InlineKeyboardButton("Back", callback_data="Back")])
  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text("Select a product:", reply_markup=reply_markup)
    

async def button_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
  
  if not await is_registered(update, context):
    return
  
  query = update.callback_query
  if query.data == "Back":
    await query.edit_message_text(text="Interrupted")
    return

  user = update.effective_user
  time = timezone.now()
  item = await Item.objects.aget(name=query.data)
  db_user = await TelegramUser.objects.aget(chat_id=user.id)
  await Item.objects.filter(name=query.data).aupdate(amount=(item.amount-1))

  new_transaction = Transaction(user_id=user.id, user_name=user.name, type=item.name, date=time, amount=-item.price)
  await new_transaction.asave()
  
  await TelegramUser.objects.filter(chat_id=user.id).aupdate(balance=(db_user.balance-item.price))
  
  db_user_refreshed = await TelegramUser.objects.aget(chat_id=user.id)
  await query.edit_message_text(text="You have successfully bought: {}.\n\n Balance: {:.2f}€".format(item.name, db_user_refreshed.balance))

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
  
  if not await is_registered(update, context):
    return
  
  user = update.effective_user
  global balance_keywords
  keyboard = [[balance_keywords[1]], [balance_keywords[2]]]
  reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
  db_user = await TelegramUser.objects.aget(chat_id=user.id)
  await update.message.reply_text(
    "Your current balance is: {:.2f}€.".format(db_user.balance), 
    reply_markup=reply_markup
  )
  return REDIRECT

async def redirect(update: Update, context:ContextTypes.DEFAULT_TYPE):
  update.message
  update.effective_message
  update.effective_chat
  update.effective_user

  global balance_keywords
  if update.effective_message.text == balance_keywords[1]:
    await update.message.reply_text(
            "How much money would you like to add? Give a positive decimal number:",
            reply_markup=ReplyKeyboardRemove(),
    )
    return ADD
  if update.effective_message.text == balance_keywords[2]:
    return ConversationHandler.END

async def add_money(update: Update, context:ContextTypes.DEFAULT_TYPE):
  amount = 0
  try:
    amount = decimal.Decimal(update.message.text.replace(",", "."))
    if amount < 0:
      raise ValueError
  except ValueError:
    await update.message.reply_text("Invalid value. Operation cancelled.")
    return ConversationHandler.END
  user = update.effective_user
  time = timezone.now()
  db_user = await TelegramUser.objects.aget(chat_id=user.id)

  await TelegramUser.objects.filter(chat_id=user.id).aupdate(balance=(db_user.balance+amount))

  new_transaction = Transaction(user_id=user.id, user_name=user.name, type="ADD", date=time, amount=amount)
  await new_transaction.asave()


  db_user = await TelegramUser.objects.aget(chat_id=user.id)
  await update.message.reply_text(
    "Adding funds succeeded, Your new balance is: {:.2f}€.".format(db_user.balance), 
    reply_markup=ReplyKeyboardRemove()
  )
  print("Money added")
  return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  print("here?")
  await update.message.reply_text("Operation cancelled", reply_markup=ReplyKeyboardRemove())
  return ConversationHandler.END

async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  
  if not await is_registered(update, context):
    return
  
  keyboard = [["Yes"],["No"]]
  reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
  user = update.effective_user
  try:
    previous_transaction = await Transaction.objects.filter(user_id=user.id).alatest('date')
    print(previous_transaction)
    await update.message.reply_text(
      (
        "Do you want to remove transaction:\n{}.{}.{} - {}:{} {} {:.2f}€?"
      ).format(
        previous_transaction.date.day, 
        previous_transaction.date.month, 
        previous_transaction.date.year, 
        previous_transaction.date.hour,
        previous_transaction.date.minute,
        previous_transaction.type, 
        previous_transaction.amount
        ),
      reply_markup=reply_markup,
    )
    return UNDO
  except Transaction.DoesNotExist:
    await update.message.reply_text("You have no previous transactions.")
    print("No transactions")


async def undo_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.message.text == "Yes":
    user = update.effective_user
    previous_transaction = await Transaction.objects.filter(user_id=user.id).alatest('date')
    if previous_transaction.type != "ADD":
      print("adding item amount")
      await Item.objects.filter(name=previous_transaction.type).aupdate(amount=F('amount')+1)
    await TelegramUser.objects.filter(chat_id = previous_transaction.user_id).aupdate(balance=F('balance')-previous_transaction.amount)
    await previous_transaction.adelete()
    
    db_user = await TelegramUser.objects.aget(chat_id=user.id)
    await update.message.reply_text(
      "Previous action has been cancelled,\nyour account balance is: {:.2f}€".format(db_user.balance),
      reply_markup=ReplyKeyboardRemove()
      )
  else:
    await update.message.reply_text(
      "Action cancelled", 
      reply_markup=ReplyKeyboardRemove()
      )
  return ConversationHandler.END


if __name__ == '__main__':
  app = Application.builder().token(config.TOKEN).build()

  conv_handler = ConversationHandler(
    entry_points=[CommandHandler("balance", balance, filters.ChatType.PRIVATE)],
    states={
      BEGINNING: [MessageHandler(filters.TEXT, balance)],
      REDIRECT: [MessageHandler(filters.Regex("^({}|{})$".format(balance_keywords[1], balance_keywords[2])), redirect)],
      ADD: [MessageHandler(filters.TEXT, add_money)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
  )

  undo_handler = ConversationHandler(
    entry_points=[CommandHandler("undo", undo, filters.ChatType.PRIVATE)],
    states={UNDO: [MessageHandler(filters.Regex(r"^(Yes|No)$"), undo_execute)]},
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
  )

  # commands
  app.add_handler(CommandHandler('start', start_command, filters.ChatType.PRIVATE))
  app.add_handler(CommandHandler('help', help_command, filters.ChatType.PRIVATE))
  app.add_handler(CommandHandler('prices', prices_command, filters.ChatType.PRIVATE))
  app.add_handler(CommandHandler('register', register_command, filters.ChatType.PRIVATE))
  app.add_handler(CommandHandler('store', store, filters.ChatType.PRIVATE))
  
  app.add_handler(CallbackQueryHandler(button_response))
  

  app.add_handler(conv_handler)
  app.add_handler(undo_handler)


  # messages
  # app.add_handler(MessageHandler(filters.TEXT, handle_message))

  app.run_polling()