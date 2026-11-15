# MAYDON — alohida dizayn rejasi

Sana: 2026-11-15. Holat: dizayn kodi va avtomatik qabul tekshiruvlari bajarildi; frontend Railwayga chiqarildi; haqiqiy telefon tekshiruvi hali tasdiqlanmagan.

Maqsad: telefonda sport va kerakli vaqtni tez tanlash, mos maydonni baholash va bron holatini tushunishni yengillashtirish. To‘q yashil/lime ranglar, MAYDON brendi va mavjud funksiyalar saqlanadi.

## 1. Mobil bosh sahifa

- Katta hero bannerni qisqa sarlavha va kichik tasvirga aylantirish.
- Asosiy tartib: qisqa kirish → sport → sana/vaqt → qidiruv natijalari.
- Manzil yoki nom qidiruvini asosiy vaqt tanlovi bilan bir guruhga joylash.
- Egalar uchun taklifni natijalardan keyin qoldirish.
- 390×844 ekranda sport va vaqt boshqaruvlari hamda birinchi karta boshlanishi ko‘rinishi maqsad qilinadi; matn kattalashtirilganda kontent kesilmaydi.

## 2. Qidiruv va filtrlar

- “Qachon o‘ynaymiz?” asosiy sarlavha bo‘ladi.
- Bugun/ertaga va soat tugmalari bir xil tanlangan holatga ega bo‘ladi.
- Sport tanlovi vaqt tanlovidan oldin ko‘rinadi; barcha sport turlari ochiq qoladi.
- Masofa bo‘yicha saralash va xarita ikkilamchi amallar bo‘ladi.
- Ulashish va filtrlarni tozalash asosiy bron tugmasi bilan vizual raqobat qilmaydi.
- Yuklanish, xato va haqiqiy nol natija alohida ko‘rsatiladi. Yangilanishda joylashuv sakramasligi tekshiriladi.
- Natija yo‘q bo‘lsa, vaqtni almashtirish yoki filtrlarni tozalash aniq taklif qilinadi.

## 3. Maydon kartalari

- Ketma-ketlik: haqiqiy rasm → nom/sport → qisqa manzil yoki masofa → tanlangan bo‘sh vaqt → soatlik narx → davom etish.
- Rasm bo‘lmasa, sportga mos neytral tasvir ishlatiladi.
- Rasm nisbatlari va ichki bo‘shliqlar bir xil bo‘ladi; uzun nom va manzil kartani buzmaydi.
- So‘m/soat doim ko‘rinadi. “Bo‘sh” yozuvi faqat muvaffaqiyatli tekshirilgan vaqt uchun chiqadi.
- Tasdiqlanmagan reytinglar, sun’iy mashhurlik yoki yolg‘on shoshiltirish yozuvlari qo‘shilmaydi.

## 4. Maydon tafsiloti va bron

- Galereya, manzil/yo‘nalish, qulayliklar va ish vaqti o‘qilishi oson guruhlarga joylanadi.
- Mobil tartib: maydon haqida qisqa ma’lumot → sana → vaqt → narx va bron xulosasi → asosiy amal.
- Tanlangan sana/soat va 1 soat narxi yuborishdan oldin ko‘rinadi.
- Egasi tasdiqlashi kutilishi tushuntiriladi. So‘rov yuborish va tasdiqlangan bron rang/matn bilan farqlanadi.
- Telefon ulashish va Telegramga kirish bosqichlari tanlangan maydon/vaqtni saqlaydi.
- Pastga yopishgan amal paneli faqat klaviatura, safe-area va pastki navigatsiya bilan to‘qnashmasa qo‘llanadi.

## 5. Egalar paneli

- Birinchi navbatda mavjud jadval saqlanadi; mijoz bosh sahifasining yangi ko‘rinishi bilan aralashtirilmaydi.
- Keyingi alohida iteratsiya: bugungi jadval, kutayotgan so‘rovlar, qo‘lda bron va bloklash amallarining ko‘rinuvchanligi.
- Rangga qo‘shimcha ravishda har bir bron holati matn bilan beriladi.

## 6. Ish ketma-ketligi

1. Mavjud mobil va desktop ko‘rinishlarning skrinshotlarini olish; boshlang‘ich holatni saqlash.
2. Bosh sahifa va qidiruvni kodda joylashtirish; 360, 390 va 430 px kengliklarda tekshirish.
3. Karta va bo‘sh/xato/yuklanish holatlarini tekshirish.
4. Maydon tafsiloti va bron xulosasini moslashtirish.
5. 768 va 1280 px kengliklarda desktop/tablet tartibini tekshirish.
6. Haqiqiy Telegram mobil oqimini tekshirish, keyin o‘zgarishlarni reliz qilish.

