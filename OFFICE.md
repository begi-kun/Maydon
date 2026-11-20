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

## Qolgan ishlar — 20-noyabr

Muddatlar pilot boshlangan kunga nisbatan berilgan. Rahbar pilot sanasini, har bir rol uchun odamni va navbatchining o‘rinbosarini belgilaydi. GitHub Issues’da vazifani dalil bilan yopish uchun ofis shablonidan foydalaniladi.

### Pilot va ommaviy targ‘ibotdan oldin

- [ ] **QA va admin.** Haqiqiy telefonda mijoz, ega va admin bilan supportdan boshlab maydon biriktirishgacha sinang. Bron, tasdiq, rad etish, bekor qilish, eslatma, bir vaqtga ikki so‘rov, boshqa akkauntga tegishli ma’lumot va muddati tugagan sessiyani tekshiring. Natijani har ssenariy uchun qayd eting.
- [ ] **Mobil QA.** Telegram kontakt oynasi, botdan ayni maydon va vaqtga qaytish, klaviatura, ekran chetlari va VoiceOver/TalkBack orqali bronni yakunlashni qurilmada tekshiring.
- [ ] **Infratuzilma navbatchisi.** Railway snapshot jadvali, saqlash muddati va saqlash joyini yozing. Mavjud rejali snapshotni alohida bazaga tiklang. Qaysi vaqtgacha ma’lumot tiklangani, sarflangan vaqt va javobgar ismni qayd eting.
- [x] **Backend muhandisi.** Uchta boshlang‘ich SQL migratsiyasi versiyalandi. Oldingi relizning sxema amallari o‘zgarishsiz ko‘chirildi. Alohida PostgreSQL bazasida avvalgi sxemadan yangilash, qayta ishga tushirish va saqlangan profilni o‘qish tekshirildi. 75 backend testi o‘tdi.
- [ ] **Bot muhandisi va navbatchi.** Health monitoring hamda kechikkan yoki yetkazilmagan xabarlar uchun sinov ogohlantirishlarini oling. Qabul qiluvchi, javob berish tartibi va navbat normallashgan vaqtni qayd eting.
- [ ] **Repo administratori.** Asosiy branchda backend va frontend CI majburiyligini tekshiring. GitHub API main uchun frontend va backend majburiyligini tasdiqladi. Muvaffaqiyatsiz PR bloklanishi bo‘yicha dalilni qayd eting.
- [ ] **Mini App muhandisi.** Xarita kalitining ruxsat etilgan production domeni va kvotasini provayder panelida tekshiring. Ishlaydigan production xaritasi va kvota nazoratini qayd eting.
- [ ] **Support mas’uli.** Admin aloqasini haqiqiy mijozdan sinang. Telegram ID, telefon, surat va bron ma’lumotidan foydalanish, saqlash muddati va o‘chirish tartibini kelishing. Mijozga support, bekor qilish va to‘lov holati qoidalarini ko‘rsating. Sinov murojaatini boshidan oxirigacha yoping.

### Pilot, o‘sish va har relizdagi ishlar

- [ ] **Pilot rahbari, D0.** Egalar roziligi bilan 5–10 maydonni tanlang, dastlabki uch egaga jadval va oflayn bron kiritishni ko‘rsating. Boshlang‘ich noyob akkauntlar soni va test hisoblari istisnolarini qayd eting.
- [ ] **Ega va support, har kuni.** Bo‘sh soatlar, javobsiz so‘rov, oflayn bron, jadval xatosi va seans natijalarini solishtiring. Birinchi sutkadagi har bir maydon natijasini yozing.
- [ ] **Rahbar, 14-kun.** Pilot hisobotida qidiruvdan bronga o‘tish, javob vaqti, bekor qilish, kelmay qolish va ikkinchi hafta qaytishini baholang. Yetishmayotgan qaydlarni ko‘rsating. Kengaytirish, uzaytirish yoki tuzatish qarorini yozing.
- [ ] **Muhandislar va navbatchi, 15–30-kun.** Pilotdagi asosiy nosozliklarni yoping, natijalarni qayta o‘lchang va tiklash mashqini takrorlang.
- [ ] **O‘sish mas’uli, 1–6-hafta.** Egalar, jamoa sardorlari va moderator roziligidagi guruhlar orqali 1 000 yangi noyob foydalanuvchini maqsad qiling. Har juma haqiqiy natijani haftalik marralar bilan solishtiring. Kanal rejasi va yuboriladigan matnlar [pilot PDFida](artifacts/pilot/Bronn-1000.pdf).
- [ ] **Reliz mas’uli, har chiqarishda.** Alohida bazada backend testlari, frontend test/build, sxema mosligi, deploy tartibi, aynan bitta bot worker, startup loglari, jonli tekshiruv va o‘zgargan Telegram oqimlarini qayd eting.

### Pilot natijasiga bog‘liq mahsulot qarorlari

- [ ] **Mahsulot rahbari va QA, 14-kundan keyin.** Tayyor takroriy qo‘lda bron va bo‘sh vaqt xabarnomasini alohida baholang. Tanlangan funksiyada bayroqni yoqish, sinash va qaytarish natijasini yozing. Xabarnoma uchun API va bot sozlamalari mos bo‘lsin.
- [ ] **Ega bilan ishlovchi muhandis.** Takroriy vaqt bloklari va ko‘p soatli bron uchun kesishuv, tundan o‘tish va qisman bekor qilish qoidalarini kelishing. Egalar o‘rtasida ma’lumot ajratilishi va jadval formulalaridan himoyalangan bron/to‘lov eksportini sinang.
- [ ] **Mahsulot rahbari.** Saralangan maydonlar va qidiruv yaxshilanishlarini pilotdagi so‘rovlar asosida ustuvorlashtiring. “O‘yinchi kerak” tajribasi uchun yopiq guruh, sardor, e’lon muddati va tasdiq tartibini belgilang.
- [ ] **To‘lov mas’uli.** Kelmay qolishlar o‘lchovidan keyin provayder va merchant shartlarini baholang. Qaror ijobiy bo‘lsa, imzolangan callback, takroriy hodisa, summa/valyuta tekshiruvi, qaytarish va hisoblarni solishtirish sinovlarini bajaring.
- [ ] **Rahbar.** A’zolik, turnir, reyting va xodim rollari bo‘yicha talablar va muvaffaqiyat mezonini pilotdan keyin belgilang. Har biri uchun alohida boshlash yoki kechiktirish qarorini yozing.

### 20-noyabr, production tekshiruvi

PR 22 orqali versiyalangan migratsiyalar va xabar navbati monitoringi productionga chiqdi. GitHub backend/frontend tekshiruvlari va jonli health, navbat hamda dizayn tekshiruvi o‘tdi. Railway PostgreSQL uchun backup jadvali va mavjud volume snapshotlari soni nol. Navbatchiga ogohlantirish yetganini tasdiqlash va rejali backupdan tiklash ochiq.
