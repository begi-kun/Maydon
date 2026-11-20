# Bronn — Hudle tajribasidan foydalanish rejasi

Sana: 2026-11-15. Maqsad: Namanganda kerakli vaqtga maydon topish va ishonchli bron qilishni soddalashtirish.

## 1. Vaqt bo‘yicha qidiruv — birinchi reliz

Mavjud: sport/manzil qidiruvi, vaqt bo‘yicha API filtri, masofa, bron vaqtini tanlovga olib o‘tish, egalar jadvali, telefon orqali olingan bronlarni qo‘lda kiritish, bloklar va Telegram eslatmalari.

Ushbu bosqichdagi ishlar:
- Bugun 18:00 / 20:00 / 22:00 va ertaga 20:00 tezkor tanlovlari; o‘tgan vaqt yashiriladi.
- Qidiruv natijalarida sana/vaqt, maydon soni va kartada tanlangan soat ko‘rsatiladi.
- Bo‘sh vaqtlar 30 soniyada qayta tekshiriladi; qo‘lda yangilash ham bor. Bu doimiy real vaqt kafolati emas; bron yaratishda server yana tekshiradi.
- Qidiruvni tizim ulashish oynasi yoki nusxalangan havola orqali yuborish. Havola sport, qidiruv so‘zi va yaroqli kelajak vaqtini tiklaydi; shaxsiy ma’lumot, GPS va Telegram parametrlari kiritilmaydi.
- Bron so‘rovi egasi tasdiqlagach kuchga kirishi ochiq yoziladi.

Tekshiruv: frontend build; URL uchun sport/vaqt validatsiyasi, eskirgan va noto‘g‘ri vaqtlar, UTC+5 va shaxsiy parametrlar olib tashlanishi. Alohida real Telegram va mobil brauzer sinovi relizdan oldin bajariladi.

Mahalliy holat (2026-11-15): birinchi bosqichning mavjud interfeysi tekshirildi. `miniapp/tests/discovery.test.mjs` sport va vaqt validatsiyasi, UTC+5, noto‘g‘ri sanalar, 5 daqiqalik/60 kunlik chegaralar, havola orqali filtrlarni tiklash va begona URL parametrlarini chiqarib tashlashni tekshiradi. `npm test` va frontend build muvaffaqiyatli o‘tdi; testlar CI tekshiruviga ham qo‘shildi. Qidiruv izohida doimiy real vaqt kafolati yo‘qligi va server bron vaqtini yana tekshirishi ochiq yozildi. Real Telegram va mobil brauzer sinovi, kod ko‘rib chiqish va reliz hali bajarilmagan. Deploy qilinmadi.

## 2. Ikki haftalik kichik pilot

Taklif: 5–10 maydon, bir mas’ul bilan ish boshlash. Egalar jadvalga telefon va kelib olingan bronlarni ham kiritishni o‘rganadi. Egalar bilan bog‘lanish va tashqi xabarlar yuborish ushbu reja bilan bajarilmaydi.

O‘lchovlar:
- Vaqt bo‘yicha qidiruvlar va ulardan yaratilgan bronlar ulushi.
- Bron so‘rovidan tasdiq/rad javobigacha vaqt.
- Jadval xatosi sababli bajarilmagan bronlar.
- Bekor qilish va kelmay qolish holatlari.
- Ikkinchi hafta qayta bron qilgan mijozlar.

Mahalliy kodda pilot analitikasi qo‘shildi; real pilot hali boshlanmagan. Minimal hodisalar: discovery_results (sana, soat, sport, natija soni), venue_open, booking_request_created. Telefon, GPS, ism va erkin qidiruv matnini hodisalarga qo‘shmaslik. So‘rovlar soni bilan alohida mijozlar sonini aralashtirmaslik. Bazaviy o‘lchovlar olinmaguncha muvaffaqiyat foizi va’da qilinmaydi.

## 3. Har hafta shu vaqt — pilotdan keyingi nomzod

Egalar uchun boshlash: to‘rt haftagacha takroriy qo‘lda bron. Har sana ish vaqti, mavjud bron va blokka qarshi tekshiriladi. Qisman band bo‘lsa, hech narsa yashirincha yozilmaydi; band sanalar ko‘rsatiladi va aniq tanlov olinadi. Har bron alohida bekor qilinadi va o‘z narxiga ega. Barcha yozuvlar bir tranzaksiya va maydon qulfi bilan himoyalanadi. Avval mojarolar va qayta urinish testlari, keyin mijoz interfeysi.

