from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackQueryHandler, ConversationHandler
)
import sqlite3
from datetime import datetime, timedelta
import os
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config from environment ---
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]            # required
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")          # e.g. https://your-app.up.railway.app
PORT = int(os.environ.get("PORT", 8443))             # Railway sets PORT automatically
DB_PATH = os.environ.get("DB_PATH", "unit_calendar.db")

# Database setup
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute(
    "CREATE TABLE IF NOT EXISTS events ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "title TEXT, date TEXT, time TEXT)"
)
conn.commit()

# Conversation states
TITLE, DATE, TIME, CONFIRM = range(4)


# --- Core Commands ---
def addevent(update, context):
    try:
        title, date, time = context.args[0], context.args[1], context.args[2]
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")
        c.execute("INSERT INTO events (title, date, time) VALUES (?, ?, ?)", (title, date, time))
        conn.commit()
        update.message.reply_text(f"Event '{title}' added on {date} at {time}.")
    except ValueError:
        update.message.reply_text("Invalid date or time format. Usage: /addevent <title> <YYYY-MM-DD> <HH:MM>")
    except IndexError:
        update.message.reply_text("Usage: /addevent <title> <YYYY-MM-DD> <HH:MM>")
    except Exception as e:
        update.message.reply_text(f"Error adding event: {str(e)}")


def updateevent(update, context):
    try:
        old_title, new_title, new_date, new_time = context.args
        datetime.strptime(new_date, "%Y-%m-%d")
        datetime.strptime(new_time, "%H:%M")
        c.execute(
            "UPDATE events SET title=?, date=?, time=? WHERE title=?",
            (new_title, new_date, new_time, old_title),
        )
        conn.commit()
        if c.rowcount == 0:
            update.message.reply_text(f"No event found with title '{old_title}'.")
        else:
            update.message.reply_text(
                f"Event '{old_title}' updated to '{new_title}' on {new_date} at {new_time}."
            )
    except IndexError:
        update.message.reply_text("Usage: /updateevent <old_title> <new_title> <YYYY-MM-DD> <HH:MM>")
    except ValueError:
        update.message.reply_text("Invalid date or time format. Usage: /updateevent <old_title> <new_title> <YYYY-MM-DD> <HH:MM>")
    except Exception as e:
        update.message.reply_text(f"Error updating event: {str(e)}")


def deleteevent(update, context):
    try:
        title = context.args[0]
        c.execute("DELETE FROM events WHERE title=?", (title,))
        conn.commit()
        if c.rowcount == 0:
            update.message.reply_text(f"No event found with title '{title}'.")
        else:
            update.message.reply_text(f"Event '{title}' deleted.")
    except IndexError:
        update.message.reply_text("Usage: /deleteevent <title>")
    except Exception as e:
        update.message.reply_text(f"Error deleting event: {str(e)}")


def week(update, context):
    try:
        now = datetime.now()
        week_later = now + timedelta(days=7)
        c.execute("SELECT title, date, time FROM events")
        events = c.fetchall()
        upcoming = [
            f"{t} on {d} at {tm}"
            for t, d, tm in events
            if now <= datetime.strptime(f"{d} {tm}", "%Y-%m-%d %H:%M") <= week_later
        ]
        if upcoming:
            update.message.reply_text("Upcoming events:\n" + "\n".join(upcoming))
        else:
            update.message.reply_text("No events this week.")
    except Exception as e:
        update.message.reply_text(f"Error fetching events: {str(e)}")


def find(update, context):
    try:
        keyword = " ".join(context.args).lower()
        c.execute("SELECT title, date, time FROM events")
        events = c.fetchall()
        matches = [f"{t} on {d} at {tm}" for t, d, tm in events if keyword in t.lower()]
        if matches:
            update.message.reply_text("\U0001F50E Matching events:\n" + "\n".join(matches))
        else:
            update.message.reply_text(f"No events found containing '{keyword}'.")
    except Exception as e:
        update.message.reply_text(f"Error searching events: {str(e)}")


