# Bronn pilotini olib borish

2026-11-15. Bu hujjat tayyorlangan koddan foydalanish tartibi; pilot o‘tkazilgani yoki production tayyorligi haqidagi hisobot emas.

## Ishga tushirishdan oldin

- Mas’ul shaxs va pilot boshlanish sanasini belgilang. 5–10 maydonni ro‘yxatga oling. Egalar bilan aloqa va taklif yuborish inson tomonidan bajariladi; bu o‘zgarish hech kimga xabar yubormaydi.
- PRODUCTION_CHECKLIST.md talablarini tekshiring: backup restore, monitoring, akkauntlar, maxfiylik/support, rate limits va CI. Ushbu funksiyalarning mahalliy sinovi bu talablarning o‘rnini bosmaydi.
- Deploy tartibi: backend → bot (bitta worker) → frontend. Backend yangi jadvallarni qo‘shadi; eski bron va rasmlar o‘zgarmaydi. Ushbu ish davomida deploy bajarilmagan.
- `ENABLE_RECURRING_BOOKINGS=false` va `ENABLE_AVAILABILITY_ALERTS=false` saqlanadi. Pilot natijalaridan so‘ng takroriy bron uchun API’da birinchi bayroqni yoqing; xabarnomalar uchun API va botda ikkinchi bayroq bir xil bo‘lishi kerak. Bayroq o‘chiq bo‘lsa ham avvalgi obunani ko‘rish/o‘chirish ishlaydi. Yoqish alohida reliz qarori.

## Egalar bilan mashq

1. Telefon yoki joyida olingan bronni jadvalga qo‘lda kiriting; bir soatni qayta band qilib bo‘lmasligini tekshiring.
2. Ish vaqtini tekshiring, ta’mirlash soatini yoping va qayta oching.
3. Mijoz so‘rovini tasdiqlang yoki rad eting. So‘rov va tasdiqlangan bron farqini tushuntiring.
4. Seans tugagach Bronlar va to‘lovlar bo‘limida “Keldi”, “Kelmadi”, “Jadval xatosi” yoki “Noma’lum” natijasini qayd qiling. Qayd o‘zgarishlari bron tarixida qoladi. Qayd qilinmagan seans avtomatik “keldi” deb olinmaydi.
5. To‘lov holati faqat qayd ekanini, pul yechmasligi va qaytarmasligini tushuntiring.

## Har kuni

- Egalar oflayn bronlarni ham kiritganini, kutilayotgan so‘rovlarga javob berganini tekshiring.
- Admin → E’tibor va Xabarlar bo‘limida navbat va yetkazish xatolarini ko‘ring. Telegram xabarni qabul qilishi o‘qilganini anglatmaydi.
- Jadval xatolari va kelmay qolishlarni seans tugagach qayd qiling. Mavjud bo‘lmagan natijani taxmin qilib to‘ldirmang.

## O‘lchovlar

Admin → Pilot → boshlanish sanasi → Hisobotni olish. Hisobot shu sanadan 14 kunni UTC+5 bo‘yicha oladi.

- `discovery_results`: sana/soat, sport, natija soni, tasodifiy sessiya va qidiruv identifikatori. Qidiruv matni, GPS, ism, telefon yoki Telegram initData yuborilmaydi. Natija bir qidiruv uchun bir marta yoziladi; 30 soniyalik avtomatik yangilash hisobni ko‘paytirmaydi. Filtr o‘zgarsa yangi qidiruv hisoblanadi.
- `venue_open`: maydon kartasi, xarita yoki to‘g‘ridan-to‘g‘ri maydon havolasini ochish. Maydon ID’si ham yoziladi.
- `booking_request_created`: faqat server muvaffaqiyatli bron yaratganda shu tranzaksiyada yoziladi. Oxirgi 24 soatdagi qidiruv identifikatoriga bog‘lanadi. Analitika ishlamasa bron to‘xtatilmaydi; bog‘lanmagan bron alohida umumiy bronlar sonida qoladi.
- Vaqtli qidiruvdan bronga ulush: shu 14 kun ichida qayd qilingan vaqtli qidiruvlardan shu davrda kamida bitta bron yaratganlar ulushi. Nol qidiruvda foiz ko‘rsatilmaydi. Bitta qidiruvdan bir nechta bron bitta konversiya hisoblanadi.
- Qidiruvlar va sahifa ochishlar qurilma hodisalari: reklama bloklagich yoki tarmoq xatosi tufayli to‘liq bo‘lmasligi, soxtalashtirilishi mumkin. Bu akkauntlar soni emas. Alohida mijozlar soni serverdagi Telegram bronlaridan olinadi; qo‘lda kiritilgan ism/telefonlar shaxsga birlashtirilmaydi.
- Javob vaqti: shu davrda yaratilgan ilova bronidan birinchi tasdiq/rad hodisasigacha soniyalar; faqat hodisasi bor bronlar. Javobsiz so‘rovlar o‘rtachaga nol sifatida kiritilmaydi. Holat sana bilan qayta hisoblanadi, tarixiy snapshot emas.
- Bekor qilishlar — davrda yaratilgan ilova bronlarining joriy holati. Seans natijalari — davrda boshlanadigan barcha bronlar bo‘yicha egalar qaydlari. Qayd qilinmagan tugagan seanslar alohida ko‘rsatiladi.
- Ikkinchi hafta qaytish — birinchi va ikkinchi haftada tasdiqlangan seanslari bor alohida Telegram mijozlari. Bu tashrif yoki pul tushumi tasdig‘i emas.

