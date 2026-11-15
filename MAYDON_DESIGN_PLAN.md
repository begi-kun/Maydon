# MAYDON — alohida dizayn rejasi

Sana: 2026-11-15. Holat: rejalashtirilgan; ushbu hujjat dizayn o‘zgarishlari bajarilganini anglatmaydi.

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
