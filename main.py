import asyncio
import logging
import datetime
import math
from pyquotex.stable_api import Quotex
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, or_f
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# --- الإعدادات الأساسية ---
logging.basicConfig(level=logging.WARNING)
BOT_TOKEN = "8039189219:AAHXEhdpOhZiqEgCpYAf1OpU6OtuWpke27k"
CHAT_ID = "5629204305"
QUOTEX_EMAIL = "moneycoinwep@gmail.com"
QUOTEX_PASS = "qwer4321"

# قائمة الـ 10 أزواج الذهبية ذات أعلى دقة
ASSET_LIST = [
    "USDCHF", "EURUSD", "AUDUSD", "EURJPY", "USDJPY",
    "NZDUSD", "USDCAD", "GBPUSD", "GBPJPY", "EURGBP"
]

session = AiohttpSession()
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

class AssetStates(StatesGroup):
    waiting_for_pair = State()
    waiting_for_next_stake = State()

class FortressEngine:
    def __init__(self):
        self.operator = "MOUAD JENNAH"
        self.client = None
        self.is_connected = False
        self.is_running = False
        self.is_trading = False
        self.account_type = "PRACTICE" 
        self.current_asset = "EURUSD"
        self.fixed_stake = 1
        self.inverse_mode = True 
        self.martingale_list = [1, 2, 4, 8, 16, 32]
        self.m_index = 0
        self.market_condition = "Unknown"
        self.consecutive_losses = 0

    async def connect(self):
        try:
            if self.client:
                try: await self.client.close()
                except: pass
            self.client = Quotex(email=QUOTEX_EMAIL, password=QUOTEX_PASS)
            check, _ = await self.client.connect()
            if check:
                self.is_connected = True
                await self.client.change_account(self.account_type)
                return True
            return False
        except Exception as e:
            logging.error(f"Connection Error: {e}")
            return False

    async def analyze_market_depth(self, asset):
        try:
            candles = await self.client.get_candles(asset, 0, 15, 60)
            if not candles: return "Low Data"
            diffs = [abs(float(c['high']) - float(c['low'])) for c in candles]
            avg_volatility = sum(diffs) / len(diffs)
            bodies = [abs(float(c['open']) - float(c['close'])) for c in candles]
            avg_body = sum(bodies) / len(bodies)
            if avg_body < (avg_volatility * 0.2):
                return "Sideways"
            elif bodies[-1] > (avg_body * 3):
                return "News/Breakout"
            else:
                return "Healthy"
        except: return "Error"

    async def is_breakout_danger(self, asset):
        try:
            candles = await self.client.get_candles(asset, 0, 5, 60)
            if not candles: return False
            last_candle = candles[-1]
            body_size = abs(float(last_candle['open']) - float(last_candle['close']))
            avg_body = sum(abs(float(c['open']) - float(c['close'])) for c in candles[:-1]) / 4
            return body_size > (avg_body * 2.5)
        except: return False

    async def get_fvg_status(self, candles):
        try:
            c1, c2, c3 = candles[-3], candles[-2], candles[-1]
            fvg_up = float(c1['high']) < float(c3['low'])
            fvg_down = float(c1['low']) > float(c3['high'])
            if fvg_up: return "FVG_BULLISH"
            if fvg_down: return "FVG_BEARISH"
            return "Balanced"
        except: return "None"

engine = FortressEngine()

def get_lightning_signal(candles):
    try:
        if len(candles) < 20: return None
        closes = [float(c['close']) for c in candles]
        
        # 1. RSI (7)
        gains, losses = [], []
        for i in range(1, 8):
            diff = closes[-i] - closes[-(i+1)]
            if diff > 0: gains.append(diff)
            else: losses.append(abs(diff))
        avg_gain = sum(gains) / 7 if gains else 0
        avg_loss = sum(losses) / 7 if losses else 0
        rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))
        
        # 2. Bollinger Bands (20, 2)
        sma = sum(closes[-20:]) / 20
        variance = sum([((x - sma) ** 2) for x in closes[-20:]]) / 20
        std_dev = math.sqrt(variance)
        upper_band = sma + (std_dev * 2)
        lower_band = sma - (std_dev * 2)
        
        # 3. FVG Check
        c1_h, c3_l = float(candles[-3]['high']), float(candles[-1]['low'])
        c1_l, c3_h = float(candles[-3]['low']), float(candles[-1]['high'])
        
        last_close = closes[-1]
        raw_signal = None
        
        if rsi > 70 and last_close >= (upper_band * 0.99) and c1_l > c3_h:
            raw_signal = "call" 
        elif rsi < 30 and last_close <= (lower_band * 1.01) and c1_h < c3_l:
            raw_signal = "put"
            
        if not raw_signal: return None
        if engine.inverse_mode:
            return "put" if raw_signal == "call" else "call"
        return raw_signal
    except: return None

# --- الأوامر البرمجية ---

@dp.message(F.text == "🔄 تبديل نوع الحساب")
async def toggle_account(m: types.Message):
    engine.account_type = "REAL" if engine.account_type == "PRACTICE" else "PRACTICE"
    if engine.is_connected:
        await engine.client.change_account(engine.account_type)
    await m.answer(f"✅ تم تحويل الحساب إلى: **{engine.account_type}**")

