# schema.org Type Reference

Quick reference for validating JSON-LD structured data. This is not
exhaustive — it covers the types most relevant to brand AI discoverability.

## Organization

Required: `name`
Recommended: `url`, `logo`, `sameAs`, `description`, `email`, `telephone`,
`address`, `foundingDate`, `founder`, `numberOfEmployees`, `slogan`,
`knowsAbout`

Key validation rules:
- `name` must be a non-empty string
- `url` must be a valid URL
- `logo` must be a URL to an image (or `ImageObject`)
- `sameAs` should be an array of URLs to authoritative external profiles
- `address` should be a `PostalAddress` object with `streetAddress`,
  `addressLocality`, `addressRegion`, `postalCode`, `addressCountry`
- `@id` should be a stable URI (e.g. `https://example.com/#organization`)

## LocalBusiness (extends Organization)

Additional required: `address`
Recommended: `openingHoursSpecification`, `priceRange`, `areaServed`,
`hasMap`, `geo`

Key validation rules:
- `openingHoursSpecification` should be an array of `OpeningHoursSpecification`
  with `dayOfWeek`, `opens`, `closes`
- `geo` should be a `GeoCoordinates` with `latitude` and `longitude`
- `priceRange` is a string like `$$` or `Free`

## Product

Required: `name`
Recommended: `description`, `image`, `brand`, `offers`, `aggregateRating`,
`review`, `sku`, `category`, `url`

Key validation rules:
- `offers` must be an `Offer` object (or array), not a string
- `Offer` requires `price` and `priceCurrency`
- `price` must be a number or numeric string
- `aggregateRating` must be an `AggregateRating` with `ratingValue` and
  `reviewCount` or `ratingCount`

## Service

Required: `name`
Recommended: `provider`, `areaServed`, `description`, `offers`,
`serviceType`, `termsOfService`

## Event

Required: `name`, `startDate`, `location`
Recommended: `endDate`, `eventStatus`, `organizer`, `offers`,
`description`, `image`, `url`

Key validation rules:
- `startDate` must be ISO 8601 date
- `location` must be a `Place` or `VirtualLocation`
- If `endDate` is in the past, `eventStatus` should be
  `EventCompleted` or `EventCancelled` — not `EventScheduled`

## Article

Required: `headline`, `datePublished`, `author`
Recommended: `dateModified`, `image`, `publisher`, `description`, `mainEntityOfPage`

Key validation rules:
- `headline` must be <= 110 chars
- `author` must be a `Person` or `Organization`
- `datePublished` and `dateModified` must be ISO 8601

## FAQPage

Required: `mainEntity` (array of `Question` objects)
Each `Question` requires: `name` (the question text), `acceptedAnswer`
(an `Answer` object with `text`)

## BreadcrumbList

Required: `itemListElement` (array of `ListItem`)
Each `ListItem` requires: `position` (integer), `name` (string), `item` (URL)

## WebSite

Required: `name`, `url`
Recommended: `publisher`, `potentialAction` (for `SearchAction`)

## Disambiguating Identifiers

For entity disambiguation, `sameAs` should link to:
- Wikidata entity (e.g. `https://www.wikidata.org/wiki/Q123456`)
- Wikipedia article (e.g. `https://en.wikipedia.org/wiki/Example_Corp`)
- Google Business profile
- LinkedIn company page
- Crunchbase profile
- Official social media (Twitter/X, Facebook, Instagram, YouTube)

At least 2 external authoritative links are recommended for strong
entity disambiguation.
