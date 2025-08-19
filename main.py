# main.py
import telebot
import json
import os
from datetime import datetime, timedelta

API_TOKEN = os.environ.get("API_TOKEN")
ADMIN_USER = "@Pruthvirajbhuruk"
WALLET_ADDRESS = "TNH9tQy2UAipH9ECQDaHPkAA13Np2nS5bV"

bot = telebot.TeleBot(API_TOKEN)

# Load/Save Data
def load_data():
    try:
        with open("database.json", "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "referrals": {}}

def save_data(data):
    with open("database.json", "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# Start
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "username": username,
            "plan": None,
            "amount": 0,
            "next_payout": None,
            "ref_by": None,
            "ref_earn": 0
        }
        save_data(data)

    # Referral Tracking
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        if ref_code in data["users"] and ref_code != user_id:
            data["users"][user_id]["ref_by"] = ref_code

    text = (
        "💼 *Investment E-Bank*\n\n"
        "Welcome to Investment E-Bank — the #1 trusted crypto-based investment platform.\n"
        "Choose your plan and grow your money every month.\n\n"
        "👉 Use /invest to get started"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Invest
@bot.message_handler(commands=["invest"])
def invest(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Basic ($15-$69)", "Classic ($200-$499)", "Pro ($1000-$1999)")
    bot.send_message(message.chat.id, "Select your plan:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["Basic ($15-$69)", "Classic ($200-$499)", "Pro ($1000-$1999)"])
def plan_selected(message):
    plan = message.text.split()[0].lower()
    user_id = str(message.from_user.id)
    data["users"][user_id]["plan"] = plan
    save_data(data)

    bot.send_message(message.chat.id,
                     f"Great! Send USDT-TRC20 to the following address:\n\n`{WALLET_ADDRESS}`\n\n"
                     f"⚠️ *After sending*, reply here with:\n"
                     f"`TXN_HASH <amount>`\nExample: TXN_HASH abcd1234 200",
                     parse_mode="Markdown")

# Capture payment info
@bot.message_handler(func=lambda m: m.text.startswith("TXN_HASH"))
def capture_txn(message):
    user_id = str(message.from_user.id)
    try:
        _, txn_hash, amount = message.text.split()
        amount = float(amount)
        data["users"][user_id]["txn"] = txn_hash
        data["users"][user_id]["amount"] = amount
        save_data(data)

        # Notify Admin
        bot.send_message(message.chat.id, "⏳ Waiting for admin approval...")
        bot.send_message(ADMIN_USER,
                         f"✅ New Investment\nUser: @{data['users'][user_id]['username']}\n"
                         f"Plan: {data['users'][user_id]['plan']}\nAmount: {amount}\nTXN: {txn_hash}\n\n"
                         f"Use /approve {user_id} {amount} to confirm.")
    except:
        bot.send_message(message.chat.id, "Wrong format. Use:\nTXN_HASH <hash> <amount>")

# Admin approve
@bot.message_handler(commands=["approve"])
def approve(message):
    if message.from_user.username != ADMIN_USER[1:]:
        return

    try:
        _, uid, amt = message.text.split()
        uid = str(uid)
        amt = float(amt)

        data["users"][uid]["approved"] = True
        # Set next payout date
        data["users"][uid]["next_payout"] = (datetime.now() + timedelta(days=30)).strftime("%d-%m-%Y")
        
        # Referral Bonus
        ref_by = data["users"][uid].get("ref_by")
        if ref_by:
            data["users"][ref_by]["ref_earn"] += amt * 0.01

        save_data(data)

        bot.send_message(uid, "✅ Your investment has been approved!\nNext payout date: "
                         + data["users"][uid]["next_payout"])
        bot.send_message(message.chat.id, "Approved successfully.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

# Portfolio
@bot.message_handler(commands=["portfolio"])
def portfolio(message):
    user = data["users"].get(str(message.from_user.id))
    if not user or not user.get("approved"):
        bot.send_message(message.chat.id, "You have no active investments.")
        return

    text = (
        f"💼 *My Portfolio*\n\n"
        f"Plan: {user['plan']}\n"
        f"Invested: {user['amount']} USDT\n"
        f"Next Payout: {user['next_payout']}\n"
        f"Referral Earnings: {user['ref_earn']} USDT"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

bot.polling(none_stop=True)