## 4. Bo‘shagan vaqt xabarnomasi

Mijoz maydon/soatga obuna bo‘ladi. Bekor qilingan bron yoki ochilgan blokdan keyin mavjudlik tekshiriladi. Bitta hodisa uchun takroriy xabar cheklanadi; muddati o‘tgan obunalar ishlamaydi. Obunani o‘chirish bor. Xabar joyni band qilmaydi; bron yaratish yana serverdan tekshiriladi. Talab pilotdagi band vaqt so‘rovlaridan baholanadi.

## 5. Keyingi tajribalar

- Sardor tasdiqlaydigan “o‘yinchi kerak” e’loni: avval kichik yopiq guruhda.
- Mahalliy to‘lov integratsiyasi: kelmay qolish holatlari o‘lchangach; merchant ulanishi, callback, takroriy hodisa, qaytarish va hisobni solishtirish ishlab chiqiladi. Hozirgi to‘lov holati pul yig‘maydi.
- A’zolik, turnirlar, reytinglar va xodim rollari: asosiy oqim tasdiqlanmaguncha keyinga qoldiriladi.

## Reliz talablari

UPDATE_PLAN.md va PRODUCTION_CHECKLIST.md dagi xavfsizlik, monitoring, backup va haqiqiy akkaunt tekshiruvlari saqlanadi. Ushbu reja production tayyorligi haqidagi xulosa emas. Birinchi bosqich mahalliy tekshirilgach, kod ko‘rib chiqish va reliz tartibi bo‘yicha chiqariladi; bu ish avtomatik deployni o‘z ichiga olmaydi.


## Amalga oshirish holati — 2026-11-15

- 1-bosqich: mavjud vaqtli qidiruv tekshirildi; URL testlari va CI qo‘shildi.
- 2-bosqich: maxfiy maydonlarsiz discovery_results/venue_open hodisalari, serverdagi booking_request_created, adminning 14 kunlik pilot hisoboti va egalar uchun seans natijasi qaydi qo‘shildi. Hisobot so‘rov va mijozlar sonini ajratadi; javob vaqti, bekor qilish, jadval xatosi/kelmay qolish va ikkinchi hafta qaytishini ko‘rsatadi. Qayd qilinmagan natijalar noma’lum qoladi.
- 3-bosqich: egalar uchun 1–4 haftalik takroriy qo‘lda bron, tekshirish/aniq sana tanlash, tranzaksiya, maydon qulfi va qayta so‘rov himoyasi tayyorlandi. `ENABLE_RECURRING_BOOKINGS` odatda o‘chiq; pilotdan keyingi qaror saqlangan.
- 4-bosqich: band slotga obuna, shaxsiy ro‘yxat/o‘chirish, workerda bo‘sh vaqtni tekshirish va bitta obuna uchun bitta navbat yozuvi tayyorlandi. `ENABLE_AVAILABILITY_ALERTS` API va botda odatda o‘chiq. Xabar joyni rezerv qilmaydi.
- Pilotni yuritish, o‘lchov ta’riflari, bayroqlar, deploy/rollback va keyingi tajribalar uchun qarorlar [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md) da yozilgan.
- Haqiqiy ikki haftalik pilot, egalarni jalb qilish, haqiqiy Telegram akkaunti sinovi, to‘lov merchant ulanishi va 5-bo‘limdagi keyingi tajribalar bajarilgan deb belgilanmagan. Avtomatik deploy bajarilmagan. PRODUCTION_CHECKLIST.md dagi qolgan operatsion talablar saqlanadi.

Mahalliy yakuniy tekshiruv: alohida PostgreSQL bazasida 66 backend testi, 4 URL testi, frontend build, 390px/1280px mahsulot brauzer oqimlari va mavjud dizaynning 19 tekshiruv/auditi o‘tdi. Brauzerda API/Telegram javoblari sinov uchun almashtirilgan; haqiqiy Telegram xabar yetkazilishi tasdiqlanmagan. Hosted CI ishga tushgani haqida xulosa berilmagan.
