"""MAYDON long-polling Telegram worker. Deploy as ONE persistent worker."""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from contacts import verified_contact_phone
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
logging.basicConfig(level=logging.INFO)
dp=Dispatcher()

def web_app_url(**params):
    url=urlsplit(os.environ['MINI_APP_URL'])
    query=dict(parse_qsl(url.query))
    query.update(v='20261110-owner-contact', **params)
    return urlunsplit((url.scheme,url.netloc,url.path or '/',urlencode(query),''))

def database():
    return psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row)

@dp.message(CommandStart())
async def start(message: Message):
    url=web_app_url()
    payload=(message.text or '').split(maxsplit=1)
    if len(payload)==2 and payload[1].startswith('phone_'):
        parts=payload[1][6:].split('_')
        if parts[0].isdigit() and len(parts[0])<=18:
            slot=int(parts[1]) if len(parts)==2 and parts[1].isdigit() and len(parts[1])<=12 else None
            with database() as conn:
                conn.execute('INSERT INTO contact_return_links(telegram_id,venue_id,slot) VALUES (%s,%s,%s) ON CONFLICT (telegram_id) DO UPDATE SET venue_id=EXCLUDED.venue_id,slot=EXCLUDED.slot,created_at=NOW()', (message.from_user.id,int(parts[0]),slot))
        await request_phone(message)
        return
    if len(payload)==2 and payload[1].startswith('book_'):
        parts=payload[1][5:].split('_')
        venue_id=parts[0]
        if venue_id.isdigit():
            arguments={'venue':venue_id}
            if len(parts)==2 and parts[1].isdigit():
                arguments['slot']=parts[1]
            url=web_app_url(**arguments)
    keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏟 MAYDONni ochish',web_app=WebAppInfo(url=url))]])
    await message.answer('MAYDON — Namangan shahridagi futbol, stol tennisi va bilyard joylari.',reply_markup=keyboard)

@dp.message(Command('phone'))
async def request_phone(message: Message):
    if message.chat.type != 'private':
        return
    keyboard=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='📞 Oʻz raqamimni ulashish',request_contact=True)]],resize_keyboard=True,one_time_keyboard=True)
    await message.answer('Bron qilish uchun oʻz Telegram telefon raqamingizni ulashing. Raqam bron qilingan maydon egasiga aloqa uchun beriladi.',reply_markup=keyboard)

@dp.message(F.contact)
async def receive_contact(message: Message):
    if message.chat.type != 'private' or not message.from_user:
        return
    try:
        phone=verified_contact_phone(message.from_user.id,message.contact.user_id,message.contact.phone_number)
    except ValueError:
        await message.answer('Boshqa odamning raqami qabul qilinmaydi. “Oʻz raqamimni ulashish” tugmasini bosing.')
        return
    with database() as conn:
        conn.execute('INSERT INTO telegram_contacts(telegram_id,phone) VALUES (%s,%s) ON CONFLICT (telegram_id) DO UPDATE SET phone=EXCLUDED.phone,shared_at=NOW()', (message.from_user.id,phone))
        target=conn.execute('DELETE FROM contact_return_links WHERE telegram_id=%s RETURNING venue_id,slot,created_at', (message.from_user.id,)).fetchone()
    params={}
    if target and target['created_at']>datetime.now(timezone.utc)-timedelta(minutes=30):
        params={'venue':str(target['venue_id'])}
        if target['slot']:params['slot']=str(target['slot'])
    await message.answer('✓ Telefon raqamingiz saqlandi. Endi bronni davom ettirishingiz mumkin.',reply_markup=ReplyKeyboardRemove())
    await message.answer('MAYDONga qaytish:',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Bronni davom ettirish',web_app=WebAppInfo(url=web_app_url(**params)))]]))

@dp.message(Command('owner'))
async def owner(message: Message):
    keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏟 Maydon qoʻshish / mening maydonlarim',web_app=WebAppInfo(url=web_app_url(owner='1')))]])
    await message.answer('Oʻz maydoningizni rasmlar va xaritadagi joylashuvi bilan yuboring.',reply_markup=keyboard)
    with database() as conn:
        rows=conn.execute('SELECT b.id,v.name,b.start_at,b.customer_phone FROM bookings b JOIN venues v ON v.id=b.venue_id WHERE v.owner_telegram_id=%s AND b.status=%s ORDER BY b.start_at LIMIT 10',(message.from_user.id,'pending')).fetchall()
    if not rows:
        await message.answer('Tasdiqlashni kutayotgan bronlar yo‘q.');return
    for r in rows:
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Tasdiqlash',callback_data=f'booking:confirmed:{r["id"]}'),InlineKeyboardButton(text='❌ Rad etish',callback_data=f'booking:rejected:{r["id"]}')]])
        local_time=r['start_at'].astimezone(timezone(timedelta(hours=5))).strftime('%d.%m.%Y · %H:%M')
        phone=r['customer_phone'] or 'Eski bron — raqam saqlanmagan'
        await message.answer(f'#{r["id"]} {r["name"]}\n🕒 {local_time} (Oʻzbekiston vaqti, UTC+5)\n📞 Mijoz: {phone}',reply_markup=keyboard)

@dp.message(Command('admin'))
async def admin(message: Message):
    if str(message.from_user.id)!=os.environ.get('ADMIN_TELEGRAM_ID'):
        await message.answer('Ruxsat yo‘q.');return
    with database() as conn:
        rows=conn.execute("SELECT id,name,address FROM venues WHERE status='pending' AND deleted_at IS NULL ORDER BY id LIMIT 10").fetchall()
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
                row=conn.execute("UPDATE venues SET status=%s WHERE id=%s AND status='pending' AND deleted_at IS NULL RETURNING owner_telegram_id,name",(decision,item_id)).fetchone()
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
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text='MAYDONni ochish',web_app=WebAppInfo(url=web_app_url())))
    worker=asyncio.create_task(deliver_notifications(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        await bot.session.close()

if __name__=='__main__':
    asyncio.run(main())
