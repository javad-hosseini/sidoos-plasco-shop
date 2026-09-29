/**
 * Sidoos Admin - CKEditor 5 SEO Companion
 *
 * Real-time SEO content analysis for Django Admin (Blogs & Products).
 * Evaluates:
 * - Word Count & Estimated Reading Time
 * - Internal & External Link Distribution & Anchor Quality
 * - Image Audit (Alt-Text Presence & Filename Warning)
 * - Heading Structure (H1 warning inside body, H2/H3 presence)
 * - Readability & Paragraph Length (Wall-of-text & Bullet list checks)
 * - Meta Description / Summary Length Meter (120-160 char sweet spot)
 *
 * Zero build-tool dependencies. 100% Native browser parsing via DOMParser.
 */

(function ($) {
    'use strict';

    // Persian digits converter for friendly UI
    function toPersianDigits(num) {
        if (num === null || num === undefined) return '';
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return String(num).replace(/[0-9]/g, function (d) {
            return persianDigits[d];
        });
    }

    // Debounce helper
    function debounce(func, wait) {
        let timeout;
        return function () {
            const context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function () {
                func.apply(context, args);
            }, wait);
        };
    }

    // Determine current admin context (article vs product)
    function detectContext() {
        if ($('#id_content').length) {
            return {
                type: 'article',
                fieldId: 'id_content',
                minWordsGood: 600,
                minWordsWarn: 300,
                metaDescField: $('#id_meta_description').length ? '#id_meta_description' : '#id_summary'
            };
        }
        if ($('#id_description').length) {
            return {
                type: 'product',
                fieldId: 'id_description',
                minWordsGood: 200,
                minWordsWarn: 80,
                metaDescField: $('#id_meta_description').length ? '#id_meta_description' : '#id_description'
            };
        }
        return null;
    }

    // Build the companion widget HTML
    function createWidgetHtml(ctx) {
        const typeLabel = ctx.type === 'article' ? 'مقاله' : 'محصول';
        const isCollapsed = localStorage.getItem('sidoos_seo_companion_collapsed') === 'true';

        return `
        <div class="seo-companion-card ${isCollapsed ? 'collapsed' : ''}" id="seoCompanionWidget">
            <div class="seo-companion-header" id="seoCompanionHeader" title="برای بستن/باز کردن کلیک کنید">
                <div class="seo-companion-title-wrap">
                    <svg class="seo-companion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                    </svg>
                    <h4 class="seo-companion-title">همیار سئو سیدوس (SEO Companion)</h4>
                </div>
                <div class="seo-companion-header-actions">
                    <span class="seo-score-badge seo-score-warning" id="seoScoreBadge">در حال تحلیل...</span>
                    <button type="button" class="seo-toggle-btn" aria-label="تغییر وضعیت نمایش">▼</button>
                </div>
            </div>

            <div class="seo-quick-strip">
                <div class="seo-quick-item">
                    <span>کلمات:</span>
                    <strong id="seoQuickWords">۰</strong>
                </div>
                <div class="seo-quick-item">
                    <span>زمان مطالعه:</span>
                    <strong id="seoQuickReadingTime">۱ دقیقه</strong>
                </div>
                <div class="seo-quick-item">
                    <span>تصاویر:</span>
                    <strong id="seoQuickImages">۰</strong>
                </div>
                <div class="seo-quick-item">
                    <span>لینک‌ها:</span>
                    <strong id="seoQuickLinks">۰</strong>
                </div>
            </div>

            <div class="seo-companion-body">
                <div class="seo-checks-grid">
                    <!-- 1. Word Count -->
                    <div class="seo-check-item" id="checkWordCount">
                        <div class="seo-check-icon">⏳</div>
                        <div class="seo-check-content">
                            <div class="seo-check-label">
                                <span>تعداد کلمات متن</span>
                                <span class="seo-check-value" id="valWordCount">۰ کلمه</span>
                            </div>
                            <div class="seo-progress-wrap">
                                <div class="seo-progress-bar bg-danger" id="progWordCount" style="width: 5%;"></div>
                            </div>
                            <p class="seo-check-desc" id="descWordCount">در حال بررسی طول محتوا...</p>
                        </div>
                    </div>

                    <!-- 2. Images & Alt Text -->
                    <div class="seo-check-item" id="checkImages">
                        <div class="seo-check-icon">🖼️</div>
                        <div class="seo-check-content">
                            <div class="seo-check-label">
                                <span>تصاویر و متن جایگزین (Alt)</span>
                                <span class="seo-check-value" id="valImages">۰ تصویر</span>
                            </div>
                            <p class="seo-check-desc" id="descImages">تصاویر محتوا بررسی می‌شوند.</p>
                        </div>
                    </div>

                    <!-- 3. Links (Internal & External) -->
                    <div class="seo-check-item" id="checkLinks">
                        <div class="seo-check-icon">🔗</div>
                        <div class="seo-check-content">
                            <div class="seo-check-label">
                                <span>لینک‌های داخلی و خارجی</span>
                                <span class="seo-check-value" id="valLinks">۰ لینک</span>
                            </div>
                            <p class="seo-check-desc" id="descLinks">وضعیت لینک‌سازی بررسی می‌شود.</p>
                        </div>
                    </div>

                    <!-- 4. Heading Structure -->
                    <div class="seo-check-item" id="checkHeadings">
                        <div class="seo-check-icon">📑</div>
                        <div class="seo-check-content">
                            <div class="seo-check-label">
                                <span>ساختار عناوین (H2 / H3)</span>
                                <span class="seo-check-value" id="valHeadings">-</span>
                            </div>
                            <p class="seo-check-desc" id="descHeadings">عدم استفاده از H1 در متن و حضور زیرعناوین بررسی می‌شود.</p>
                        </div>
                    </div>

                    <!-- 5. Readability & Formatting -->
                    <div class="seo-check-item" id="checkReadability">
                        <div class="seo-check-icon">👓</div>
                        <div class="seo-check-content">
                            <div class="seo-check-label">
                                <span>خوانایی و پاراگراف‌ها</span>
                                <span class="seo-check-value" id="valReadability">استاندارد</span>
                            </div>
                            <p class="seo-check-desc" id="descReadability">طول پاراگراف‌ها و استفاده از لیست‌های بالت‌دار بررسی می‌شود.</p>
                        </div>
                    </div>

                    <!-- 6. Meta Description Meter -->
                    <div class="seo-meta-meter" id="checkMetaDesc">
                        <div class="seo-check-label">
                            <span>طول توضیحات سئو (Meta Description)</span>
                            <span class="seo-check-value" id="valMetaDesc">۰ / ۱۶۰ کاراکتر</span>
                        </div>
                        <div class="seo-progress-wrap">
                            <div class="seo-progress-bar bg-warning" id="progMetaDesc" style="width: 0%;"></div>
                        </div>
                        <p class="seo-check-desc" id="descMetaDesc">طول بهینه توضیحات متا برای گوگل بین ۱۲۰ تا ۱۶۰ کاراکتر است.</p>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    // Core Analysis Engine
    function analyzeContent(rawHtml, ctx) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(rawHtml || '', 'text/html');

        // --- 1. Text & Words ---
        const text = (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
        const wordMatches = text.match(/[\w\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+/g) || [];
        const wordCount = wordMatches.length;
        const readingTime = Math.max(1, Math.ceil(wordCount / 180));

        let wordScore = 0;
        let wordStatus = 'danger'; // danger | warning | good
        let wordDesc = '';

        if (wordCount >= ctx.minWordsGood) {
            wordScore = 20;
            wordStatus = 'good';
            wordDesc = `طول محتوا عالی است (${toPersianDigits(wordCount)} کلمه). برای سئو و ایندکس موتورهای جستجو بسیار مناسب است.`;
        } else if (wordCount >= ctx.minWordsWarn) {
            wordScore = 14;
            wordStatus = 'warning';
            wordDesc = `طول محتوا قابل قبول است (${toPersianDigits(wordCount)} کلمه)، اما رساندن آن به بیش از ${toPersianDigits(ctx.minWordsGood)} کلمه به رتبه‌بندی بهتر کمک می‌کند.`;
        } else {
            wordScore = Math.round((wordCount / ctx.minWordsWarn) * 10);
            wordStatus = 'danger';
            wordDesc = `محتوا کوتاه است (${toPersianDigits(wordCount)} کلمه). حداقل ${toPersianDigits(ctx.minWordsWarn)} کلمه برای جلوگیری از جریمه محتوای ضعیف (Thin Content) پیشنهاد می‌شود.`;
        }

        // --- 2. Images & Alt Text ---
        const images = doc.querySelectorAll('img');
        const imgCount = images.length;
        let missingAltCount = 0;
        let filenameAltCount = 0;

        images.forEach(img => {
            const alt = (img.getAttribute('alt') || '').trim();
            if (!alt) {
                missingAltCount++;
            } else if (/\.(jpe?g|png|webp|gif|svg)$/i.test(alt) || /^img_\d+$/i.test(alt) || /^image$/i.test(alt)) {
                filenameAltCount++;
            }
        });

        let imgScore = 0;
        let imgStatus = 'good';
        let imgDesc = '';

        if (imgCount === 0) {
            imgScore = 12;
            imgStatus = 'warning';
            imgDesc = 'هیچ تصویری در متن نیست. افزودن حداقل یک تصویر به تعامل و ماندگاری کاربر در صفحه کمک می‌کند.';
        } else if (missingAltCount > 0) {
            imgScore = 6;
            imgStatus = 'danger';
            imgDesc = `${toPersianDigits(missingAltCount)} تصویر فاقد متن جایگزین (Alt) است! حتماً برای تمام تصاویر متن توصیفی وارد کنید.`;
        } else if (filenameAltCount > 0) {
            imgScore = 14;
            imgStatus = 'warning';
            imgDesc = 'برخی تصاویر از نام فایل به عنوان متن جایگزین استفاده کرده‌اند. متن را به عبارتی مفهومی تغییر دهید.';
        } else {
            imgScore = 20;
            imgStatus = 'good';
            imgDesc = `تمام ${toPersianDigits(imgCount)} تصویر متن جایگزین مناسب دارند ✅`;
        }

        // --- 3. Links Analysis ---
        const links = doc.querySelectorAll('a[href]');
        let internalLinks = 0;
        let externalLinks = 0;
        let badAnchors = 0;
        const currentHost = window.location.hostname;

        links.forEach(a => {
            const href = (a.getAttribute('href') || '').trim();
            const anchorText = (a.textContent || '').trim();

            if (!href || href === '#') {
                badAnchors++;
                return;
            }

            // Check generic anchor text
            if (/^(اینجا|این لینک|کلیک کنید|لینک|اینجا کلیک کنید|here|click here|link)$/i.test(anchorText)) {
                badAnchors++;
            }

            if (href.startsWith('/') || href.startsWith('#') || href.includes('sidoos.ir') || (currentHost && href.includes(currentHost))) {
                internalLinks++;
            } else if (href.startsWith('http://') || href.startsWith('https://')) {
                externalLinks++;
            } else {
                internalLinks++;
            }
        });

        let linkScore = 0;
        let linkStatus = 'good';
        let linkDesc = '';

        if (badAnchors > 0) {
            linkScore = 8;
            linkStatus = 'danger';
            linkDesc = `${toPersianDigits(badAnchors)} لینک با آدرس خالی (#) یا متن عمومی (مانند «اینجا») یافت شد. از انکرتکست‌های معنادار استفاده کنید.`;
        } else if (internalLinks > 0 && externalLinks > 0) {
            linkScore = 20;
            linkStatus = 'good';
            linkDesc = `ترکیب عالی: ${toPersianDigits(internalLinks)} لینک داخلی و ${toPersianDigits(externalLinks)} لینک خارجی معتبر ثبت شده است.`;
        } else if (internalLinks > 0) {
            linkScore = 16;
            linkStatus = 'good';
            linkDesc = `${toPersianDigits(internalLinks)} لینک داخلی ثبت شده است. در صورت نیاز ارجاع به منبع خارجی نیز اضافه کنید.`;
        } else if (externalLinks > 0) {
            linkScore = 14;
            linkStatus = 'warning';
            linkDesc = `${toPersianDigits(externalLinks)} لینک خارجی ثبت شده، اما هیچ لینک داخلی به سایر صفحات سایت سیدوس داده نشده است.`;
        } else {
            linkScore = 8;
            linkStatus = 'warning';
            linkDesc = 'هیچ لینکی در متن وجود ندارد. لینک‌سازی داخلی به محصولات یا مقالات دیگر سیدوس سئوی سایت را تقویت می‌کند.';
        }

        // --- 4. Heading Structure ---
        const h1s = doc.querySelectorAll('h1');
        const h2s = doc.querySelectorAll('h2');
        const h3s = doc.querySelectorAll('h3');

        let headingScore = 0;
        let headingStatus = 'good';
        let headingDesc = '';

        if (h1s.length > 0) {
            headingScore = 4;
            headingStatus = 'danger';
            headingDesc = 'خطای سئو: تگ H1 در متن استفاده شده است! عنوان صفحه خود H1 است. لطفا عنوان‌های داخل متن را به H2 یا H3 تغییر دهید.';
        } else if (wordCount > 250 && h2s.length === 0) {
            headingScore = 10;
            headingStatus = 'warning';
            headingDesc = 'متن طولانی است ولی فاقد زیرعنوان H2 است. برای بخش‌بندی و درک بهتر گوگل از H2 استفاده کنید.';
        } else if (h2s.length > 0) {
            headingScore = 20;
            headingStatus = 'good';
            headingDesc = `ساختار عناوین عالی است (${toPersianDigits(h2s.length)} تیتر H2 و ${toPersianDigits(h3s.length)} تیتر H3).`;
        } else {
            headingScore = 16;
            headingStatus = 'good';
            headingDesc = 'ساختار عناوین قابل قبول است.';
        }

        // --- 5. Readability & Paragraphs ---
        const paragraphs = doc.querySelectorAll('p');
        let longParagraphCount = 0;
        paragraphs.forEach(p => {
            const pWords = ((p.textContent || '').match(/[\w\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+/g) || []).length;
            if (pWords > 120) {
                longParagraphCount++;
            }
        });

        const lists = doc.querySelectorAll('ul, ol');
        let readScore = 10;
        let readStatus = 'good';
        let readDesc = 'پاراگراف‌ها روان و خوانا هستند.';

        if (longParagraphCount > 0) {
            readScore = 5;
            readStatus = 'warning';
            readDesc = `${toPersianDigits(longParagraphCount)} پاراگراف بسیار طولانی (بیش از ۱۲۰ کلمه) است. برای خوانایی بهتر در موبایل آن‌ها را بشکنید.`;
        } else if (wordCount > 400 && lists.length === 0) {
            readScore = 8;
            readStatus = 'warning';
            readDesc = 'برای نمایش در بخش نتایج ویژه گوگل (Featured Snippets)، استفاده از یک لیست بالت‌دار پیشنهاد می‌شود.';
        } else if (lists.length > 0) {
            readScore = 10;
            readStatus = 'good';
            readDesc = `استفاده مناسب از لیست و پاراگراف‌های تفکیک‌شده (${toPersianDigits(lists.length)} لیست بالت‌دار).`;
        }

        // --- 6. Meta Description Meter ---
        const metaVal = ($(ctx.metaDescField).val() || '').trim();
        const metaLen = metaVal.length;
        let metaScore = 0;
        let metaStatus = 'warning';
        let metaDesc = '';

        if (metaLen === 0) {
            metaScore = 0;
            metaStatus = 'danger';
            metaDesc = 'توضیحات متا خالی است! گوگل به طور تصادفی متنی از صفحه را نشان خواهد داد.';
        } else if (metaLen < 70) {
            metaScore = 5;
            metaStatus = 'warning';
            metaDesc = `توضیحات متا با ${toPersianDigits(metaLen)} کاراکتر خیلی کوتاه است. حداقل ۱۲۰ کاراکتر توصیه می‌شود.`;
        } else if (metaLen <= 160) {
            metaScore = 10;
            metaStatus = 'good';
            metaDesc = `طول توضیحات متا (${toPersianDigits(metaLen)} کاراکتر) در محدوده طلایی گوگل (۱۲۰ تا ۱۶۰ کاراکتر) است.`;
        } else {
            metaScore = 5;
            metaStatus = 'danger';
            metaDesc = `توضیحات متا با ${toPersianDigits(metaLen)} کاراکتر طولانی است و در نتایج گوگل بریده (Truncate) خواهد شد.`;
        }

        // Total score calculation (max 100)
        const totalScore = Math.min(100, Math.max(0, wordScore + imgScore + linkScore + headingScore + readScore + metaScore));

        return {
            totalScore: totalScore,
            words: { count: wordCount, readingTime: readingTime, status: wordStatus, desc: wordDesc },
            images: { count: imgCount, missingAlt: missingAltCount, status: imgStatus, desc: imgDesc },
            links: { internal: internalLinks, external: externalLinks, bad: badAnchors, status: linkStatus, desc: linkDesc },
            headings: { h1: h1s.length, h2: h2s.length, h3: h3s.length, status: headingStatus, desc: headingDesc },
            readability: { longP: longParagraphCount, lists: lists.length, status: readStatus, desc: readDesc },
            meta: { length: metaLen, status: metaStatus, desc: metaDesc }
        };
    }

    // Render analysis results into UI
    function renderResults(res, ctx) {
        // Overall Score Badge
        const $badge = $('#seoScoreBadge');
        $badge.removeClass('seo-score-good seo-score-warning seo-score-danger');

        let scoreLabel = 'ضعیف';
        if (res.totalScore >= 80) {
            $badge.addClass('seo-score-good');
            scoreLabel = 'عالی';
        } else if (res.totalScore >= 50) {
            $badge.addClass('seo-score-warning');
            scoreLabel = 'نیاز به بهبود';
        } else {
            $badge.addClass('seo-score-danger');
            scoreLabel = 'ضعیف';
        }
        $badge.text(`امتیاز سئو: ${toPersianDigits(res.totalScore)} / ۱۰۰ (${scoreLabel})`);

        // Quick strip
        $('#seoQuickWords').text(toPersianDigits(res.words.count));
        $('#seoQuickReadingTime').text(`${toPersianDigits(res.words.readingTime)} دقیقه`);
        $('#seoQuickImages').text(toPersianDigits(res.images.count));
        $('#seoQuickLinks').text(toPersianDigits(res.links.internal + res.links.external));

        // 1. Words
        updateCheckCard('#checkWordCount', '#valWordCount', '#descWordCount',
            `${toPersianDigits(res.words.count)} کلمه`,
            res.words.desc,
            res.words.status
        );
        const wordPct = Math.min(100, Math.round((res.words.count / ctx.minWordsGood) * 100));
        $('#progWordCount')
            .css('width', `${wordPct}%`)
            .attr('class', `seo-progress-bar bg-${res.words.status}`);

        // 2. Images
        updateCheckCard('#checkImages', '#valImages', '#descImages',
            `${toPersianDigits(res.images.count)} تصویر`,
            res.images.desc,
            res.images.status
        );

        // 3. Links
        updateCheckCard('#checkLinks', '#valLinks', '#descLinks',
            `${toPersianDigits(res.links.internal)} داخلی | ${toPersianDigits(res.links.external)} خارجی`,
            res.links.desc,
            res.links.status
        );

        // 4. Headings
        const headingVal = res.headings.h1 > 0 ? '❌ تگ H1 دارد' : `${toPersianDigits(res.headings.h2)} تیتر H2`;
        updateCheckCard('#checkHeadings', '#valHeadings', '#descHeadings',
            headingVal,
            res.headings.desc,
            res.headings.status
        );

        // 5. Readability
        updateCheckCard('#checkReadability', '#valReadability', '#descReadability',
            res.readability.status === 'good' ? 'استاندارد ✅' : 'نیاز به بررسی',
            res.readability.desc,
            res.readability.status
        );

        // 6. Meta Description Meter
        const metaPct = Math.min(100, Math.round((res.meta.length / 160) * 100));
        $('#valMetaDesc').text(`${toPersianDigits(res.meta.length)} / ۱۶۰ کاراکتر`);
        $('#descMetaDesc').text(res.meta.desc);
        $('#progMetaDesc')
            .css('width', `${metaPct}%`)
            .attr('class', `seo-progress-bar bg-${res.meta.status}`);
    }

    function updateCheckCard(cardSelector, valSelector, descSelector, valText, descText, status) {
        const $card = $(cardSelector);
        $card.removeClass('seo-check-good seo-check-warning seo-check-danger');
        $card.addClass(`seo-check-${status}`);

        const icon = status === 'good' ? '✅' : (status === 'warning' ? '⚠️' : '❌');
        $card.find('.seo-check-icon').text(icon);
        $(valSelector).text(valText);
        $(descSelector).text(descText);
    }

    // Initialize Companion
    function initSEOCompanion() {
        const ctx = detectContext();
        if (!ctx) return;

        const $field = $(`#${ctx.fieldId}`);
        if (!$field.length) return;

        // Avoid duplicate insertion
        if ($('#seoCompanionWidget').length) return;

        // Locate insertion anchor
        const $ckWrapper = $field.closest('.django-ckeditor-5, .form-row, .form-group');
        const widgetHtml = createWidgetHtml(ctx);

        if ($ckWrapper.length) {
            $ckWrapper.after(widgetHtml);
        } else {
            $field.after(widgetHtml);
        }

        // Toggle collapse handler
        $('#seoCompanionHeader').on('click', function () {
            const $widget = $('#seoCompanionWidget');
            $widget.toggleClass('collapsed');
            localStorage.setItem('sidoos_seo_companion_collapsed', $widget.hasClass('collapsed'));
        });

        // Runner function
        function runCheck() {
            let htmlData = '';
            // Try CKEditor 5 instance from window.editors
            if (window.editors && window.editors[ctx.fieldId]) {
                htmlData = window.editors[ctx.fieldId].getData();
            } else {
                // Fallback to editable div or textarea
                const $editable = $field.siblings('.ck-editor').find('.ck-editor__editable');
                if ($editable.length) {
                    htmlData = $editable.html();
                } else {
                    htmlData = $field.val() || '';
                }
            }
            const results = analyzeContent(htmlData, ctx);
            renderResults(results, ctx);
        }

        const debouncedRun = debounce(runCheck, 180);

        // Register with django-ckeditor-5 callback if available
        if (typeof window.ckeditorRegisterCallback === 'function') {
            window.ckeditorRegisterCallback(ctx.fieldId, function (editor) {
                editor.model.document.on('change:data', debouncedRun);
                setTimeout(runCheck, 100);
            });
        }

        // Listen for direct DOM input/keyup on CKEditor editable area
        $(document).on('input keyup paste change', '.ck-editor__editable', debouncedRun);

        // Also listen to Meta Description / Summary changes
        $(document).on('input keyup change', ctx.metaDescField, debouncedRun);
        $(document).on('input keyup change', '#id_summary, #id_meta_description', debouncedRun);

        // Initial check after short delay to allow CKEditor to mount
        setTimeout(runCheck, 400);
        setTimeout(runCheck, 1200);
    }

    // Run on DOM ready
    $(document).ready(function () {
        initSEOCompanion();
    });

})(window.jQuery || window.django.jQuery);
