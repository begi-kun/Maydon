# MAYDON — Hudle tajribasidan foydalanish rejasi

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

## 2. Ikki haftalik kichik pilot

Taklif: 5–10 maydon, bir mas’ul bilan ish boshlash. Egalar jadvalga telefon va kelib olingan bronlarni ham kiritishni o‘rganadi. Egalar bilan bog‘lanish va tashqi xabarlar yuborish ushbu reja bilan bajarilmaydi.

O‘lchovlar:
- Vaqt bo‘yicha qidiruvlar va ulardan yaratilgan bronlar ulushi.
- Bron so‘rovidan tasdiq/rad javobigacha vaqt.
- Jadval xatosi sababli bajarilmagan bronlar.
- Bekor qilish va kelmay qolish holatlari.
- Ikkinchi hafta qayta bron qilgan mijozlar.

Hozir qidiruv hodisalari uchun analitika qo‘shilmadi. Pilot oldidan minimal hodisalar: discovery_results (sana, soat, sport, natija soni), venue_open, booking_request_created. Telefon, GPS, ism va erkin qidiruv matnini hodisalarga qo‘shmaslik. So‘rovlar soni bilan alohida mijozlar sonini aralashtirmaslik. Bazaviy o‘lchovlar olinmaguncha muvaffaqiyat foizi va’da qilinmaydi.

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
