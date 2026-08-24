PROJECT: Sidoos B2B Wholesale E-commerce
STACK: Django + Custom Frontend
LANGUAGE: Persian / RTL

TARGET USERS:
Mostly older shop owners / wholesalers.
Many users are not highly familiar with technology.
A large portion of traffic comes from mobile.

CORE UX:
Modern visual design + extremely simple UX.

The user should never feel lost.
Important actions must be obvious.
Mobile-first and highly responsive.
Animations are welcome but must never hurt usability.

==================================================
DESIGN SYSTEM
==================================================

Style:
Modern Natural Premium

Colors:

Background:       #F7F7F2
Primary:          #245C43
Primary Dark:     #173D2D
Accent:           #A8C66C
Text:             #202522
Muted Text:       #6E756F
Sale/Attention:   #E87932

Global typography and design tokens belong in base.html.

Navbar and footer are reusable partials:
partials/navbar.html
partials/footer.html

Components inherit the global font from base.html.

==================================================
FINAL HOMEPAGE STRUCTURE
==================================================

1. HERO / SLIDER
----------------
3–4 slides.

Each slide has:
- Image
- Title
- Short description
- One clear CTA

Possible CTAs:
- مشاهده محصولات
- مشاهده تخفیف‌ها
- مشاهده محصولات پرفروش
- مشاهده دسته‌بندی‌ها

Avoid multiple competing CTAs.

Hero should be visually impressive but easy to understand.

Admin must be able to control:
- Image
- Title
- Description
- Button text
- Button URL
- Order
- Active/Inactive

Potential model:
HeroSlide


2. TRUST / WHY SIDOOS
---------------------
A compact section communicating trust and benefits.

Examples:
- تولید ایرانی
- کیفیت محصولات
- تنوع محصولات
- ارسال
- پشتیبانی

Should focus on real business advantages.

Not just decorative trust badges.

Potentially:
TrustFeature / static section


3. FEATURED CATEGORIES
----------------------
Show only a limited number of important categories.

DO NOT show dozens of categories.

Use high-level categories.

Admin controls which categories appear.

Potential model:
FeaturedCategory

A category can optionally have:
- image
- title
- order
- active
- "پرفروش" badge if applicable


4. BEST SELLING PRODUCTS
------------------------
Show selected best-selling products.

Admin must control:
- Which products appear
- Order
- Active/Inactive

Potential model:
HomepageProduct

A product can be assigned to:
- Best Sellers
- Special Offers
- potentially other homepage sections later

Do NOT hard-code these products.


5. SPECIAL OFFERS
-----------------
Dedicated section for heavily discounted / special products.

Use #E87932 carefully for:
- discount badges
- offer labels
- attention elements

Admin controls:
- Products
- Order
- Active/Inactive

Potentially same HomepageProduct mechanism with a section/type.


6. ABOUT SIDOOS
---------------
A short homepage introduction to Sidoos.

Should communicate:
- Manufacturing background
- Iranian production
- Product variety
- Quality
- Experience

This is a SHORT homepage version.

The full company description belongs primarily in the footer / about page.

CTA can be:
"درباره سیدوس"


7. TESTIMONIALS
---------------
Customer reviews / testimonials.

Should only contain real customer feedback.

Admin must be able to add/edit/remove/reorder testimonials.

Potential model:
Testimonial

Fields may include:
- customer name
- text
- rating
- image/avatar if needed
- active
- order


8. MAGAZINE / ARTICLES
----------------------
Add a Magazine / Blog section.

Purpose:
- Educational content
- Product-related articles
- Industry information
- Helpful content
- SEO
- Building trust

Homepage should show a limited number of latest/featured articles.

Potential model:
Article / MagazineArticle

Admin should control:
- title
- slug
- cover image
- excerpt
- content
- publication status
- published date
- featured
- order/category if needed

Homepage should NOT show dozens of articles.

Example:

مجله سیدوس

[Article] [Article] [Article]

مشاهده همه مطالب →


9. FOOTER
---------
Existing custom footer.

==================================================
IMPORTANT ARCHITECTURE
==================================================

Homepage must be dynamic.

Do not hard-code homepage products/categories/slides.

Core future models:

Product
Category
HeroSlide
FeaturedCategory
HomepageProduct
Testimonial
MagazineArticle

Product is a CORE model and will eventually connect to:

- Categories
- Search
- Product listing
- Product detail
- Best sellers
- Special offers
- Cart
- Orders
- Admin

Homepage management should be admin-driven.

For MVP:
Do NOT build a generic Elementor-style page builder.

Keep the architecture explicit and maintainable.

==================================================
CATEGORY UX
==================================================

There are many product categories.

Never expose 100 categories at once.

Use:

High-level categories
        ↓
Subcategories
        ↓
Products
        +
Filters
        +
Search

Category = what the product is.

Filter = properties such as:
- size
- color
- material
- type
etc.

Progressive disclosure should be used.

==================================================
HOMEPAGE FINAL ORDER
==================================================

Navbar

↓
Hero / Slider

↓
Why Sidoos / Trust

↓
Featured Categories

↓
Best Selling Products

↓
Special Offers

↓
About Sidoos

↓
Testimonials

↓
Magazine / Articles

↓
Footer


==================================================
DESIGN PHILOSOPHY
==================================================

The homepage should NOT try to demonstrate every frontend technique.

The goal is:

A professional, trustworthy, modern wholesale store
that an older shop owner can understand immediately.

Modern UI.
Simple UX.
Strong mobile experience.
Clear product discovery.
Clear calls to action.
No unnecessary complexity.