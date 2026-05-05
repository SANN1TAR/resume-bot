import os
import re
import html
import asyncio
import logging
import traceback
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler, PicklePersistence
)
from pdf_gen import generate_pdf

load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN")
WEBHOOK_URL     = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET  = os.getenv("WEBHOOK_SECRET", "changeme-replace-with-random-string")
PORT            = int(os.getenv("PORT", 8443))
DEVELOPER_CHAT_ID = os.getenv("DEVELOPER_CHAT_ID")
DATA_PATH       = os.getenv("DATA_PATH", "bot_data.pkl")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

(NAME, AGE, CITY, PHONE, EMAIL, TARGET_JOB, EXPERIENCE, SKILLS, EDUCATION, ABOUT, CONFIRM) = range(11)

QUESTIONS = {
    NAME:       "Как тебя зовут? (ФИО полностью)",
    AGE:        "Сколько лет?",
    CITY:       "Город проживания?",
    PHONE:      "Номер телефона (формат: +7XXXXXXXXXX):",
    EMAIL:      "Электронная почта:",
    TARGET_JOB: "На какую должность претендуешь?",
    EXPERIENCE: "Опыт работы (кратко, или «нет опыта»):",
    SKILLS:     "Навыки и умения (через запятую):",
    EDUCATION:  "Образование (учебное заведение, год окончания):",
    ABOUT:      "Пару слов о себе — кто ты и чего хочешь достичь:",
}

STEP_KEYS = ["name", "age", "city", "phone", "email", "target_job", "experience", "skills", "education", "about"]
TOTAL_STEPS = len(STEP_KEYS)


def _q(step: int) -> str:
    """Format question with step counter: [N/10] question"""
    return f"[{step + 1}/{TOTAL_STEPS}] {QUESTIONS[step]}"


async def safe_send(func, *args, retries=5, **kwargs):
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except (TimedOut, NetworkError):
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                raise


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = NAME
    await update.message.reply_text(
        "Здарова! Я сделаю тебе резюме за 2 минуты.\n"
        "Отвечай на вопросы — получишь готовый PDF.\n\n"
        "Команды: /cancel — отмена  |  /restart — начать заново\n\n"
        + _q(NAME)
    )
    return NAME


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = NAME
    await update.message.reply_text("Начинаем заново!\n\n" + _q(NAME))
    return NAME


async def handle_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step", NAME)
    context.user_data[STEP_KEYS[step]] = update.message.text.strip()
    next_step = step + 1

    if next_step < TOTAL_STEPS:
        context.user_data["step"] = next_step
        await safe_send(update.message.reply_text, _q(next_step))
        return next_step
    else:
        await _show_confirmation(update, context)
        return CONFIRM


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or not (14 <= int(text) <= 80):
        await update.message.reply_text("Введи возраст цифрами (от 14 до 80). Попробуй ещё раз:")
        return AGE
    context.user_data["age"] = text
    context.user_data["step"] = CITY
    await safe_send(update.message.reply_text, _q(CITY))
    return CITY


async def invalid_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Неверный формат. Нужен: +7XXXXXXXXXX (11 цифр). Попробуй ещё:"
    )
    return PHONE


async def invalid_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Похоже, это не email. Пример: ivan@mail.ru"
    )
    return EMAIL


async def _show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    lines = [
        f"ФИО: {d.get('name', '—')}",
        f"Возраст: {d.get('age', '—')}",
        f"Город: {d.get('city', '—')}",
        f"Телефон: {d.get('phone', '—')}",
        f"Email: {d.get('email', '—')}",
        f"Должность: {d.get('target_job', '—')}",
        f"Опыт: {d.get('experience', '—')}",
        f"Навыки: {d.get('skills', '—')}",
        f"Образование: {d.get('education', '—')}",
        f"О себе: {d.get('about', '—')}",
    ]
    summary = "Проверь данные перед генерацией:\n\n" + "\n".join(lines)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Генерировать PDF", callback_data="confirm"),
        InlineKeyboardButton("🔄 Начать заново", callback_data="restart"),
    ]])
    await safe_send(update.message.reply_text, summary, reply_markup=keyboard)


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm":
        await query.edit_message_text("Секунду, генерирую PDF...")
        data = {k: context.user_data.get(k, "") for k in STEP_KEYS}
        pdf_path = generate_pdf(data)
        with open(pdf_path, "rb") as f:
            await safe_send(
                context.bot.send_document,
                chat_id=query.message.chat_id,
                document=f,
                filename="resume.pdf",
                caption="Готово! Твоё резюме. Удачи на собесе."
            )
        os.remove(pdf_path)
        context.user_data.clear()
        return ConversationHandler.END
    else:
        context.user_data.clear()
        context.user_data["step"] = NAME
        await query.edit_message_text("Начинаем заново!")
        await safe_send(
            context.bot.send_message,
            chat_id=query.message.chat_id,
            text=_q(NAME)
        )
        return NAME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Отменено. Напиши /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Что-то пошло не так. Напиши /cancel и начни заново."
        )
    if DEVELOPER_CHAT_ID:
        tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        msg = f"<b>Ошибка в боте</b>\n<pre>{html.escape(tb[-3000:])}</pre>"
        try:
            await context.bot.send_message(
                chat_id=int(DEVELOPER_CHAT_ID),
                text=msg,
                parse_mode="HTML"
            )
        except Exception:
            pass


def main():
    persistence = PicklePersistence(filepath=DATA_PATH)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("restart", restart),
        ],
        states={
            NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            AGE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            CITY:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            PHONE: [
                MessageHandler(filters.Regex(r"^\+7\d{10}$") & ~filters.COMMAND, handle_step),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_phone),
            ],
            EMAIL: [
                MessageHandler(filters.Regex(EMAIL_RE) & ~filters.COMMAND, handle_step),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_email),
            ],
            TARGET_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            SKILLS:     [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            EDUCATION:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            ABOUT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            CONFIRM:    [CallbackQueryHandler(handle_confirmation)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("restart", restart),
        ],
        name="resume_conv",
        persistent=True,
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)

    if WEBHOOK_URL:
        logger.info("Starting in webhook mode on port %s", PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=WEBHOOK_SECRET,
            webhook_url=WEBHOOK_URL,
        )
    else:
        logger.info("Starting in polling mode")
        app.run_polling()


if __name__ == "__main__":
    main()