# --- Interactive Help Menu ---
def hello(update, context):
    keyboard = [
        [InlineKeyboardButton("\u2795 Quick Add Event", callback_data="quickadd")],
        [InlineKeyboardButton("\U0001F4C5 Weekly Events", callback_data="week_run")],
        [InlineKeyboardButton("\U0001F4C6 List All Events", callback_data="list_all")],
        [InlineKeyboardButton("\U0001F50E Search Events", callback_data="search_prompt")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("\U0001F44B Hi! Choose an option:", reply_markup=reply_markup)


def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "quickadd":
        query.edit_message_text("Please enter the event title:")
        return TITLE
    elif query.data == "week_run":
        try:
            now = datetime.now()
            week_later = now + timedelta(days=7)
            c.execute("SELECT title, date, time FROM events")
            events = c.fetchall()
            upcoming = [
                f"{t} on {d} at {tm}"
                for t, d, tm in events
                if now <= datetime.strptime(f"{d} {tm}", "%Y-%m-%d %H:%M") <= week_later
            ]
            if upcoming:
                query.edit_message_text("Upcoming events:\n" + "\n".join(upcoming))
            else:
                query.edit_message_text("No events this week.")
        except Exception as e:
            query.edit_message_text(f"Error fetching events: {str(e)}")
        return ConversationHandler.END
    elif query.data == "list_all":
        try:
            c.execute("SELECT title, date, time FROM events ORDER BY date, time")
            events = c.fetchall()
            if events:
                all_events = [f"{t} on {d} at {tm}" for t, d, tm in events]
                query.edit_message_text("\U0001F4C5 All Scheduled Events:\n" + "\n".join(all_events))
            else:
                query.edit_message_text("No events scheduled yet.")
        except Exception as e:
            query.edit_message_text(f"Error fetching events: {str(e)}")
        return ConversationHandler.END
    elif query.data == "search_prompt":
        query.edit_message_text("\U0001F50E Please type: /find <keyword>")
        return ConversationHandler.END


# --- Quick Add Flow ---
def get_title(update, context):
    context.user_data["title"] = update.message.text
    update.message.reply_text("Got it! Now enter the date (YYYY-MM-DD):")
    return DATE


def get_date(update, context):
    try:
        date_input = update.message.text
        datetime.strptime(date_input, "%Y-%m-%d")
        context.user_data["date"] = date_input
        update.message.reply_text("Great! Now enter the time (HH:MM):")
        return TIME
    except ValueError:
        update.message.reply_text("Invalid date format. Please enter date as YYYY-MM-DD:")
        return DATE


def get_time(update, context):
    try:
        time_input = update.message.text
        datetime.strptime(time_input, "%H:%M")
        context.user_data["time"] = time_input
        title = context.user_data["title"]
        date = context.user_data["date"]
        time = context.user_data["time"]

        keyboard = [
            [InlineKeyboardButton("\u2705 Confirm", callback_data="confirm_event")],
            [InlineKeyboardButton("\u274C Cancel", callback_data="cancel_event")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"\U0001F4CC Event Preview:\n\nTitle: {title}\nDate: {date}\nTime: {time}\n\nDo you want to save this?",
            reply_markup=reply_markup,
        )
        return CONFIRM
    except ValueError:
        update.message.reply_text("Invalid time format. Please enter time as HH:MM:")
        return TIME


def confirm(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "confirm_event":
        try:
            title = context.user_data["title"]
            date = context.user_data["date"]
            time = context.user_data["time"]
            c.execute("INSERT INTO events (title, date, time) VALUES (?, ?, ?)", (title, date, time))
            conn.commit()
            query.edit_message_text(f"\u2705 Event '{title}' added on {date} at {time}.")
        except Exception as e:
            query.edit_message_text(f"Error saving event: {str(e)}")
    elif query.data == "cancel_event":
        query.edit_message_text("\u274C Event creation cancelled.")
    return ConversationHandler.END


# --- Wire handlers once at import time so both polling and webhook paths can reuse them ---
def _register_handlers(dispatcher):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern="^quickadd$")],
        states={
            TITLE: [MessageHandler(Filters.text & ~Filters.command, get_title)],
            DATE: [MessageHandler(Filters.text & ~Filters.command, get_date)],
            TIME: [MessageHandler(Filters.text & ~Filters.command, get_time)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern="^(confirm|cancel)_event$")],
        },
        fallbacks=[CommandHandler("cancel", confirm)],
        allow_reentry=True,
    )
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(button, pattern="^(week_run|list_all|search_prompt)$"))
    dispatcher.add_handler(CommandHandler("addevent", addevent))
    dispatcher.add_handler(CommandHandler("updateevent", updateevent))
    dispatcher.add_handler(CommandHandler("deleteevent", deleteevent))
    dispatcher.add_handler(CommandHandler("week", week))
    dispatcher.add_handler(CommandHandler("find", find))
    dispatcher.add_handler(CommandHandler("hello", hello))
    dispatcher.add_handler(CommandHandler("help", hello))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r"(?i)^hello$"), hello))


def main():
    updater = Updater(TOKEN, use_context=True)
    _register_handlers(updater.dispatcher)

    if WEBHOOK_URL:
        # Production: webhook mode (used on Railway)
        # PTB v13 has a built-in Tornado-based webhook server, no gunicorn needed.
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}",
        )
        logger.info("Webhook set: %s/%s on port %s", WEBHOOK_URL, TOKEN, PORT)
        updater.idle()
    else:
        # Local dev: polling mode
        logger.info("No WEBHOOK_URL set, falling back to polling.")
        updater.start_polling()
        updater.idle()


if __name__ == "__main__":
    main()
