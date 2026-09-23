import os
import re
import shutil
import urllib.parse
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.blogs.models import Article
from apps.products.models import (
    Category,
    Product,
    ProductImage,
    ProductLike,
    ProductSave,
)


class Command(BaseCommand):
    help = 'Migrate products, categories, blog articles, and media from WordPress/WooCommerce backup.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql',
            type=str,
            default=r'E:\Temp\Sidoos Migration\sbaba5doos9_d7b3_1789657240.sql',
            help='Path to the WordPress MariaDB SQL dump file',
        )
        parser.add_argument(
            '--uploads',
            type=str,
            default=r'E:\Temp\Sidoos Migration\domains\domains\sidoos.ir\public_html\wp-content\uploads',
            help='Path to the WordPress wp-content/uploads directory',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate migration without modifying the database or disk',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products, categories, and articles before migration',
        )
        parser.add_argument(
            '--resolve-links-only',
            action='store_true',
            help='Only resolve internal backlinks on existing articles and products without re-running full migration',
        )

    ESCAPE_MAP = {
        'r': '\r',
        'n': '\n',
        't': '\t',
        '0': '\0',
        "'": "'",
        '"': '"',
        '\\': '\\',
    }

    def parse_sql_row(self, line):
        line = line.strip()
        if line.startswith('('):
            if line.endswith('),') or line.endswith(');'):
                line = line[1:-2]
            elif line.endswith(')'):
                line = line[1:-1]
            else:
                return None
        else:
            return None

        vals = []
        in_str = False
        escape = False
        quote_char = None
        curr = []
        for ch in line:
            if in_str:
                if escape:
                    curr.append(self.ESCAPE_MAP.get(ch, ch))
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == quote_char:
                    in_str = False
                else:
                    curr.append(ch)
            else:
                if ch in ("'", '"'):
                    in_str = True
                    quote_char = ch
                elif ch == ',':
                    vals.append("".join(curr).strip())
                    curr = []
                else:
                    curr.append(ch)
        vals.append("".join(curr).strip())
        return vals

    def clean_persian_slug(self, raw_slug, fallback_title, existing_slugs):
        slug = urllib.parse.unquote(raw_slug or '').strip()
        # Replace characters not matching ^[\w\u0600-\u06FF\s\-]+$
        slug = re.sub(r'[^\w\u0600-\u06FF\s\-]', '-', slug)
        slug = re.sub(r'[\s\-]+', '-', slug).strip('-')

        if not slug:
            fallback = slugify(fallback_title or 'article', allow_unicode=True)
            slug = re.sub(r'[^\w\u0600-\u06FF\s\-]', '-', fallback)
            slug = re.sub(r'[\s\-]+', '-', slug).strip('-') or 'article'

        base = slug[:240]
        cand = base
        idx = 2
        while cand in existing_slugs:
            cand = f"{base[:230]}-{idx}"
            idx += 1
        existing_slugs.add(cand)
        return cand

    def clean_product_slug(self, raw_slug, fallback_title, existing_slugs):
        slug = urllib.parse.unquote(raw_slug or '').strip()
        slug = slugify(slug, allow_unicode=True)
        if not slug:
            slug = slugify(fallback_title or 'product', allow_unicode=True) or 'product'

        base = slug[:240]
        cand = base
        idx = 2
        while cand in existing_slugs:
            cand = f"{base[:230]}-{idx}"
            idx += 1
        existing_slugs.add(cand)
        return cand

    def clean_category_slug(self, raw_slug, fallback_name, existing_slugs):
        slug = urllib.parse.unquote(raw_slug or '').strip()
        slug = slugify(slug, allow_unicode=True)
        if not slug:
            slug = slugify(fallback_name or 'category', allow_unicode=True) or 'category'

        base = slug[:240]
        cand = base
        idx = 2
        while cand in existing_slugs:
            cand = f"{base[:230]}-{idx}"
            idx += 1
        existing_slugs.add(cand)
        return cand

    def clean_canonical_url(self, raw_url):
        if not raw_url or not isinstance(raw_url, str):
            return ""
        url = raw_url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return ""
        try:
            from django.core.validators import URLValidator
            validator = URLValidator()
            validator(url)
            return url[:500]
        except Exception:
            return ""

    def clean_seo_title(self, raw_title, fallback_title):
        if not raw_title or not isinstance(raw_title, str):
            return fallback_title[:200]
        text = self.clean_plain_text(raw_title)
        # Replace %title% with fallback_title
        text = re.sub(r'%title%', fallback_title, text, flags=re.IGNORECASE)
        # Remove known Rank Math / Yoast tokens
        tokens_to_remove = [
            r'%sep\s*%', r'%sitename%', r'%date%', r'%currentdate%',
            r'%currentday%', r'%currentmonth%', r'%currentyear%',
            r'%currenttime(?:\([^)]*\))?%', r'%sitedesc%', r'%org_name%',
            r'%post_thumbnail%', r'%search_query%', r'%filename%',
            r'%count\([^)]*\)%', r'%arch_query\s*%', r'%\s*se%', r'%\s*%'
        ]
        for pattern in tokens_to_remove:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        # Strip internal shortlinks
        text = re.sub(r'https?://[^\s,]+(?:\?p=\d+)?', ' ', text)
        # Strip appended brand suffix since templates already append it
        text = re.sub(r'[\s\|\-]+سیدوس\s*$', '', text).strip()
        # Clean up punctuation and whitespace
        text = re.sub(r'[\s,\|\-]+$', '', text)
        text = re.sub(r'^[\s,\|\-]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text or len(text) < 2:
            return fallback_title[:200]
        return text[:200]

    def clean_seo_description(self, raw_desc, fallback_desc=""):
        target = raw_desc or fallback_desc
        if not target or not isinstance(target, str):
            return ""
        text = self.clean_plain_text(target)
        tokens_to_remove = [
            r'%sep\s*%', r'%sitename%', r'%date%', r'%currentdate%',
            r'%currentday%', r'%currentmonth%', r'%currentyear%',
            r'%currenttime(?:\([^)]*\))?%', r'%sitedesc%', r'%org_name%',
            r'%post_thumbnail%', r'%search_query%', r'%filename%',
            r'%count\([^)]*\)%', r'%arch_query\s*%', r'%\s*se%', r'%\s*%'
        ]
        for pattern in tokens_to_remove:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'^[\s,\|\-]+|[\s,\|\-]+$', '', text)
        return text[:300]


    def wpautop(self, tee, br=True):
        if not tee or not tee.strip():
            return ""
        tee = tee.replace('\r\n', '\n').replace('\r', '\n')
        if '\n' not in tee:
            return tee

        blocks = '(?:table|thead|tfoot|caption|col|colgroup|tbody|tr|td|th|div|dl|dd|dt|ul|ol|li|pre|form|map|area|blockquote|address|math|style|p|h[1-6]|hr|fieldset|legend|section|article|aside|hgroup|header|footer|nav|figure|figcaption|details|menu|summary|video)'
        pieces = re.split(r'(<(?:pre|code)[^>]*>.*?</(?:pre|code)>)', tee, flags=re.DOTALL | re.IGNORECASE)

        output = []
        for i, piece in enumerate(pieces):
            if i % 2 == 1:
                output.append(piece)
                continue
            p = piece
            if not p.strip():
                output.append(p)
                continue
            p = re.sub(r'(<' + blocks + r'[^>]*>)', r'\n\1', p)
            p = re.sub(r'(</' + blocks + r'>)', r'\1\n\n', p)
            p = re.sub(r'\n[ \t\r\f\v]*\n+', '\n\n', p)
            paragraphs = [x.strip() for x in p.split('\n\n') if x.strip()]
            new_paras = []
            for para in paragraphs:
                if re.match(r'^\s*</?' + blocks, para, re.IGNORECASE):
                    new_paras.append(para)
                else:
                    if br:
                        para = para.replace('\n', '<br />\n')
                    new_paras.append(f'<p>{para}</p>')
            output.append("\n\n".join(new_paras))
        result = "".join(output)
        # Clean up any misplaced <p></tag></p> or <p><tag></p>
        result = re.sub(r'<p>\s*(</?(?:' + blocks + r')[^>]*>)\s*</p>', r'\1', result, flags=re.IGNORECASE)
        result = re.sub(r'<p>\s*</p>', '', result)
        return result

    def clean_content(self, text):
        if not text:
            return ""

        # A. Transform [caption ...]<img ... /> caption[/caption]
        def caption_sub(match):
            inner = match.group(1).strip()
            media_match = re.search(r'(?:<a\s+[^>]*>)?\s*<img\s+[^>]*\/?>\s*(?:<\/a>)?', inner, re.IGNORECASE)
            if media_match:
                media_html = media_match.group(0).strip()
                caption_text = inner.replace(media_html, '').strip()
                caption_text = re.sub(r'^(?:<span[^>]*>|<strong>|<p>)+', '', caption_text)
                caption_text = re.sub(r'(?:<\/span>|<\/strong>|<\/p>)+$', '', caption_text).strip()
                if caption_text:
                    return f'<figure class="wp-caption my-4 text-center">{media_html}<figcaption class="wp-caption-text mt-2 text-sm text-center">{caption_text}</figcaption></figure>'
                return f'<figure class="wp-caption my-4 text-center">{media_html}</figure>'
            return inner

        text = re.sub(r'\[caption(?:\s+[^\]]*)?\](.*?)\[/caption\]', caption_sub, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\[/?caption[^\]]*\]', '', text, flags=re.IGNORECASE)

        # B. Transform [video ... mp4="..."][/video]
        def video_sub(match):
            attrs = match.group(1) or ""
            mp4_m = re.search(r'mp4=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
            if mp4_m:
                v_url = mp4_m.group(1)
                v_url = re.sub(r'https?://(?:www\.)?sidoos\.ir/wp-content/uploads/', '/media/uploads/', v_url)
                return f'<div class="my-4 text-center"><video controls class="w-100 rounded" style="max-width:100%; height:auto;" preload="metadata"><source src="{v_url}" type="video/mp4">مرورگر شما از پخش ویدیو پشتیبانی نمی‌کند.</video></div>'
            return ''

        text = re.sub(r'\[video(?:\s+([^\]]*))?\](?:\[/video\])?', video_sub, text, flags=re.IGNORECASE)
        # C. Remove images that have 🌸 or 🍃 in alt text
        text = re.sub(r'<img[^>]*alt=[\"\'][^\"\']*[🌸🍃][^\"\']*[\"\'][^>]*\/?>', '', text)
        text = re.sub(r'<img\s+[^>]*?[🌸🍃][^>]*?\/?>', '', text)
        # Convert any other WordPress SVG emoji image into its plain alt text so it never renders as a huge block image
        text = re.sub(r'<img[^>]*class=[\"\'][^\"\']*emoji[^\"\']*[\"\'][^>]*alt=[\"\']([^\"\']*)[\"\'][^>]*\/?>', r'\1', text)
        text = re.sub(r'<img[^>]*alt=[\"\']([^\"\']*)[\"\'][^>]*class=[\"\'][^\"\']*emoji[^\"\']*[\"\'][^>]*\/?>', r'\1', text)

        # D. Rewrite legacy WordPress upload URLs to /media/uploads/
        text = re.sub(r'https?://(?:www\.)?sidoos\.ir/wp-content/uploads/', '/media/uploads/', text)
        text = re.sub(r'//sidoos\.ir/wp-content/uploads/', '/media/uploads/', text)
        text = re.sub(r'/wp-content/uploads/', '/media/uploads/', text)

        # E. Clean empty paragraphs and excess spaces
        text = re.sub(r'<p>\s*(?:&nbsp;|\s)*\s*</p>', '', text)

        # F. Apply wpautop
        text = self.wpautop(text)

        return text.strip()

    def clean_plain_text(self, text):
        if not text:
            return ""
        # Remove shortcodes first
        text = re.sub(r'\[/?(?:caption|video|audio|gallery|embed)[^\]]*\]', '', text, flags=re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def parse_datetime_safe(self, dt_str):
        if not dt_str or dt_str.startswith('0000'):
            return timezone.now()
        try:
            naive = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            tz = timezone.get_current_timezone()
            return timezone.make_aware(naive, tz)
        except Exception:
            return timezone.now()

    def resolve_all_backlinks(self, dry_run=False):
        self.stdout.write("Resolving internal backlinks in Articles and Products...")

        products_by_slug = {p.slug.strip('/'): p for p in Product.objects.all()}
        articles_by_slug = {a.slug.strip('/'): a for a in Article.objects.all()}
        categories_by_slug = {c.slug.strip('/'): c for c in Category.objects.all()}

        all_products = list(Product.objects.all())
        all_articles = list(Article.objects.all())

        def resolve_url(url, anchor_text=""):
            parsed = urllib.parse.urlparse(url)
            raw_path = parsed.path.strip('/')
            if not raw_path:
                return ('HOME', '/', 'صفحه اصلی')

            slug = urllib.parse.unquote(raw_path).strip('/')

            # 1. Exact match on Product slug
            if slug in products_by_slug:
                p = products_by_slug[slug]
                return ('PRODUCT_EXACT', f'/products/{p.slug}/', p.name)

            # 2. Exact match on Article slug
            if slug in articles_by_slug:
                a = articles_by_slug[slug]
                return ('ARTICLE_EXACT', f'/blogs/{a.slug}/', a.title)

            # 3. Exact match on Category slug
            if slug in categories_by_slug:
                c = categories_by_slug[slug]
                return ('CATEGORY_EXACT', f'/products/?category={c.slug}', c.name)

            # 4. Normalized slug match
            norm_slug = re.sub(r'[\s\-_]+', '-', slug.lower())
            for p_slug, p in products_by_slug.items():
                if re.sub(r'[\s\-_]+', '-', p_slug.lower()) == norm_slug:
                    return ('PRODUCT_NORM', f'/products/{p.slug}/', p.name)

            for a_slug, a in articles_by_slug.items():
                if re.sub(r'[\s\-_]+', '-', a_slug.lower()) == norm_slug:
                    return ('ARTICLE_NORM', f'/blogs/{a.slug}/', a.title)

            # 5. Fuzzy match against Products (similarity >= 0.65)
            best_prod = None
            best_prod_score = 0.0
            slug_tokens = set([w.lower() for w in re.split(r'[\s\-_]+', slug) if len(w) > 2])

            for p in all_products:
                p_tokens = set([w.lower() for w in re.split(r'[\s\-_]+', f"{p.slug} {p.name} {p.meta_title}") if len(w) > 2])
                overlap = len(slug_tokens & p_tokens)
                token_ratio = overlap / max(len(slug_tokens), 1)

                sim_slug = SequenceMatcher(None, slug.lower(), p.slug.lower()).ratio()
                sim_name = SequenceMatcher(None, slug.lower(), p.name.lower()).ratio()
                sim_anchor = SequenceMatcher(None, anchor_text.lower(), p.name.lower()).ratio() if anchor_text else 0

                score = max(sim_slug, sim_name, sim_anchor) + (0.25 if token_ratio >= 0.5 else 0.0)
                if score > best_prod_score:
                    best_prod_score = score
                    best_prod = p

            if best_prod_score >= 0.65 and best_prod:
                return ('PRODUCT_FUZZY', f'/products/{best_prod.slug}/', best_prod.name)

            # 6. Fuzzy match against Articles (similarity >= 0.65)
            best_art = None
            best_art_score = 0.0
            for a in all_articles:
                sim_slug = SequenceMatcher(None, slug.lower(), a.slug.lower()).ratio()
                sim_title = SequenceMatcher(None, slug.lower(), a.title.lower()).ratio()
                sim_anchor = SequenceMatcher(None, anchor_text.lower(), a.title.lower()).ratio() if anchor_text else 0
                score = max(sim_slug, sim_title, sim_anchor)
                if score > best_art_score:
                    best_art_score = score
                    best_art = a

            if best_art_score >= 0.65 and best_art:
                return ('ARTICLE_FUZZY', f'/blogs/{best_art.slug}/', best_art.title)

            # 7. Unresolvable dead link -> unwrap
            return ('UNWRAP', None, None)

        def rewrite_html_links(html):
            if not html:
                return html, {}

            counts = {}

            def repl(match):
                full_tag = match.group(0)
                tag_attrs = match.group(1)
                inner_content = match.group(2)
                anchor_text = re.sub(r'<[^>]+>', '', inner_content).strip()

                href_m = re.search(r'href=[\"\']([^\"\']+)[\"\']', tag_attrs, re.IGNORECASE)
                if not href_m:
                    return full_tag

                href = href_m.group(1).strip()

                is_internal = re.match(r'^https?://(?:www\.)?sidoos\.ir(?:/|$)', href, re.IGNORECASE)
                if not is_internal:
                    return full_tag

                if '/media/' in href or '/wp-content/' in href or '/wp-admin/' in href:
                    return full_tag

                res_type, new_url, _ = resolve_url(href, anchor_text)
                counts[res_type] = counts.get(res_type, 0) + 1

                if res_type == 'UNWRAP' or not new_url:
                    # Remove the <a> wrapper and preserve anchor text
                    return inner_content

                new_attrs = re.sub(
                    r'href=[\"\'][^\"\']+[\"\']',
                    f'href="{new_url}"',
                    tag_attrs,
                    count=1,
                    flags=re.IGNORECASE,
                )
                return f'<a{new_attrs}>{inner_content}</a>'

            pattern = re.compile(r'<a(\s+[^>]*?)>(.*?)<\/a>', re.DOTALL | re.IGNORECASE)
            new_html = pattern.sub(repl, html)
            return new_html, counts

        total_art_links = {}
        updated_articles = 0
        for a in Article.objects.all():
            new_content, counts = rewrite_html_links(a.content)
            for k, v in counts.items():
                total_art_links[k] = total_art_links.get(k, 0) + v
            if new_content != a.content:
                updated_articles += 1
                if not dry_run:
                    a.content = new_content
                    a.save(update_fields=['content'])

        total_prod_links = {}
        updated_products = 0
        for p in Product.objects.all():
            new_desc, counts = rewrite_html_links(p.description)
            for k, v in counts.items():
                total_prod_links[k] = total_prod_links.get(k, 0) + v
            if new_desc != p.description:
                updated_products += 1
                if not dry_run:
                    p.description = new_desc
                    p.save(update_fields=['description'])

        self.stdout.write(f"  Articles modified: {updated_articles} / {len(all_articles)}, Products modified: {updated_products} / {len(all_products)}")
        for k, v in sorted(total_art_links.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"    - {k}: {v}")

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if options.get('resolve_links_only'):
            self.resolve_all_backlinks(dry_run=dry_run)
            return

        sql_path = options['sql']
        uploads_dir = options['uploads']
        clear_existing = options['clear']

        if not os.path.isfile(sql_path):
            self.stderr.write(self.style.ERROR(f"SQL file not found: {sql_path}"))
            return

        if not os.path.isdir(uploads_dir):
            self.stderr.write(self.style.ERROR(f"Uploads dir not found: {uploads_dir}"))
            return

        self.stdout.write(self.style.SUCCESS(f"=== Starting WordPress migration from {sql_path} ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Simulating migration. No database changes will be saved."))

        # 1. Parse WordPress tables
        self.stdout.write("Reading WordPress SQL dump (Pass 1: structure & posts)...")
        terms = {}
        term_tax = {}
        term_rels = defaultdict(list)
        products = {}
        articles = {}
        attachments = {}

        with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
            curr_table = None
            for line in f:
                if 'INSERT INTO `zzP5k_terms` VALUES' in line:
                    curr_table = 'terms'
                    continue
                elif 'INSERT INTO `zzP5k_term_taxonomy` VALUES' in line:
                    curr_table = 'term_taxonomy'
                    continue
                elif 'INSERT INTO `zzP5k_term_relationships` VALUES' in line:
                    curr_table = 'term_relationships'
                    continue
                elif 'INSERT INTO `zzP5k_posts` VALUES' in line:
                    curr_table = 'posts'
                    continue
                elif line.startswith('INSERT INTO') or line.startswith('/*!40000') or line.startswith('--'):
                    curr_table = None
                    continue

                if curr_table == 'terms':
                    v = self.parse_sql_row(line)
                    if v and len(v) >= 3:
                        tid = int(v[0])
                        terms[tid] = {
                            'name': v[1].strip("'"),
                            'slug': urllib.parse.unquote(v[2].strip("'")),
                        }
                elif curr_table == 'term_taxonomy':
                    v = self.parse_sql_row(line)
                    if v and len(v) >= 5:
                        ttid = int(v[0])
                        term_tax[ttid] = {
                            'term_id': int(v[1]),
                            'taxonomy': v[2].strip("'"),
                            'parent': int(v[4]),
                        }
                elif curr_table == 'term_relationships':
                    v = self.parse_sql_row(line)
                    if v and len(v) >= 2:
                        obj_id = int(v[0])
                        ttid = int(v[1])
                        term_rels[obj_id].append(ttid)
                elif curr_table == 'posts':
                    v = self.parse_sql_row(line)
                    if v and len(v) >= 21:
                        pid = int(v[0])
                        pt = v[20].strip("'")
                        st = v[7].strip("'")
                        if pt == 'product':
                            products[pid] = {
                                'id': pid,
                                'title': v[5].strip("'"),
                                'slug': v[11].strip("'"),
                                'content': v[4].strip("'"),
                                'excerpt': v[6].strip("'"),
                                'status': st,
                                'date': v[2].strip("'"),
                                'modified': v[14].strip("'"),
                            }
                        elif pt == 'post':
                            articles[pid] = {
                                'id': pid,
                                'title': v[5].strip("'"),
                                'slug': v[11].strip("'"),
                                'content': v[4].strip("'"),
                                'excerpt': v[6].strip("'"),
                                'status': st,
                                'date': v[2].strip("'"),
                                'modified': v[14].strip("'"),
                            }
                        elif pt == 'attachment':
                            attachments[pid] = {
                                'id': pid,
                                'title': v[5].strip("'"),
                                'guid': v[18].strip("'"),
                            }

        self.stdout.write(f"  Found: {len(products)} products, {len(articles)} articles, {len(attachments)} attachments, {len(terms)} terms.")

        # Pass 2: Collect meta
        self.stdout.write("Reading WordPress SQL dump (Pass 2: postmeta)...")
        needed_pids = set(products.keys()) | set(articles.keys()) | set(attachments.keys())
        postmeta = defaultdict(dict)

        with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
            curr_table = None
            for line in f:
                if 'INSERT INTO `zzP5k_postmeta` VALUES' in line:
                    curr_table = 'postmeta'
                    continue
                elif line.startswith('INSERT INTO') or line.startswith('/*!40000') or line.startswith('--'):
                    curr_table = None
                    continue

                if curr_table == 'postmeta':
                    v = self.parse_sql_row(line)
                    if v and len(v) >= 4:
                        try:
                            pid = int(v[1])
                            if pid in needed_pids:
                                k = v[2].strip("'")
                                val = v[3].strip("'")
                                postmeta[pid][k] = val
                        except ValueError:
                            pass

        self.stdout.write(f"  Loaded postmeta for {len(postmeta)} records.")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("[SUCCESS] Dry run completed: All data parsed successfully!"))
            return

        # Prepare creator
        creator = User.objects.filter(is_superuser=True).first() or User.objects.first()

        # Clear existing data if requested
        if clear_existing:
            self.stdout.write("Clearing existing mock products, categories, and articles...")
            ProductLike.objects.all().delete()
            ProductSave.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Article.objects.all().delete()

        # 2. Migrate Product Categories
        self.stdout.write("Migrating Product Categories...")
        # Get product_cat entries from term_tax
        # Sort so parents come before children
        cat_items = []
        for ttid, tax_info in term_tax.items():
            if tax_info['taxonomy'] == 'product_cat':
                tid = tax_info['term_id']
                if tid in terms:
                    cat_items.append({
                        'ttid': ttid,
                        'term_id': tid,
                        'parent_tid': tax_info['parent'],
                        'name': terms[tid]['name'],
                        'slug': terms[tid]['slug'],
                    })

        # Build tree order
        cat_by_tid = {c['term_id']: c for c in cat_items}
        cat_django_map = {} # term_id -> Category instance
        existing_cat_slugs = set(Category.objects.values_list('slug', flat=True))

        def create_category_node(tid, depth=0):
            if tid in cat_django_map:
                return cat_django_map[tid]
            if tid not in cat_by_tid:
                return None
            info = cat_by_tid[tid]
            parent_obj = None
            if info['parent_tid'] and info['parent_tid'] in cat_by_tid and info['parent_tid'] != tid:
                parent_obj = create_category_node(info['parent_tid'], depth + 1)

            c_slug = self.clean_category_slug(info['slug'], info['name'], existing_cat_slugs)
            cat_obj, created = Category.objects.get_or_create(
                name=info['name'],
                parent=parent_obj,
                defaults={
                    'slug': c_slug,
                    'creator': creator,
                }
            )
            cat_django_map[tid] = cat_obj
            return cat_obj

        for c in cat_items:
            create_category_node(c['term_id'])

        self.stdout.write(f"  Migrated {len(cat_django_map)} product categories.")

        # Prepare media destination directories
        covers_dir = os.path.join(settings.MEDIA_ROOT, 'products', 'covers')
        images_dir = os.path.join(settings.MEDIA_ROOT, 'products', 'images')
        articles_dir = os.path.join(settings.MEDIA_ROOT, 'blogs', 'articles')
        os.makedirs(covers_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(articles_dir, exist_ok=True)

        def get_media_path(attach_id):
            if not attach_id:
                return None
            try:
                aid = int(attach_id)
            except ValueError:
                return None
            rel_file = postmeta.get(aid, {}).get('_wp_attached_file')
            if not rel_file:
                return None
            full_src = os.path.join(uploads_dir, rel_file.replace('/', os.sep))
            if os.path.isfile(full_src):
                return full_src
            return None

        # 3. Migrate Products
        self.stdout.write("Migrating Products...")
        existing_prod_names = set(Product.objects.values_list('name', flat=True))
        existing_prod_slugs = set(Product.objects.values_list('slug', flat=True))

        created_prod_count = 0
        created_gallery_count = 0

        for pid, pdata in products.items():
            pmeta = postmeta.get(pid, {})
            p_title = pdata['title'].strip() or f"محصول کد {pid}"
            # Ensure unique name
            base_name = p_title[:240]
            cand_name = base_name
            n_idx = 2
            while cand_name in existing_prod_names:
                cand_name = f"{base_name[:230]} {n_idx}"
                n_idx += 1
            existing_prod_names.add(cand_name)

            p_slug = self.clean_product_slug(pdata['slug'], cand_name, existing_prod_slugs)

            # Pricing
            raw_price = pmeta.get('_price', '').strip()
            raw_sale = pmeta.get('_sale_price', '').strip()

            price_num = 0
            if raw_price.isdigit() and int(raw_price) > 0:
                price_num = int(raw_price)

            sale_num = None
            if raw_sale.isdigit() and int(raw_sale) > 0:
                s_val = int(raw_sale)
                if s_val < price_num:
                    sale_num = s_val

            call_for_price = (price_num == 0)
            if call_for_price:
                price_num = 0
                sale_num = None

            # Cover image
            cover_src = get_media_path(pmeta.get('_thumbnail_id'))
            if not cover_src:
                # Fallback to first gallery image if available
                gallery_str = pmeta.get('_product_image_gallery', '').strip()
                if gallery_str:
                    first_gid = gallery_str.split(',')[0].strip()
                    cover_src = get_media_path(first_gid)

            cover_rel = ''
            if cover_src:
                cover_fname = f"p_{pid}_" + os.path.basename(cover_src)
                cover_dst = os.path.join(covers_dir, cover_fname)
                if not os.path.isfile(cover_dst):
                    shutil.copy2(cover_src, cover_dst)
                cover_rel = f"products/covers/{cover_fname}"
            else:
                default_file = os.path.join(covers_dir, "default.jpg")
                if not os.path.isfile(default_file):
                    with open(default_file, "wb") as df:
                        df.write(b"")
                cover_rel = "products/covers/default.jpg"

            # Primary Category
            assigned_cat = None
            p_ttids = term_rels.get(pid, [])
            for ttid in p_ttids:
                if ttid in term_tax and term_tax[ttid]['taxonomy'] == 'product_cat':
                    tid = term_tax[ttid]['term_id']
                    if tid in cat_django_map:
                        assigned_cat = cat_django_map[tid]
                        break

            # Description
            raw_desc = pdata['content'].strip() or pdata['excerpt'].strip()
            desc = self.clean_content(raw_desc) or f"<p>{cand_name}</p>"

            # SEO
            meta_title = self.clean_seo_title(pmeta.get('rank_math_title'), cand_name)
            meta_desc = self.clean_seo_description(pmeta.get('rank_math_description'), pdata['excerpt'])
            canonical = self.clean_canonical_url(pmeta.get('rank_math_canonical_url', ''))

            prod = Product(
                name=cand_name,
                slug=p_slug,
                description=desc,
                price=price_num,
                on_sale_price=sale_num,
                call_for_price=call_for_price,
                published=(pdata['status'] == 'publish'),
                cover_image=cover_rel,
                category=assigned_cat,
                creator=creator,
                meta_title=meta_title[:200],
                meta_description=meta_desc,
                canonical_url=canonical[:500],
                created_at=self.parse_datetime_safe(pdata['date']),
                updated_at=self.parse_datetime_safe(pdata['modified']),
            )

            prod.save()
            created_prod_count += 1

            # Product tags
            prod_tag_names = []
            for ttid in p_ttids:
                if ttid in term_tax and term_tax[ttid]['taxonomy'] == 'product_tag':
                    tid = term_tax[ttid]['term_id']
                    if tid in terms:
                        prod_tag_names.append(terms[tid]['name'])
            if prod_tag_names:
                prod.tags.add(*prod_tag_names)

            # Product Gallery Images
            gallery_str = pmeta.get('_product_image_gallery', '').strip()
            if gallery_str:
                gallery_ids = [gid.strip() for gid in gallery_str.split(',') if gid.strip()]
                for g_idx, gid in enumerate(gallery_ids, 1):
                    g_src = get_media_path(gid)
                    if g_src:
                        g_fname = f"p_{pid}_g_{gid}_" + os.path.basename(g_src)
                        g_dst = os.path.join(images_dir, g_fname)
                        if not os.path.isfile(g_dst):
                            shutil.copy2(g_src, g_dst)
                        ProductImage.objects.create(
                            product=prod,
                            image=f"products/images/{g_fname}",
                            order=g_idx,
                        )
                        created_gallery_count += 1

        self.stdout.write(f"  Migrated {created_prod_count} products and {created_gallery_count} gallery images.")

        # 4. Migrate Blog Articles
        self.stdout.write("Migrating Blog Articles...")
        existing_article_slugs = set(Article.objects.values_list('slug', flat=True))
        created_article_count = 0

        for aid, adata in articles.items():
            ameta = postmeta.get(aid, {})
            a_title = adata['title'].strip() or f"مقاله شماره {aid}"
            a_slug = self.clean_persian_slug(adata['slug'], a_title, existing_article_slugs)

            # Content & summary
            raw_content = adata['content'].strip()
            content = self.clean_content(raw_content) or "<p></p>"

            raw_summary = self.clean_plain_text(adata['excerpt'])
            if not raw_summary:
                raw_summary = self.clean_plain_text(content)[:250] or a_title
            summary = raw_summary[:300]

            # Calculate reading time based on plain text words
            plain_words = len(re.findall(r'[\w\u0600-\u06FF]+', self.clean_plain_text(content)))
            reading_time = max(1, min(60, round(plain_words / 200) or 1))

            # Featured Image
            feat_src = get_media_path(ameta.get('_thumbnail_id'))
            feat_rel = ''
            if feat_src:
                f_fname = f"a_{aid}_" + os.path.basename(feat_src)
                f_dst = os.path.join(articles_dir, f_fname)
                if not os.path.isfile(f_dst):
                    shutil.copy2(feat_src, f_dst)
                feat_rel = f"blogs/articles/{f_fname}"

            # SEO
            meta_title = self.clean_seo_title(ameta.get('rank_math_title'), a_title)
            meta_desc = self.clean_seo_description(ameta.get('rank_math_description'), summary)
            canonical = self.clean_canonical_url(ameta.get('rank_math_canonical_url', ''))

            pub_date = self.parse_datetime_safe(adata['date'])
            is_pub = (adata['status'] == 'publish')

            article = Article(
                title=a_title[:200],
                slug=a_slug,
                summary=summary,
                content=content,
                featured_image=feat_rel if feat_rel else None,
                reading_time=reading_time,
                published_at=pub_date,
                is_published=is_pub,
                meta_title=meta_title[:200],
                meta_description=meta_desc,
                canonical_url=canonical[:500],
                created_at=pub_date,
                updated_at=self.parse_datetime_safe(adata['modified']),
            )

            article.save()
            created_article_count += 1

            # Article tags
            a_ttids = term_rels.get(aid, [])
            post_tag_names = []
            for ttid in a_ttids:
                if ttid in term_tax and term_tax[ttid]['taxonomy'] == 'post_tag':
                    tid = term_tax[ttid]['term_id']
                    if tid in terms:
                        post_tag_names.append(terms[tid]['name'])
            if post_tag_names:
                article.tags.add(*post_tag_names)

        self.stdout.write(f"  Migrated {created_article_count} blog articles.")

        # 5. Resolve internal backlinks
        self.resolve_all_backlinks(dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS(
            f"\n[SUCCESS] Migration Complete!"
            f"\n  - Categories: {Category.objects.count()}"
            f"\n  - Products: {Product.objects.count()}"
            f"\n  - Product Gallery Images: {ProductImage.objects.count()}"
            f"\n  - Blog Articles: {Article.objects.count()}"
        ))
