# Maydon loyiha ofisi

2026-yil 20-noyabr. Bronn Railway’da ishlayapti. Hozirgi maqsad — haqiqiy bron jarayonini tasdiqlash va Namangandagi 5–10 maydon bilan boshqariladigan pilotni boshlash.

## Jamoa qanday ishlaydi

| Rol | Birinchi topshiriq | Ishni qabul qilish dalili |
|---|---|---|
| Loyiha rahbari | Har bir rolga ism, navbatchiga o‘rinbosar va pilot sanasini belgilash | Ishlar GitHub Issues’da mas’ul va muddat bilan ochilgan |
| Backend muhandisi | Sxema o‘zgarishlarini versiyalash | Oldingi sxemadan yangilash va takror ishga tushirish testi alohida PostgreSQL’da o‘tgan |
| Infratuzilma navbatchisi | Railway snapshot jadvali, saqlash muddati va tiklashni tekshirish | Izolyatsiyalangan tiklash vaqti, eng so‘nggi tiklangan bron va navbatchi qayd etilgan |
| Bot muhandisi | Xabarlar navbati va yetkazish xatolarini kuzatish | Sinov muhitida kechikkan xabar ogohlantirish bergan va navbatchi uni qabul qilgan |
| Mini App muhandisi va QA | Xarita domeni va kvotasini tekshirish, telefon orqali bron sinovi | Egasi, mijoz va admin akkauntlarida bron, tasdiq, bekor qilish va eslatma tekshirilgan |
| Pilot va support mas’uli | Maydon egalarini tayyorlash, yordam kanali va ma’lumot o‘chirish jarayonini aniqlash | Ishlaydigan aloqa, tasdiqlangan saqlash muddati va sinov murojaati yopilgan |

Har vazifa uchun “Maydon ofisi vazifasi” shablonidan foydalaniladi. Bajaruvchi ishni pull request yoki tekshiruv natijasiga bog‘laydi. Rahbar har kuni to‘siqlarni ko‘radi va qabul mezoni bajarilgan ishni yopadi. Rollarga odam biriktirish ochiq.

## Production va pilotga kirish

1. QA reliz commitini qayd etadi. Validate workflow’da backend, frontend, dizayn va mahsulot tekshiruvlari o‘tishi kerak. Repo administratori majburiy CI sozlamasini tekshiradi.
2. Navbatchi snapshot, tiklash va ogohlantirish dalillarini yig‘adi. Production health workflow asosiy branchga tushgach, GitHub Actions jadvali bo‘yicha taxminan har 15 daqiqada ishga tushadi. Navbatchi birinchi hosted natija va xato bildirishnomasini tekshiradi.
3. Kod relizi kerak bo‘lsa, backend, bitta bot worker va frontend ketma-ket chiqariladi. QA live tekshiruvni va Telegram’dagi haqiqiy akkaunt sinovini bajaradi.
4. Rahbar ochiq bandlarni [production ro‘yxati](PRODUCTION_CHECKLIST.md) bilan solishtiradi. Ikki marta band qilish, begona akkaunt ma’lumotiga kirish yoki tiklash sinovi muvaffaqiyatsiz bo‘lsa, kengaytirish to‘xtatiladi. Navbatchi hodisa vaqtini, ta’sirlangan xizmatni va oxirgi sog‘lom relizni qayd etib, [tiklash tartibi](RECOVERY_RUNBOOK.md) bo‘yicha ishlaydi.

## Pilot boshlanganidan keyin

| Davr | Mas’ul va ish | Natija |
|---|---|---|
| Birinchi 24 soat | Navbatchi har relizdan keyin health, backlog va bot worker sonini tekshiradi. Support har maydon egasi bilan birinchi so‘rov natijasini qayd etadi. | Ochiq hodisalar, mas’ul va keyingi tekshiruv vaqti |
| 2–7-kun | Pilot mas’uli javobsiz so‘rovlar, jadval to‘qnashuvi va oflayn bronlarni egalar bilan har kuni solishtiradi. | Muammo kesimida soni va tuzatishga biriktirilgan vazifa |
| 14-kun | Rahbar Admin → Pilot’dan 14 kunlik hisobotni oladi. Jamoa qidiruvdan brongacha o‘tish, egalar javobi va seans natijalarini [pilot mezonlari](PILOT_RUNBOOK.md) bilan baholaydi. | Dalillar bilan kengaytirish, pilotni uzaytirish yoki tuzatish qarori |
| 15–30-kun | Muhandislar qarordagi asosiy muammolarni yopadi. Navbatchi qayta tiklash mashqini takrorlaydi. | Takroriy o‘lchov va keyingi maydonlar guruhiga qaror |

## 20-noyabr tekshiruvlari

Mini App’da 4 test va production build o‘tdi. Live tekshiruv API va baza holati, owner/admin endpointlarining autentifikatsiya talabi va frontendning API bilan mosligini tasdiqladi. Ushbu tekshiruvda haqiqiy Telegram broni bajarilmadi. Hosted CI, snapshot jadvali va tashqi ogohlantirishning navbatchiga yetib borishi ochiq.