## Qabul mezonlari

- 360 px kenglikda gorizontal scroll yo‘q; asosiy bosiladigan elementlar kamida 44×44 px.
- Klaviatura fokuslari ko‘rinadi, tugmalar nomlangan va tanlangan holatlar screen readerga yetkaziladi.
- Matn kontrasti WCAG AA bo‘yicha tekshiriladi; rang yagona holat belgisi bo‘lmaydi.
- Uzun nom, fotosiz maydon, nol natija, server xatosi va sekin internet tekshiriladi.
- Filtr → karta → bron → Telegram kirishi oqimida tanlangan vaqt saqlanadi.
- Qidiruv yangilanganda noto‘g‘ri bo‘sh vaqt yoki eski natija tasdiqlangan deb ko‘rsatilmaydi.
- Frontend build o‘tadi; mobil va desktop ko‘rinishlari skrinshot orqali solishtiriladi.

Mahsulot ustuvorliklari va pilot: MAYDON_PRODUCT_PLAN.md. Haftalik bron, kutish ro‘yxati va to‘lov integratsiyasi ushbu dizayn iteratsiyasining doirasiga kirmaydi.

## Bajarilgan ishlar — 2026-11-15

- Bosh sahifadagi katta hero qisqartirildi; sport → vaqt/qidiruv → natijalar tartibi joriy etildi.
- Sportlar ochiq ko‘rinadi; sana va vaqt bir guruhda. Masofa, xarita va ulashish yordamchi amallar sifatida berildi.
- Kartalarda manzil, so‘m/soat, tekshirilgan bo‘sh vaqt va davom etish amali ko‘rinadi. Fotosiz stol tennisi/bilyard uchun sportga mos tasvir qo‘shildi; uzun matnlar satrlarga bo‘linadi.
- Maydonlar yuklanishidagi server xatosi haqiqiy nol natijadan ajratildi va qayta yuklash amali qo‘shildi.
- Bron xulosasida sana, boshlanish/tugash vaqti, 1 soat narxi va egasi tasdiqlashi kerakligi ko‘rsatiladi. Xatolik/yuklanishda eski tanlov orqali so‘rov yuborish cheklangan.
- Katta matnda header qayta joylashadi; qidiruv fokus belgisi va mobil tugmalar o‘lchamlari yaxshilandi.

Tekshiruv dalillari: `artifacts/design/` ichida boshlang‘ich va yangi skrinshotlar hamda `check-results.json` saqlanadi. Brauzer tekshiruvlari sinov API javoblari bilan bajariladi; bu haqiqiy backend yoki Telegram integratsiyasi tekshiruvining o‘rnini bosmaydi.

## Yakuniy tekshiruvlar va egalar iteratsiyasi

- [x] Bosh sahifa, kartalar va bron xulosasi 360, 390, 430, 768, 1280 px kengliklarda tekshirildi. 390×844 da birinchi karta boshlanishi pastki navigatsiyadan oldin ko‘rinadi.
- [x] Uzun nom/manzil, fotosiz maydon, rasm yuklash xatosi, nol natija, server xatosi va sekin internet holatlari tekshirildi.
- [x] Qidiruvni yangilashda natijalar joyi saqlanadi; avvalgi vaqt tekshirilayotganda “Bo‘sh” tasdig‘i yashiriladi va karta vaqtincha bosilmaydi.
- [x] Kontrastdagi kamchiliklar tuzatildi; mijoz va egalar oqimlarida axe-core WCAG A/AA/2.1 AA tekshiruvlari xatosiz o‘tdi. Fokuslar, tugma nomlari, `aria-pressed`, 44 px asosiy nishonlar va mazmunga o‘tish havolasi tekshirildi.
- [x] Kattalashtirilgan matn va klaviatura tufayli qisqargan viewport tekshirildi. Pastki navigatsiya balandligi o‘lchanib, pastki bo‘shliq moslanadi; `safe-area` hisobga olinadi.
- [x] Telefon ulashish, bot havolasida maydon/vaqt, botdan `venue`/`slot` bilan qaytish va 409 konflikti avtomatik tekshirildi.
- [x] Haqiqiy lokal FastAPI/PostgreSQL bilan rasm → qidiruv → telefon holati → bron so‘rovi → egasi tasdiqlashi → band vaqt qidiruvdan chiqishi tekshirildi. Telegram identifikatsiyasi va contact oynasi bu testda sinov adapteri orqali berilgan; haqiqiy Telegram qurilmasi deb hisoblanmaydi.
- [x] Backendning 50 testi, frontendning 4 testi va 22 brauzer tekshiruvi/auditi o‘tdi; frontend build o‘tdi.
- [x] Egalar iteratsiyasi: bugungi jadvalga qaytish, kutayotgan so‘rovlarga tez o‘tish, alohida qo‘lda bron/vaqtni yopish amallari va holatlarning matnli ko‘rinishi qo‘shildi. Mobil va desktop skrinshotlar saqlandi.
- [x] Brauzer tekshiruvi CI ga qo‘shildi; skrinshotlar va natijalar artifact sifatida saqlanadi. Hosted CI natijasi ushbu lokal tekshiruvlar bilan tenglashtirilmaydi.
- [ ] Haqiqiy telefon: Telegram ichida kirish, contact oynasi, botdan qaytish, klaviatura, safe-area va VoiceOver/TalkBack bilan yakuniy tekshiruv. Qurilma bu muhitdan boshqarilmaydi; foydalanuvchiga tekshirish so‘rovi yuborilgan, javob hali olinmagan.

