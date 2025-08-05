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

# ID канала для отзывов
FEEDBACK_CHANNEL_ID = "-1002394099637"  # Замените на реальный ID

# Кэш для хранения отзывов
feedback_cache = []

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛠 Проблема с товаром"), KeyboardButton("📦 Пришёл не тот товар")],
        [KeyboardButton("❓ Задать вопрос")],
        [KeyboardButton("📝 Оставить отзыв"), KeyboardButton("👀 Посмотреть отзывы")],
        [KeyboardButton("💸 Кэшбэк за отзыв")]
    ], resize_keyboard=True)

def get_rating_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("⭐️ 1"), KeyboardButton("⭐️ 2"), KeyboardButton("⭐️ 3")],
        [KeyboardButton("⭐️ 4"), KeyboardButton("⭐️ 5"), KeyboardButton("🚫 Без оценки")]
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

async def show_feedbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем последние сообщения из канала
        messages = []
        try:
            async for msg in context.bot.get_chat_history(chat_id=FEEDBACK_CHANNEL_ID, limit=5):
                if msg.text:
                    messages.append(msg.text)
        except Exception as e:
            logger.error(f"Ошибка при чтении истории канала: {e}")
        
        if messages:
            # Формируем сообщение из канала
            feedbacks_text = "🌟 Последние отзывы:\n\n"
            for i, msg in enumerate(messages, 1):
                parts = msg.split('\n')
                feedback = parts[0]  # Первая строка - текст отзыва
                
                # Ищем строку с оценкой
                rating_line = ""
                for part in parts:
                    if "⭐️" in part or "🚫" in part:
                        rating_line = part
                        break
                
                feedbacks_text += f"{i}. {feedback}\n"
                if rating_line:
                    feedbacks_text += f"{rating_line}\n"
                feedbacks_text += "\n"
            
            await update.message.reply_text(feedbacks_text)
            return
        elif feedback_cache:
            # Если канал недоступен, используем кэш
            last_five = feedback_cache[-5:][::-1]
            cache_text = "🌟 Последние отзывы:\n\n"
            for i, fb in enumerate(last_five, 1):
                parts = fb.split('\n')
                cache_text += f"{i}. {parts[0]}\n"
                if len(parts) > 1:
                    cache_text += f"{parts[1]}\n"
                cache_text += "\n"
            await update.message.reply_text(cache_text)
            return
        else:
            await update.message.reply_text("Пока нет отзывов. Будьте первым!")
            return
            
    except Exception as e:
        logger.error(f"Ошибка показа отзывов: {e}")
        await update.message.reply_text(
            "Примеры отзывов:\n\n"
            "1. Отличный товар! Быстрая доставка\n⭐️⭐️⭐️⭐️⭐️\n\n"
            "2. Качество на высоте\n⭐️⭐️⭐️⭐️\n\n"
            "3. Недоволен упаковкой\n⭐️⭐️⭐️\n\n"
            "4. Продукт супер\n⭐️⭐️⭐️⭐️\n\n"
            "5. Всё понравилось\n🚫 Без оценки"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    
    # Показ последних отзывов
    if text == "👀 Посмотреть отзывы":
        await show_feedbacks(update, context)
        return
    
    # Обработка кнопок поддержки с разными сообщениями
    support_messages = {
        "🛠 Проблема с товаром": (
            "🛠 <b>Проблема с товаром</b>\n\n"
            "Опишите проблему с товаром и укажите номер заказа. Мы постараемся решить ваш вопрос как можно скорее.\n\n"
            "<i>Вы можете прикрепить фото для наглядности.</i>"
        ),
        "📦 Пришёл не тот товар": (
            "📦 <b>Пришёл не тот товар</b>\n\n"
            "Укажите номер заказа и опишите, какой товар вы заказывали и какой пришел вместо него. "
            "Мы решим эту проблему в кратчайшие сроки.\n\n"
            "<i>Вы можете прикрепить фото ошибочного товара.</i>"
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
    
    # Обработка обращений в поддержку (Проблемы с товаром, неверный товар, вопросы)
    if 'support_issue' in context.user_data:
        issue_type = context.user_data['support_issue']
        await forward_to_support(update, context, issue_type)
        await update.message.reply_text(
            "✅ Ваше обращение отправлено в поддержку! Мы свяжемся с вами в ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        del context.user_data['support_issue']
        return
    
    # Обработка оставления отзыва
    if text == "📝 Оставить отзыв":
        await update.message.reply_text(
            "Напишите ваш отзыв:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['feedback_state'] = 'awaiting_text'
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
    
    # Обработка текста отзыва
    if context.user_data.get('feedback_state') == 'awaiting_text':
        context.user_data['feedback_text'] = text
        context.user_data['feedback_state'] = 'awaiting_rating'
        await update.message.reply_text(
            "Пожалуйста, оцените товар (или нажмите 'Без оценки'):",
            reply_markup=get_rating_keyboard()
        )
        return
    
    # Обработка оценки
    if context.user_data.get('feedback_state') == 'awaiting_rating':
        rating = None
        if '⭐️' in text:
            try:
                rating = int(text.split()[1])
            except (IndexError, ValueError):
                rating = None
        elif text == "🚫 Без оценки":
            rating = None
        
        # Формируем сообщение для канала
        feedback_text = context.user_data.get('feedback_text', '')
        channel_message = feedback_text
        if rating is not None:
            stars = '⭐️' * rating
            channel_message += f"\n{stars}"
        else:
            channel_message += "\n🚫 Без оценки"
        
        # Отправляем отзыв в канал
        try:
            await context.bot.send_message(
                chat_id=FEEDBACK_CHANNEL_ID,
                text=channel_message
            )
            # Сохраняем в кэш
            feedback_cache.append(channel_message)
            # Держим не более 50 отзывов в кэше
            if len(feedback_cache) > 50:
                feedback_cache.pop(0)
        except Exception as e:
            logger.error(f"Ошибка при отправке в канал: {e}")
            await update.message.reply_text("⚠️ Ошибка при сохранении отзыва. Попробуйте позже.")
            # Сбрасываем состояние
            context.user_data.pop('feedback_state', None)
            context.user_data.pop('feedback_text', None)
            return
        
        # Подтверждение пользователю
        if rating is not None:
            stars = '⭐️' * rating
            await update.message.reply_text(
                f"✅ Спасибо за ваш отзыв и оценку {stars}!",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "✅ Спасибо за ваш отзыв!",
                reply_markup=get_main_keyboard()
            )
        
        # Очищаем состояние
        context.user_data.pop('feedback_state', None)
        context.user_data.pop('feedback_text', None)
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
    
    # Если это обращение в поддержку (проблемы с товаром, неверный товар, вопросы)
    if 'support_issue' in context.user_data:
        issue_type = context.user_data['support_issue']
        await forward_to_support(update, context, issue_type)
        await update.message.reply_text(
            "✅ Ваше обращение отправлено в поддержку! Мы свяжемся с вами в ближайшее время.",
            reply_markup=get_main_keyboard()
        )
        del context.user_data['support_issue']
        return
    
    # Если это отзыв с фото - не поддерживается
    if context.user_data.get('feedback_state') == 'awaiting_text':
        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте текстовый отзыв. Фото не поддерживаются.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.pop('feedback_state', None)
        return

def main():
    application = Application.builder().token("7748869714:AAFT58Mc0wH9g_x9mbozRRWY_iXPFCdxnHU").build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()