Qidiruv hodisalarining API’si faqat ruxsat etilgan maydonlarni qabul qiladi. PostgreSQL orqali 60 hodisa/sessiya/daqiqa va umumiy 2000 hodisa/daqiqa chegaralari bor. Yangi takroriy bron va obuna yozuvlari uchun 30 so‘rov/akkaunt/daqiqa chegarasi; 100 faol kelajak obuna chegarasi mavjud. 429 javobida Retry-After beriladi. Bular UPDATE_PLAN.md dagi barcha endpointlar uchun umumiy himoya ishlarini tugatmaydi. Limit hisoblagichlari 24 soatdan keyin keyingi yozuvda tozalanadi; bu bron/analitika uchun retention siyosati emas.

## Pilotdan keyingi funksiyalarni tekshirish

Takroriy qo‘lda bron: bo‘sh vaqtni tanlang → “Har hafta shu vaqtga bron” → 1–4 hafta → tekshirish → sanalarni tanlash → tasdiqlash. Band sanada sukut bilan qisman bron yaratilmaydi. Saqlash yana tekshiradi va tanlangan sanalarning barchasini bir tranzaksiyada yozadi. So‘rov kaliti qayta yuborilganda mavjud natija qaytariladi; har bron alohida bekor qilinadi, o‘z narxi va to‘lov holatiga ega. Bu egalar vositasi; mijoz uchun takroriy bron interfeysi kiritilmagan.

Bo‘sh vaqt xabarnomasi: band vaqt → “Bo‘shasa xabar bering”. Bronlar → “Bo‘sh vaqt xabarnomalari” orqali obunani o‘chirish mumkin. Worker har 15 soniyada mavjudlikni qayta tekshiradi; rad etilgan/bekor qilingan bron va ochilgan blok ham shu yo‘l bilan qamraladi. O‘chiq obuna, yopiq maydon/soat, qayta band qilingan vaqt yoki 5 daqiqadan kam qolgan slotga xabar yuborilmaydi. Har obuna bir marta navbatga tushadi. Bu rezerv emas; bron serverdan yana tekshiriladi. Telegram yuborish va bazada belgilash orasida worker qulab qolsa, avvalgi xabarnomalar kabi takroriy yetkazish ehtimoli qoladi. Obunani o‘chirish allaqachon Telegramga yuborilgan xabarni qaytarib olmaydi.

Rollback: bayroqlarni o‘chiring va avvalgi ilova versiyalarini qaytaring. Yangi jadvallar/ustunlarni o‘chirmang; bu baza tiklash amali emas. Backend eski versiyaga qaytishidan oldin yangi botni to‘xtatish/qaytarish kerak.

## Keyingi tajribalar bo‘yicha ochiq qarorlar

- “O‘yinchi kerak”: avval yopiq guruh, mas’ul sardor, e’lon muddati va tasdiqlash tartibi belgilanadi. Pilot dalili va ushbu qoidalarsiz ommaviy modul yoqilmaydi.
- To‘lov: kelmay qolishlar o‘lchovi, provayder va merchant akkaunti kerak. Shundan keyin imzolangan callback, bir xil hodisaga qayta javob, summani/valyutani tekshirish, qaytarish va reconciliation uchun alohida integratsiya qilinadi. Soxta “to‘lov muvaffaqiyatli” oqimi qo‘shilmagan.
- A’zolik, turnir, reyting va xodim rollari reja bo‘yicha keyinga qoldirilgan; talablari tasdiqlanmagan.

Ikki haftalik real pilotni kod testi bilan almashtirish mumkin emas. Egalar/mijozlar bilan real sinov, pilot natijasi va xizmatga oid qarorlar hali talab qilinadi.