@dp.message(F.text == "💰 نظام المضاعفة")
async def toggle_martingale(m: types.Message):
    kb = ReplyKeyboardBuilder()
    for val in engine.martingale_list:
        kb.add(types.KeyboardButton(text=f"استخدام {val}$"))
    kb.adjust(2)
    kb.row(types.KeyboardButton(text="🔙 عودة"))
    await m.answer("اختر مبلغ الصفقة للمنافسة:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text.startswith("استخدام "))
async def set_stake(m: types.Message, state: FSMContext):
    try:
        val = int(m.text.split(" ")[1].replace("$", ""))
        engine.fixed_stake = val
        await m.answer(f"🎯 تم الضبط: **{val}$**\nجاري مراقبة الـ 10 أزواج الذهبية (FVG + Rebalancing)...")
        engine.is_running = True
        asyncio.create_task(execution_loop())
    except: pass

@dp.message(F.text == "🔄 تبديل الوضع (العكس)")
async def toggle_inverse(m: types.Message):
    engine.inverse_mode = not engine.inverse_mode
    status = "مفعل (نحن أذكياء)" if engine.inverse_mode else "معطل"
    await m.answer(f"⚙️ وضع العكس الآن: **{status}**")

@dp.message(F.text == "⚙️ تغيير الزوج")
async def change_pair(m: types.Message, state: FSMContext):
    await m.answer("أرسل اسم الزوج (مثل USDJPY)")
    await state.set_state(AssetStates.waiting_for_pair)

@dp.message(AssetStates.waiting_for_pair)
async def set_pair(m: types.Message, state: FSMContext):
    engine.current_asset = m.text.upper().strip()
    await state.clear()
    await m.answer(f"✅ الزوج اليدوي الحالي: `{engine.current_asset}`")

@dp.message(F.text == "👤 الحساب")
async def account_info(m: types.Message):
    try:
        balance = await engine.client.get_balance()
        await m.answer(f"👤 المشغل: {engine.operator}\n💰 الرصيد: `{balance}`\n🛠 الحالة: {engine.market_condition}")
    except: await m.answer("⚠️ يرجى التأكد من الاتصال أولاً")

async def execution_loop():
    if not engine.is_running: return
    await bot.send_message(CHAT_ID, "🚀 **V7 ULTIMATE MATRIX**\nبدأ المسح الذكي لـ 10 أزواج...")
    
    while engine.is_running:
        if not engine.client or not engine.is_connected:
            await engine.connect(); await asyncio.sleep(5); continue
        
        try:
            # مسح الـ 10 أزواج بالتوالي للبحث عن أفضل فرصة
            for asset in ASSET_LIST:
                if not engine.is_running: break
                candles = await engine.client.get_candles(asset, 0, 30, 30)
                if candles and not engine.is_trading:
                    signal = get_lightning_signal(candles)
                    if signal:
                        now = datetime.datetime.now()
                        wait_time = 60 - now.second
                        if wait_time > 5:
                            await asyncio.sleep(wait_time - 5)
                            is_danger = await engine.is_breakout_danger(asset)
                            if is_danger: continue 
                            
                            await bot.send_message(CHAT_ID, f"⚖️ فرصة ذهبية في {asset}\nالسوق ينسحب لسد الفجوة. دخول {signal.upper()}")
                            await asyncio.sleep(5)
                        
                        status, info = await engine.client.buy(engine.fixed_stake, asset, signal, 60)
                        if status:
                            engine.is_trading = True
                            await bot.send_message(CHAT_ID, f"🎯 صيد ثمين في {asset} بمبلغ {engine.fixed_stake}$")
                            await asyncio.sleep(70)
                            res_candles = await engine.client.get_candles(asset, 0, 10, 5)
                            open_p, close_p = float(res_candles[-1]['open']), float(res_candles[-1]['close'])
                            is_win = (signal == "call" and close_p > open_p) or (signal == "put" and close_p < open_p)
                            
                            kb = ReplyKeyboardBuilder()
                            for val in [5, 10, 25, 50, 100]: kb.add(types.KeyboardButton(text=f"استخدام {val}$"))
                            kb.adjust(3)
                            
                            msg = f"🏁 **{asset} | {'✅ ربح' if is_win else '❌ خسارة'}**"
                            await bot.send_message(CHAT_ID, msg, reply_markup=kb.as_markup(resize_keyboard=True))
                            
                            engine.is_trading = False
                            # في حال الخسارة، البوت سيستمر في البحث في الأزواج الأخرى للتعويض
                            break 
                await asyncio.sleep(0.5) # فاصل زمني بين فحص كل زوج
        except Exception as e: logging.error(f"Error: {e}")
        await asyncio.sleep(1)

@dp.message(F.text == "⚡ تشغيل")
async def start_eng(m: types.Message):
    if not engine.is_running:
        engine.is_running = True
        asyncio.create_task(execution_loop())

@dp.message(F.text == "🛑 إيقاف")
async def stop_eng(m: types.Message):
    engine.is_running = False
    await m.answer("🛑 توقف المحرك.")

@dp.message(or_f(F.text == "🔙 عودة", Command("start")))
async def start(m: types.Message):
    if not engine.is_connected: await engine.connect()
    kb = ReplyKeyboardBuilder()
    kb.row(types.KeyboardButton(text="⚡ تشغيل"), types.KeyboardButton(text="🛑 إيقاف"))
    kb.row(types.KeyboardButton(text="🔄 تبديل الوضع (العكس)"), types.KeyboardButton(text="⚙️ تغيير الزوج"))
    kb.row(types.KeyboardButton(text="🔄 تبديل نوع الحساب"), types.KeyboardButton(text="💰 نظام المضاعفة"))
    kb.row(types.KeyboardButton(text="👤 الحساب"))
    await m.answer(f"🛡️ **V7 MULTI-ASSET MODE**\nتحليل الـ 10 الكبار + FVG Algo ⚖️", reply_markup=kb.as_markup(resize_keyboard=True))

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
