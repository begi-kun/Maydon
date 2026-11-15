# Hudle public website analysis

Inspected: 15 November 2026. Scope: public homepage HTML/CSS, venue-search page, and venue-owner marketing page. No account login, booking submission, or payment was performed. This is an analysis of observable behavior, not access to Hudle's private source code.

## Public structure

- Homepage: https://hudle.in/
- Search: https://hudle.in/venue-search?cityId=&preferred_sports=8&venueName=
- Owner product: https://hudle.in/list-your-sports-venue
- Homepage paths include sport-and-city discovery links, owner acquisition, brand/corporate solutions, community stories, and policy pages.

The homepage presents a fitness headline, live-games counter, three illustrated entry points (community, booking, competition), sport categories, player stories, and a city/sport directory. Its emphasis is both discovery and community.

Sport selection links into a dedicated search route. The inspected football link sets preferred_sports=8; cityId and venueName are empty. Search exposes venue name, sport, and city controls with a Submit action. The fetched page showed an empty state. That does not establish whether the interactive site has no inventory; client rendering or location selection may affect results.

## Design evidence

Public stylesheet inspected: https://hudle.in/website/_next/static/css/29878e4eb37fed16.css

- Colors declared include deep teal #0C6A63, turquoise #40B3A2 and #02B8A5, warm cream #FFF8F0, and pale greens #CBF6D9 / #E9FFE8.
- Font declarations include Inter and bundled Geist families. The exact font used by each element needs rendered inspection.
- Assets include separate sport backgrounds and foreground illustrations, testimonial portraits, and desktop/mobile footer images.
- CSS includes responsive rules around 640, 768, 1024, 1280, and 1536 pixels, plus narrower-screen overrides.
- These observations come from HTML and CSS; pixel dimensions, motion, and exact rendered layout have not been visually verified.

## Frontend architecture

Observed /website/_next/static/ assets, app/layout and app/page bundles, and Next.js streamed script data establish a Next.js App Router frontend for the homepage. Utility CSS is consistent with Tailwind; that tooling identification is an inference. Images are served from website.hudle.in, commonly as WebP.

The search route accepts discovery state in URL parameters. This is a useful pattern for shareable sport and city selections. The public frontend does not establish Hudle's private database schema, booking locks, payment integrations, or server implementation.

## Owner product

Hudle advertises slot management, staff permissions, facility analytics, payment/invoice tracking, report exports, memberships, equipment rentals, and event registrations. Its owner page uses partner logos, product illustrations, testimonials, a demo form, and FAQs. These are advertised capabilities, not independently tested functionality. The page advertises 0% commission, but the full commercial terms were not verified.

## Translation to Maydon

Maydon already documents sport/location discovery, hourly availability, booking history, owner schedules, manual bookings, blocks, payment-status tracking, analytics, moderation, and Telegram reminders.

Recommended sequence:

1. Make discovery the main customer action: sport, location, date, then venues with clear hourly prices and availability.
2. Add shareable discovery parameters to Maydon's URLs while preserving Telegram authentication and booking continuation.
3. Use real venue photography alongside consistent sport illustrations; preserve Maydon's dark-green/lime identity.
4. Add a dedicated owner introduction explaining schedules, manual bookings, blocks, and analytics, with a direct entry to the existing submission flow.
5. Add truthful trust information: real venue photos, location, amenities, booking status, cancellation rules, and support contact.
6. Consider memberships, staff roles, equipment rental, reviews, and community games only after the core booking flow is validated.

Do not present Maydon's payment-status tracking as payment collection. Do not introduce Hudle's numerical claims, testimonials, partner logos, or commercial promises into Maydon.

## Unverified booking flow

A likely implementation model is discovery → venue detail → sport/court → date/time → price summary → authentication → payment/confirmation. This is a proposed model, not a verified recording of Hudle's checkout. Authenticated screens, cancellation/rescheduling interactions, live slot behavior, and payment handling remain unverified.

## Suggested Maydon interface

- Home: location, short booking headline, sport selector, date, nearby venue cards, owner entry.
- Results: active filters, photographs, venue name, distance, hourly price, availability action.
- Venue: gallery, address/map, amenities, hours, booking rules, date and time selection.
- Confirmation: selected venue/time, price, customer contact, explicit pending/confirmed status.
- Owner: daily schedule, pending requests, manual bookings, blocks, payment status, analytics.

This document proposes adaptation; it does not modify or deploy Maydon.