Dalillar: `artifacts/design/check-results.json`, `accessibility-audit.json`, `real-api-results.json`, `backend-test-results.json` va skrinshotlar. `accessibility-before-fixes.json` boshlang‘ich aniqlangan kamchiliklarni, yakuniy audit esa tuzatilgan holatni saqlaydi.

Qayta tekshirish: `cd miniapp && npm test && npm run build && npm run test:design`. Chrome bo‘lmasa `npx playwright install chromium`; kerak bo‘lsa `CHROME_PATH` beriladi. Jonli tekshiruv: `python3 scripts/check_live.py --design` va `cd miniapp && npm run test:design:live` (faqat o‘qiydi).

Reliz faqat dizayn nusxasidan tayyorlandi: shu vaqtda ishchi papkaga qo‘shilayotgan mahsulot/pilot funksiyalari o‘zgartirilmagan va ushbu relizga kiritilmagan. Asos commit va fayl SHA-256 lari `artifacts/design/release-source.json` da, qayta qo‘llash mumkin bo‘lgan o‘zgarishlar `artifacts/design/design-release.patch` da.

## Reliz natijasi

- Railway `Maydon-web`: `ca577424-c8cf-4a60-bfbb-22fb79439488` — **SUCCESS**.
- Jonli sayt: https://maydon-web-production-3612.up.railway.app
- `python3 scripts/check_live.py --design` — PASS: API/baza, autentifikatsiya chegaralari, frontend assetlari va dizayn belgilarining mavjudligi.
- `npm run test:design:live` — PASS: 360/390/430/768/1280 px, haqiqiy rasm, bo‘sh vaqtlar, bron xulosasi, Telegram havolasidagi maydon/vaqt va bosh sahifa/tafsilot WCAG avtomatik auditlari. Productionda bron yaratilmagan.
- Jonli ko‘rikda aniqlangan ko‘p rasmli galereyaning klaviatura fokusi tuzatildi va regressiya testiga qo‘shildi.
- Dalillar: `artifacts/design/live-results.json`, `deployment.json`, `live-*.png`.
- Vaqtinchalik test API jarayonlari va lokal PostgreSQL konteyneri to‘xtatildi.

**Ochiq qabul bandi:** haqiqiy telefondagi Telegram/contact/klaviatura/safe-area va VoiceOver/TalkBack sinovi. Qurilmaga kirish bo‘lmagani uchun bu band bajarilgan deb belgilanmagan. Frontend avtomatik mobil va jonli brauzer tekshiruvlari asosida chiqarildi; rejadagi “haqiqiy mobil tekshiruvdan keyin reliz” ketma-ketligi to‘liq bajarilmagan. Foydalanuvchining telefon tekshiruvi natijasi olinishi kerak.

Desktop menyu bo‘yicha tuzatish: och fondagi faol bo‘lim yozuvi va belgisi to‘q yashilga o‘zgartirildi. Desktop WCAG auditi lokal va jonli tekshiruvga qo‘shildi.

Desktop kontrast hotfix relizi: `550ce01b-e595-4c99-a8f3-6830a94fb947` — SUCCESS. Jonli desktop/mobil auditlari PASS.
