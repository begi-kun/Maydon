"""MAYDON long-polling Telegram worker. Deploy as ONE persistent worker."""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
logging.basicConfig(level=logging.INFO)
dp=Dispatcher()

def database():
    return psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row)

@dp.message(CommandStart())
async def start(message: Message):
    url=os.environ['MINI_APP_URL']
    keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏟 MAYDONni ochish',web_app=WebAppInfo(url=url))]])
    await message.answer('MAYDON — Namangan shahridagi futbol, stol tennisi va bilyard joylari.',reply_markup=keyboard)

@dp.message(Command('owner'))
async def owner(message: Message):
    with database() as conn:
        rows=conn.execute('SELECT b.id,v.name,b.start_at FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE v.owner_telegram_id=%s AND b.status=%s ORDER BY b.start_at LIMIT 10',(message.from_user.id,'pending')).fetchall()
    if not rows:
        await message.answer('Tasdiqlashni kutayotgan bronlar yo‘q.');return
    for r in rows:
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Tasdiqlash',callback_data=f'booking:confirmed:{r["id"]}'),InlineKeyboardButton(text='❌ Rad etish',callback_data=f'booking:rejected:{r["id"]}')]])
        await message.answer(f'#{r["id"]} {r["name"]} — {r["start_at"]}',reply_markup=keyboard)

@dp.message(Command('admin'))
async def admin(message: Message):
    if str(message.from_user.id)!=os.environ.get('ADMIN_TELEGRAM_ID'):
        await message.answer('Ruxsat yo‘q.');return
    with database() as conn:
        rows=conn.execute("SELECT id,name,address FROM venues WHERE status='pending' ORDER BY id LIMIT 10").fetchall()
    if not rows:
        await message.answer('Yangi maydon arizalari yo‘q.');return
    for r in rows:
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Tasdiqlash',callback_data=f'venue:approved:{r["id"]}'),InlineKeyboardButton(text='❌ Rad etish',callback_data=f'venue:rejected:{r["id"]}')]])
        await message.answer(f'#{r["id"]} {r["name"]} — {r["address"]}',reply_markup=keyboard)

@dp.callback_query()
async def decide(call):
    try:
        kind,decision,raw_id=call.data.split(':')
        item_id=int(raw_id)
        if kind=='booking' and decision in ('confirmed','rejected'):
            with database() as conn:
                row=conn.execute("UPDATE bookings SET status=%s WHERE id=%s AND status='pending' AND venue_id IN (SELECT id FROM venues WHERE owner_telegram_id=%s) RETURNING user_telegram_id",(decision,item_id,call.from_user.id)).fetchone()
                if row:
                    conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)',(row['user_telegram_id'],f'📅 Bron #{item_id}: {decision}.'))
        elif kind=='venue' and decision in ('approved','rejected') and str(call.from_user.id)==os.environ.get('ADMIN_TELEGRAM_ID'):
            with database() as conn:
                row=conn.execute("UPDATE venues SET status=%s WHERE id=%s AND status='pending' RETURNING owner_telegram_id,name",(decision,item_id)).fetchone()
                if row:
                    conn.execute('INSERT INTO notifications(recipient_id,body) VALUES (%s,%s)',(row['owner_telegram_id'],f'🏟 {row["name"]}: ariza {decision}.'))
        else:
            await call.answer('Ruxsat yo‘q',show_alert=True);return
        if not row:
            await call.answer('So‘rov topilmadi yoki allaqachon ko‘rib chiqilgan.',show_alert=True);return
        await call.answer('Saqlandi')
        await call.message.edit_reply_markup(reply_markup=None)
    except (ValueError,AttributeError):
        await call.answer('Noto‘g‘ri so‘rov',show_alert=True)

async def deliver_notifications(bot:Bot):
    while True:
        try:
            with database() as conn:
                rows=conn.execute('SELECT id,recipient_id,body FROM notifications WHERE sent_at IS NULL ORDER BY id LIMIT 30').fetchall()
            for r in rows:
                try:
                    await bot.send_message(r['recipient_id'],r['body'])
                    with database() as conn:
                        conn.execute('UPDATE notifications SET sent_at=NOW() WHERE id=%s AND sent_at IS NULL',(r['id'],))
                except Exception as exc:
                    logging.warning('Could not deliver notification %s: %s',r['id'],exc)
        except Exception:
            logging.exception('Notification polling failed')
        await asyncio.sleep(15)

async def main():
    for name in ('BOT_TOKEN','DATABASE_URL','MINI_APP_URL'):
        if not os.getenv(name):raise RuntimeError(f'Missing {name}')
    bot=Bot(os.environ['BOT_TOKEN'])
    worker=asyncio.create_task(deliver_notifications(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        await bot.session.close()

if __name__=='__main__':
    asyncio.run(main())
