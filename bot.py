# Телеграм-бот для генерации резюме в PDF
# Вход: ответы пользователя на вопросы (ФИО, возраст, опыт и т.д.)
# Выход: готовый PDF файл с резюме

import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from pdf_gen import generate_pdf

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# Шаги диалога
(
    NAME, AGE, CITY, PHONE, EMAIL,
    TARGET_JOB, EXPERIENCE, SKILLS, EDUCATION, ABOUT
) = range(10)

QUESTIONS = {
    NAME:       "Привет! Давай сделаем резюме. Как тебя зовут? (ФИО полностью)",
    AGE:        "Сколько лет?",
    CITY:       "Город проживания?",
    PHONE:      "Номер телефона (формат: +7XXXXXXXXXX):",
    EMAIL:      "Электронная почта:",
    TARGET_JOB: "На какую должность претендуешь?",
    EXPERIENCE: "Опыт работы — напиши кратко. Если нет — так и пиши «нет опыта»:",
    SKILLS:     "Навыки и умения (через запятую):",
    EDUCATION:  "Образование (школа/колледж/вуз, год окончания):",
    ABOUT:      "Пару слов о себе — что ты за человек, что умеешь, чего хочешь:",
}

STEP_KEYS = [
    "name", "age", "city", "phone", "email",
    "target_job", "experience", "skills", "education", "about"
]


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
    await update.message.reply_text(
        "Здарова! Я сделаю тебе резюме за 2 минуты.\n"
        "Отвечай на вопросы — и получишь готовый PDF.\n\n"
        "Для отмены в любой момент — /cancel\n\n"
        + QUESTIONS[NAME]
    )
    return NAME


async def handle_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step", NAME)
    key = STEP_KEYS[step]
    context.user_data[key] = update.message.text.strip()

    next_step = step + 1

    if next_step < len(QUESTIONS):
        context.user_data["step"] = next_step
        await safe_send(update.message.reply_text, QUESTIONS[next_step])
        return next_step
    else:
        await safe_send(update.message.reply_text, "Секунду, генерирую PDF...")
        data = {k: context.user_data.get(k, "") for k in STEP_KEYS}
        pdf_path = generate_pdf(data)
        with open(pdf_path, "rb") as f:
            await safe_send(
                update.message.reply_document,
                document=f,
                filename="resume.pdf",
                caption="Готово! Твоё резюме. Удачи на собесе."
            )
        os.remove(pdf_path)
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Отменено. Напиши /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            AGE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            CITY:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            PHONE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            EMAIL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            TARGET_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            SKILLS:     [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            EDUCATION:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
            ABOUT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    print("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
