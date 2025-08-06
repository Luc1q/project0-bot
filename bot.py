import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# Настройки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ID администратора и службы поддержки
ADMIN_ID = 929334625  # Замените на ваш ID
SUPPORT_ID = 848337587  # Замените на ID службы поддержки

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛠 Проблема с товаром")],
        [KeyboardButton("❓ Задать вопрос")],
        [KeyboardButton("💸 Кэшбэк за отзыв")]
    ], resize_keyboard=True)

# Пересылка сообщения в поддержку
async def forward_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE, issue_type: str):
    user = update.message.from_user
    user_info = f"👤 {user.full_name} "
    if user.username:
        user_info += f"(username: @{user.username}) "
    user_info += f"(ID: {user.id})\n"
    
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    message = (
        f"🚨 НОВОЕ ОБРАЩЕНИЕ\n"
        f"Тип: {issue_type}\n"
        f"Время: {time_str}\n"
        f"Пользователь:\n{user_info}\n"
    )
    
    if update.message.text:
        message += f"Сообщение:\n{update.message.text}"
        await context.bot.send_message(SUPPORT_ID, message)
    elif update.message.photo:
        caption = f"{message}\n{update.message.caption}" if update.message.caption else message
        await context.bot.send_photo(
            SUPPORT_ID, 
            update.message.photo[-1].file_id, 
            caption=caption[:1000]
        )
    elif update.message.document:
        caption = f"{message}\n{update.message.caption}" if update.message.caption else message
        await context.bot.send_document(
            SUPPORT_ID, 
            update.message.document.file_id, 
            caption=caption[:1000]
        )

# Отправка запроса на кэшбэк администратору
async def send_cashback_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_info = f"👤 {user.full_name} "
    if user.username:
        user_info += f"(username: @{user.username}) "
    user_info += f"(ID: {user.id})"
    
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    details = context.user_data.get('cashback_details', 'Не указаны')
    
    message = (
        f"💸 ЗАПРОС КЭШБЭКА\n"
        f"Время: {time_str}\n"
        f"Пользователь: {user_info}\n"
        f"Реквизиты:\n{details}"
    )
    
    try:
        # Отправляем администратору
        if 'cashback_photo' in context.user_data:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=context.user_data['cashback_photo'],
                caption=message
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=message
            )
    except Exception as e:
        logger.error(f"Ошибка отправки кэшбэк-запроса: {e}")

# Обработчики сообщений
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать на линию поддержки магазина SUNNE fashion. Выберите подходящий пункт меню:",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    
    # Обработка кнопок поддержки с разными сообщениями
    support_messages = {
        "🛠 Проблема с товаром": (
            "🛠 <b>Проблема с товаром</b>\n\n"
            "Опишите проблему с товаром и укажите номер заказа. Мы постараемся решить ваш вопрос как можно скорее.\n\n"
            "<i>Вы можете прикрепить фото для наглядности.</i>"
        ),
        "❓ Задать вопрос": (
            "❓ <b>Задать вопрос</b>\n\n"
            "Задайте ваш вопрос, и мы ответим на него в ближайшее время. "
            "Если вопрос касается конкретного заказа, укажите его номер."
        )
    }
    
    if text in support_messages:
        context.user_data['support_issue'] = text
        await update.message.reply_html(
            support_messages[text],
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Обработка обращений в поддержку (Проблемы с товаром, вопросы)
    if 'support_issue' in context.user_data:
        issue_type = context.user_data['support_issue']
        await forward_to_support(update, context, issue_type)
        await update.message.reply_text(
            "✅ Ваше обращение отправлено в поддержку! Мы свяжемся с вами в ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        del context.user_data['support_issue']
        return
    
    # Обработка кнопки кэшбэка (отправляется администратору)
    if text == "💸 Кэшбэк за отзыв":
        context.user_data['cashback_state'] = 'awaiting_photo'
        await update.message.reply_text(
            "📸 Пришлите скриншот вашего отзыва и укажите в подписи:\n"
            "1. Номер телефона\n"
            "2. Банк или номер карты для перевода\n\n"
            "Пример подписи:\n"
            "Телефон: +79991234567\n"
            "Карта Сбербанка: 1234 5678 9012 3456",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Обработка данных для кэшбэка (текстовое описание)
    if context.user_data.get('cashback_state') == 'awaiting_details':
        context.user_data['cashback_details'] = text
        await send_cashback_request(update, context)
        # Сброс состояния
        context.user_data.pop('cashback_state', None)
        context.user_data.pop('cashback_photo', None)
        await update.message.reply_text(
            "✅ Запрос на кэшбэк отправлен администратору! Мы проверим информацию и ответим в ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        return

# Обработчик медиа-сообщений
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработка фото для кэшбэка (отправляется администратору)
    if context.user_data.get('cashback_state') == 'awaiting_photo' and update.message.photo:
        # Сохраняем фото для последующей отправки
        context.user_data['cashback_photo'] = update.message.photo[-1].file_id
        
        # Проверяем наличие подписи с реквизитами
        if update.message.caption:
            context.user_data['cashback_details'] = update.message.caption
            await send_cashback_request(update, context)
            # Сброс состояния
            context.user_data.pop('cashback_state', None)
            context.user_data.pop('cashback_photo', None)
            await update.message.reply_text(
                "✅ Запрос на кэшбэк отправлен администратору! Мы проверим информацию и ответим в ближайшее время.",
                reply_markup=get_main_keyboard()
            )
        else:
            # Если подписи нет - запрашиваем реквизиты отдельно
            context.user_data['cashback_state'] = 'awaiting_details'
            await update.message.reply_text(
                "📝 Теперь укажите реквизиты для перевода в формате:\n"
                "Телефон: +79991234567\n"
                "Карта Сбербанка: 1234 5678 9012 3456"
            )
        return
    
    # Если это обращение в поддержку (проблемы с товаром, вопросы)
    if 'support_issue' in context.user_data:
        issue_type = context.user_data['support_issue']
        await forward_to_support(update, context, issue_type)
        await update.message.reply_text(
            "✅ Ваше обращение отправлено в поддержку! Мы свяжемся с вами в ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        del context.user_data['support_issue']
        return

def main():
    application = Application.builder().token("8357794711:AAEGxzXXsJqS4c-Fx64bsAglj_cteNes734").build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()

