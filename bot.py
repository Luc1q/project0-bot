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

# ID администратора
ADMIN_ID = 736634954

# Константы для текстов кнопок
PROBLEM_BUTTON = "🛠 Проблема с товаром"
QUESTION_BUTTON = "❓ Задать вопрос"
CASHBACK_BUTTON = "₽ Кэшбэк за отзыв Wildberries"

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton(PROBLEM_BUTTON)],
        [KeyboardButton(QUESTION_BUTTON)],
        [KeyboardButton(CASHBACK_BUTTON)]
    ], resize_keyboard=True)

# Пересылка сообщения администратору
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, issue_type: str):
    user = update.message.from_user
    user_info = f"👤 {user.full_name} "
    if user.username:
        user_info += f"(username: @{user.username}) "
    user_info += f"(ID: {user.id})\n"
    
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Формируем базовое сообщение
    message = (
        f"🚨 НОВОЕ СООБЩЕНИЕ\n"
        f"Тип: {issue_type}\n"
        f"Время: {time_str}\n"
        f"Пользователь:\n{user_info}\n"
    )
    
    # Добавляем контент сообщения
    text_content = update.message.text or update.message.caption
    if text_content:
        message += f"Сообщение:\n{text_content}"
    
    # Отправляем контент администратору
    try:
        # Для фото
        if update.message.photo:
            photo = update.message.photo[-1]
            sent_message = await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=message
            )
        # Для документов
        elif update.message.document:
            document = update.message.document
            sent_message = await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=document.file_id,
                caption=message
            )
        # Для текста
        else:
            sent_message = await context.bot.send_message(
                chat_id=ADMIN_ID, 
                text=message
            )
    except Exception as e:
        logger.error(f"Ошибка при пересылке администратору: {e}")
        return

    # Сохраняем связь сообщения
    context.bot_data.setdefault('admin_messages', {})[sent_message.message_id] = {
        'user_id': user.id,
        'original_message': update.message
    }

# Обработка ответов администратора
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что это администратор
    if update.message.from_user.id != ADMIN_ID:
        return
    
    # Проверяем, что это ответ на сообщение
    if not update.message.reply_to_message:
        return
    
    # Получаем информацию о пересланном сообщении
    replied_message_id = update.message.reply_to_message.message_id
    message_info = context.bot_data.get('admin_messages', {}).get(replied_message_id)
    
    if not message_info:
        await update.message.reply_text("❌ Не удалось найти исходное сообщение пользователя.")
        return
    
    # Отправляем ответ пользователю
    try:
        user_id = message_info['user_id']
        
        # Если администратор ответил текстом
        if update.message.text:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✉️ Ответ от поддержки:\n\n{update.message.text}"
            )
        # Если администратор ответил с фото
        elif update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo.file_id,
                caption=f"✉️ Ответ от поддержки:\n\n{update.message.caption}" if update.message.caption else None
            )
        # Если администратор ответил документом
        elif update.message.document:
            document = update.message.document
            await context.bot.send_document(
                chat_id=user_id,
                document=document.file_id,
                caption=f"✉️ Ответ от поддержки:\n\n{update.message.caption}" if update.message.caption else None
            )
        
        # Подтверждение администратору
        await update.message.reply_text("✅ Ответ успешно отправлен пользователю.")
        
    except Exception as e:
        logger.error(f"Ошибка отправки ответа пользователю: {e}")
        await update.message.reply_text("❌ Не удалось отправить ответ. Возможно, пользователь заблокировал бота.")

# Обработчики сообщений
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать на линию поддержки магазина SUNNE fashion. Выберите подходящий пункт меню:",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Обработка кнопок поддержки
    support_messages = {
        PROBLEM_BUTTON: "Проблема с товаром",
        QUESTION_BUTTON: "Вопрос",
        CASHBACK_BUTTON: "Кэшбэк за отзыв Wildberries"
    }
    
    if text in support_messages:
        context.user_data['issue_type'] = support_messages[text]
        
        # Обработка кнопки кэшбэка
        if text == CASHBACK_BUTTON:
            context.user_data['cashback_state'] = 'awaiting_data'
            # ИСПРАВЛЕННЫЙ ТЕКСТ С ПРАВИЛЬНЫМИ ПЕРЕНОСАМИ СТРОК
            await update.message.reply_text(
                "📸 Пришлите скриншот вашего отзыва и укажите:\n"
                "1. Номер телефона\n"
                "2. ФИО\n"
                "3. Банк или номер карты для перевода\n\n"
                "Пример:\n"
                "Телефон: +79991234567\n"
                "ФИО: Иванов Иван Иванович\n"  # ДОБАВЛЕН ПЕРЕНОС СТРОКИ
                "Карта Банка: 1234 5678 9012 3456",  # ОТДЕЛЬНАЯ СТРОКА
                reply_markup=ReplyKeyboardRemove()
            )
        # Обработка других кнопок
        else:
            await update.message.reply_text(
                "Опишите вашу проблему или вопрос. Вы можете прикрепить фото или документ:",
                reply_markup=ReplyKeyboardRemove()
            )
        return
    
    # Обработка текста для кэшбэка
    if context.user_data.get('cashback_state') == 'awaiting_data':
        await forward_to_admin(update, context, "Кэшбэк за отзыв Wildberries")
        context.user_data.pop('cashback_state', None)
        await update.message.reply_text(
            "✅ Ваш запрос отправлен! Ожидайте обработки.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Обработка обычных сообщений (проблемы/вопросы)
    if 'issue_type' in context.user_data:
        issue_type = context.user_data['issue_type']
        await forward_to_admin(update, context, issue_type)
        await update.message.reply_text(
            "✅ Ваше сообщение отправлено! Мы ответим в самое ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        del context.user_data['issue_type']
        return

# Обработчик медиа-сообщений
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработка медиа для кэшбэка
    if context.user_data.get('cashback_state') == 'awaiting_data':
        await forward_to_admin(update, context, "Кэшбэк за отзыв Wildberries")
        context.user_data.pop('cashback_state', None)
        await update.message.reply_text(
            "✅ Ваш запрос отправлен администратору!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Обработка медиа для обычных сообщений
    if 'issue_type' in context.user_data:
        issue_type = context.user_data['issue_type']
        await forward_to_admin(update, context, issue_type)
        await update.message.reply_text(
            "✅ Ваше сообщение отправлено! Мы ответим в самое ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        del context.user_data['issue_type']
        return

def main():
    application = Application.builder().token("8357794711:AAEGxzXXsJqS4c-Fx64bsAglj_cteNes734").build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик ответов администратора
    admin_reply_filter = filters.Chat(ADMIN_ID) & filters.REPLY
    application.add_handler(MessageHandler(admin_reply_filter, handle_admin_reply))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
