/**
 * CKEditor 5 Live SEO Optimizer & Checklist Engine - Sidoos Admin
 *
 * Real-time SEO analysis engine and live scoring widget for Django Admin
 * (Articles and Products), evaluating RankMath/Yoast style SEO rules:
 * - Basic SEO & Focus Keyword analysis
 * - Additional SEO & Structure (Subheadings, Image Alt, Short URL, Number in Title, TOC)
 * - Readability & Media (Paragraph length, Internal & External links, Media)
 * - Automated System Optimizations (WebP conversion, Canonical URL)
 * - Built-in Table of Contents (TOC) Generator
 * - Built-in Image Alt Text Inspector
 */

(function () {
    'use strict';

    // State
    let activeEditor = null;
    let debounceTimer = null;
    let isArticle = false;
    let isProduct = false;

    // SVG Icons
    const ICONS = {
        PASS: `<svg viewBox="0 0 20 20" width="18" height="18" fill="#15803d"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd"/></svg>`,
        WARN: `<svg viewBox="0 0 20 20" width="18" height="18" fill="#b45309"><path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/></svg>`,
        FAIL: `<svg viewBox="0 0 20 20" width="18" height="18" fill="#b91c1c"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd"/></svg>`,
        INFO: `<svg viewBox="0 0 20 20" width="18" height="18" fill="#0369a1"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd"/></svg>`,
        CHEVRON: `<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/></svg>`,
        TOC: `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 4h18v2H3V4zm0 7h12v2H3v-2zm0 7h18v2H3v-2zm16-6l4 3-4 3v-6z"/></svg>`,
        ALT: `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>`,
    };

    // =========================================================================
    // 1. Text & Unicode Normalization Utilities
    // =========================================================================
    function normalizePersianText(str) {
        if (!str) return '';
        return str
            .toString()
            .toLowerCase()
            .replace(/[\u200B-\u200D\uFEFF]/g, ' ') // Zero-width spaces to normal space
            .replace(/ي/g, 'ی')
            .replace(/ك/g, 'ک')
            .replace(/[\u064B-\u065F]/g, '')        // Persian diacritics
            .replace(/\s+/g, ' ')
            .trim();
    }

    function countWords(str) {
        if (!str) return 0;
        const matches = str.match(/[\w\u0600-\u06FF]+/g);
        return matches ? matches.length : 0;
    }

    function countOccurrences(text, searchTerm) {
        if (!text || !searchTerm) return 0;
        const normText = normalizePersianText(text);
        const normTerm = normalizePersianText(searchTerm);
        if (!normTerm) return 0;

        // Escape regex special chars
        const escaped = normTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escaped, 'gi');
        const matches = normText.match(regex);
        return matches ? matches.length : 0;
    }

    function extractPlainText(html) {
        if (!html) return '';
        const temp = document.createElement('div');
        temp.innerHTML = html;
        return (temp.textContent || temp.innerText || '').replace(/\s+/g, ' ').trim();
    }

    // =========================================================================
    // 2. SEO Rule Evaluation Engine
    // =========================================================================
    function evaluateSEO() {
        const $focusKeyInput = document.getElementById('id_focus_keyword');
        const focusKeyword = ($focusKeyInput ? $focusKeyInput.value : '').trim();

        // Title: Article title or Product name
        const $titleInput = document.getElementById('id_title') || document.getElementById('id_name');
        const titleText = ($titleInput ? $titleInput.value : '').trim();

        const $metaTitleInput = document.getElementById('id_meta_title');
        const metaTitleText = ($metaTitleInput ? $metaTitleInput.value : '').trim() || titleText;

        const $metaDescInput = document.getElementById('id_meta_description');
        const metaDescText = ($metaDescInput ? $metaDescInput.value : '').trim();

        const $slugInput = document.getElementById('id_slug');
        const slugText = ($slugInput ? $slugInput.value : '').trim();

        // CKEditor Content HTML
        let contentHtml = '';
        if (activeEditor && typeof activeEditor.getData === 'function') {
            contentHtml = activeEditor.getData();
        } else {
            const $contentInput = document.getElementById('id_content') || document.getElementById('id_description');
            contentHtml = ($contentInput ? $contentInput.value : '');
        }

        const plainText = extractPlainText(contentHtml);
        const totalWords = countWords(plainText);

        // Parse HTML DOM for tag-specific audits
        const parser = new DOMParser();
        const doc = parser.parseFromString(contentHtml || '<div></div>', 'text/html');

        // Headings (H2, H3, H4)
        const headings = Array.from(doc.querySelectorAll('h2, h3, h4'));
        const headingTexts = headings.map(h => extractPlainText(h.innerHTML));

        // Images
        const images = Array.from(doc.querySelectorAll('img'));
        const imageAlts = images.map(img => (img.getAttribute('alt') || '').trim());

        // Links
        const links = Array.from(doc.querySelectorAll('a'));

        // Paragraphs
        const paragraphs = Array.from(doc.querySelectorAll('p'));

        // Rule results container
        const results = {
            basic: [],
            additional: [],
            readability: [],
            automated: [],
        };

        let passedPoints = 0;
        let totalPossiblePoints = 0;

        function addRule(category, name, status, desc, tip, weight = 10) {
            results[category].push({ name, status, desc, tip });
            totalPossiblePoints += weight;
            if (status === 'pass') {
                passedPoints += weight;
            } else if (status === 'warning') {
                passedPoints += Math.round(weight * 0.5);
            }
        }

        // ---------------------------------------------------------------------
        // Category 1: Basic SEO
        // ---------------------------------------------------------------------
        const hasKeyword = Boolean(focusKeyword);

        // 1.1 Focus Keyword Defined
        if (hasKeyword) {
            addRule('basic', 'تعیین کلمه کلیدی کانونی', 'pass',
                `کلمه کلیدی کانونی «${focusKeyword}» برای این صفحه تعیین شده است.`,
                'عالی است.', 10);
        } else {
            addRule('basic', 'تعیین کلمه کلیدی کانونی', 'fail',
                'کلمه کلیدی کانونی هنوز تعیین نشده است.',
                'لطفاً در فیلد «کلمه کلیدی کانونی» عبارت مورد نظرتان را وارد کنید.', 10);
        }

        // 1.2 Focus Keyword in SEO Title
        if (!hasKeyword) {
            addRule('basic', 'کلمه کلیدی در عنوان سئو', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی کانونی را وارد کنید.', 10);
        } else {
            const inTitle = countOccurrences(metaTitleText, focusKeyword) > 0;
            if (inTitle) {
                addRule('basic', 'کلمه کلیدی در عنوان سئو', 'pass',
                    'کلمه کلیدی در عنوان سئو (یا عنوان اصلی) به کار رفته است.',
                    'عالی است.', 10);
            } else {
                addRule('basic', 'کلمه کلیدی در عنوان سئو', 'fail',
                    'کلمه کلیدی کانونی در عنوان سئو یافت نشد.',
                    'پیشنهاد می‌شود کلمه کلیدی را در ابتدای عنوان سئو قرار دهید.', 10);
            }
        }

        // 1.3 Focus Keyword in Meta Description
        if (!hasKeyword) {
            addRule('basic', 'کلمه کلیدی در توضیحات متای سئو', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی کانونی را وارد کنید.', 10);
        } else {
            const inMetaDesc = countOccurrences(metaDescText, focusKeyword) > 0;
            if (inMetaDesc) {
                addRule('basic', 'کلمه کلیدی در توضیحات متای سئو', 'pass',
                    'کلمه کلیدی در توضیحات متای سئو موجود است.',
                    'عالی است.', 10);
            } else {
                addRule('basic', 'کلمه کلیدی در توضیحات متای سئو', 'fail',
                    'کلمه کلیدی در توضیحات متای سئو یافت نشد.',
                    'کلمه کلیدی را به متن توضیحات متا اضافه کنید تا در نتایج گوگل پررنگ شود.', 10);
            }
        }

        // 1.4 Focus Keyword in URL / Slug
        if (!hasKeyword) {
            addRule('basic', 'کلمه کلیدی در آدرس (اسلاگ)', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی کانونی را وارد کنید.', 10);
        } else {
            const normSlug = normalizePersianText(slugText).replace(/[-_]/g, ' ');
            const inSlug = countOccurrences(normSlug, focusKeyword) > 0;
            if (inSlug) {
                addRule('basic', 'کلمه کلیدی در آدرس (اسلاگ)', 'pass',
                    'کلمه کلیدی در نامک (اسلاگ) URL موجود است.',
                    'عالی است.', 10);
            } else {
                addRule('basic', 'کلمه کلیدی در آدرس (اسلاگ)', 'fail',
                    'کلمه کلیدی در اسلاگ این صفحه یافت نشد.',
                    'پیشنهاد می‌شود کلمه کلیدی را در اسلاگ قرار دهید (مثلاً با خط تیره).', 10);
            }
        }

        // 1.5 Focus Keyword at Beginning of Content
        if (!hasKeyword) {
            addRule('basic', 'کلمه کلیدی در ۱۰٪ ابتدای محتوا', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی کانونی را وارد کنید.', 10);
        } else {
            // First 100 words or first paragraph
            const firstParaText = paragraphs.length ? extractPlainText(paragraphs[0].innerHTML) : '';
            const first100Words = plainText.split(/\s+/).slice(0, 100).join(' ');
            const inIntro = countOccurrences(firstParaText, focusKeyword) > 0 || countOccurrences(first100Words, focusKeyword) > 0;
            if (inIntro) {
                addRule('basic', 'کلمه کلیدی در ۱۰٪ ابتدای محتوا', 'pass',
                    'کلمه کلیدی در پاراگراف یا ۱۰۰ کلمه ابتدایی محتوا به کار رفته است.',
                    'عالی است.', 10);
            } else {
                addRule('basic', 'کلمه کلیدی در ۱۰٪ ابتدای محتوا', 'fail',
                    'کلمه کلیدی در ابتدای متن مشاهده نشد.',
                    'کلمه کلیدی را در پاراگراف اول بیاورید تا ربات‌های جستجو سریع‌تر موضوع را تشخیص دهند.', 10);
            }
        }

        // 1.6 Focus Keyword in Content
        if (!hasKeyword) {
            addRule('basic', 'کلمه کلیدی در متن محتوا', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی کانونی را وارد کنید.', 10);
        } else {
            const keywordOccurrences = countOccurrences(plainText, focusKeyword);
            if (keywordOccurrences >= 1) {
                addRule('basic', 'کلمه کلیدی در متن محتوا', 'pass',
                    `کلمه کلیدی ${keywordOccurrences} بار در محتوا به کار رفته است.`,
                    'عالی است.', 10);
            } else {
                addRule('basic', 'کلمه کلیدی در متن محتوا', 'fail',
                    'کلمه کلیدی اصلاً در متن محتوا وجود ندارد.',
                    'کلمه کلیدی کانونی را به طور طبیعی در متن مقاله/محصول به کار ببرید.', 10);
            }
        }

        // 1.7 Content Word Count (600–2500 for articles; 150–1200 for products)
        const minWords = isProduct ? 150 : 600;
        const maxWords = isProduct ? 1200 : 2500;
        if (totalWords >= minWords && totalWords <= maxWords) {
            addRule('basic', 'طول محتوا', 'pass',
                `طول محتوا ${totalWords} کلمه است (محدوده استاندارد: ${minWords} تا ${maxWords} کلمه).`,
                'عالی است.', 10);
        } else if (totalWords > maxWords) {
            addRule('basic', 'طول محتوا', 'pass',
                `محتوای شما بسیار جامع است (${totalWords} کلمه).`,
                'خوب است؛ اطمینان حاصل کنید ساختار متن با زیرعنوان‌ها به خوبی حفظ شده است.', 10);
        } else {
            addRule('basic', 'طول محتوا', 'fail',
                `طول محتوا تنها ${totalWords} کلمه است. حداقل مقدار پیشنهادی ${minWords} کلمه است.`,
                `محتوا را گسترش دهید تا حداقل به ${minWords} کلمه برسد.`, 10);
        }

        // 1.8 Keyword Density (Target ~ 1%)
        if (!hasKeyword || totalWords === 0) {
            addRule('basic', 'تراکم کلمه کلیدی', 'fail',
                'تراکم کلمه کلیدی ۰٪ است.',
                'هدف حدود ۱٪ تراکم کلمه کلیدی در کل متن است.', 10);
        } else {
            const keywordWordCount = countWords(focusKeyword) || 1;
            const keywordCount = countOccurrences(plainText, focusKeyword);
            const density = (keywordCount * keywordWordCount / totalWords) * 100;
            const densityFormatted = density.toFixed(2);

            if (keywordCount === 0) {
                addRule('basic', 'تراکم کلمه کلیدی', 'fail',
                    `تراکم کلمه کلیدی ۰٪ است (۰ بار تکرار).`,
                    'هدف حدود ۱٪ است. کلمه کلیدی را در متن تکرار کنید.', 10);
            } else if (density >= 0.7 && density <= 2.2) {
                addRule('basic', 'تراکم کلمه کلیدی', 'pass',
                    `تراکم کلمه کلیدی ${densityFormatted}٪ است (${keywordCount} بار تکرار).`,
                    'عالی است؛ در محدوده طلایی ۱٪ قرار دارد.', 10);
            } else if (density > 2.2 && density <= 3.5) {
                addRule('basic', 'تراکم کلمه کلیدی', 'warning',
                    `تراکم کلمه کلیدی ${densityFormatted}٪ کمی بالاست (${keywordCount} بار تکرار).`,
                    'مراقب باشید زیاده‌روی در تکرار کلمه کلیدی (Keyword Stuffing) نشود.', 10);
            } else if (density > 3.5) {
                addRule('basic', 'تراکم کلمه کلیدی', 'fail',
                    `تراکم کلمه کلیدی بیش از حد بالاست (${densityFormatted}٪ - ${keywordCount} بار تکرار).`,
                    'کلمه کلیدی را بیش از حد تکرار کرده‌اید؛ ممکن است توسط موتورهای جستجو جریمه شوید.', 10);
            } else {
                addRule('basic', 'تراکم کلمه کلیدی', 'warning',
                    `تراکم کلمه کلیدی ${densityFormatted}٪ است (${keywordCount} بار تکرار).`,
                    'کمی کلمه کلیدی را بیشتر به کار ببرید تا به حدود ۱٪ برسد.', 10);
            }
        }

        // ---------------------------------------------------------------------
        // Category 2: Additional SEO & Structure
        // ---------------------------------------------------------------------

        // 2.1 Focus Keyword in Subheadings (H2, H3, H4)
        if (!hasKeyword) {
            addRule('additional', 'کلمه کلیدی در زیرعنوان‌ها (H2, H3)', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی را مشخص کنید.', 8);
        } else {
            const headingWithKeyword = headingTexts.some(h => countOccurrences(h, focusKeyword) > 0);
            if (headingWithKeyword) {
                addRule('additional', 'کلمه کلیدی در زیرعنوان‌ها (H2, H3)', 'pass',
                    'کلمه کلیدی کانونی در زیرعنوان‌های متن به کار رفته است.',
                    'عالی است.', 8);
            } else if (headings.length > 0) {
                addRule('additional', 'کلمه کلیدی در زیرعنوان‌ها (H2, H3)', 'fail',
                    'کلمه کلیدی در هیچ‌کدام از زیرعنوان‌های H2 یا H3 یافت نشد.',
                    'کلمه کلیدی را در حداقل یکی از تیترهای فرعی متن قرار دهید.', 8);
            } else {
                addRule('additional', 'کلمه کلیدی در زیرعنوان‌ها (H2, H3)', 'fail',
                    'هیچ تیتر و زیرعنوانی (H2, H3) در متن استفاده نشده است.',
                    'متن را با تیترهای H2 و H3 بخش‌بندی کنید و کلمه کلیدی را در آن‌ها بیاورید.', 8);
            }
        }

        // 2.2 Image Alt Text with Focus Keyword
        if (!hasKeyword) {
            addRule('additional', 'متن جایگزین (Alt) تصویر با کلمه کلیدی', 'fail',
                'کلمه کلیدی مشخص نشده است.',
                'ابتدا کلمه کلیدی را مشخص کنید.', 8);
        } else if (images.length === 0) {
            addRule('additional', 'متن جایگزین (Alt) تصویر با کلمه کلیدی', 'fail',
                'هیچ تصویری در متن وجود ندارد.',
                'حداقل یک تصویر اضافه کرده و متن جایگزین (Alt) آن را برابر کلمه کلیدی قرار دهید.', 8);
        } else {
            const imgWithKeyAlt = imageAlts.some(alt => countOccurrences(alt, focusKeyword) > 0);
            if (imgWithKeyAlt) {
                addRule('additional', 'متن جایگزین (Alt) تصویر با کلمه کلیدی', 'pass',
                    'حداقل یک تصویر دارای متن جایگزین حاوی کلمه کلیدی است.',
                    'عالی است.', 8);
            } else {
                addRule('additional', 'متن جایگزین (Alt) تصویر با کلمه کلیدی', 'fail',
                    'تصویر با متن جایگزین (Alt) حاوی کلمه کلیدی یافت نشد.',
                    'روی تصویر کلیک کرده و با دکمه «تغییر متن جایگزین»، کلمه کلیدی را در Alt وارد کنید.', 8);
            }
        }

        // 2.3 Short & Optimized URL
        if (!slugText) {
            addRule('additional', 'آدرس صفحه (URL)', 'fail',
                'نامک (اسلاگ) خالی است.',
                'اسلاگ به صورت خودکار یا دستی تکمیل خواهد شد.', 6);
        } else if (slugText.length <= 75) {
            addRule('additional', 'آدرس صفحه (URL)', 'pass',
                `طول اسلاگ بهینه و کوتاه است (${slugText.length} کاراکتر).`,
                'عالی است.', 6);
        } else {
            addRule('additional', 'آدرس صفحه (URL)', 'warning',
                `طول اسلاگ بیش از حد طولانی است (${slugText.length} کاراکتر).`,
                'پیشنهاد می‌شود اسلاگ کمتر از ۷۵ کاراکتر باشد.', 6);
        }

        // 2.4 Number in SEO Title
        const hasNumberInTitle = /[0-9۰-۹]/.test(metaTitleText);
        if (hasNumberInTitle) {
            addRule('additional', 'وجود عدد در عنوان سئو', 'pass',
                'عنوان سئو حاوی عدد است.',
                'عنوان‌های دارای عدد نرخ کلیک (CTR) بالاتری دارند.', 6);
        } else {
            addRule('additional', 'وجود عدد در عنوان سئو', 'warning',
                'عنوان سئو حاوی عدد نیست.',
                'افزودن عدد (مثلاً «۱۰ نکته...»، «سال ۱۴۰۳»، یا کد مدل) نرخ کلیک را تا ۳۶٪ افزایش می‌دهد.', 6);
        }

        // 2.5 Table of Contents (TOC)
        const hasTocClass = doc.querySelector('.table-of-contents, .sidoos-toc-box, [data-toc="true"]') !== null;
        if (hasTocClass) {
            addRule('additional', 'فهرست مطالب (Table of Contents)', 'pass',
                'فهرست مطالب در متن درج شده است.',
                'عالی است؛ تجربه کاربری و پرش سریع به بخش‌ها فراهم است.', 8);
        } else if (headings.length >= 3) {
            addRule('additional', 'فهرست مطالب (Table of Contents)', 'warning',
                `متن دارای ${headings.length} زیرعنوان است اما فهرست مطالب ندارد.`,
                'می‌توانید با دکمه «درج فهرست مطالب» در بالای این پنل به صورت خودکار فهرست بسازید.', 8);
        } else {
            addRule('additional', 'فهرست مطالب (Table of Contents)', 'info',
                'برای متون طولانی استفاده از فهرست مطالب توصیه می‌شود.',
                'با ایجاد زیرعنوان‌های متعدد، می‌توانید فهرست مطالب خودکار درج کنید.', 8);
        }

        // ---------------------------------------------------------------------
        // Category 3: Readability & Media
        // ---------------------------------------------------------------------

        // 3.1 Dofollow External Links
        const externalLinks = links.filter(a => {
            const href = (a.getAttribute('href') || '').trim();
            if (!href.startsWith('http://') && !href.startsWith('https://')) return false;
            if (href.includes('sidoos.ir') || href.includes(window.location.hostname)) return false;
            return true;
        });
        const dofollowExternal = externalLinks.filter(a => {
            const rel = (a.getAttribute('rel') || '').toLowerCase();
            return !rel.includes('nofollow');
        });

        if (dofollowExternal.length >= 1) {
            addRule('readability', 'لینک‌های خروجی معتبر (Dofollow)', 'pass',
                `${dofollowExternal.length} لینک خروجی Dofollow به منابع خارجی یافت شد.`,
                'عالی است؛ ارجاع به منابع معتبر به سئو کمک می‌کند.', 8);
        } else if (externalLinks.length >= 1) {
            addRule('readability', 'لینک‌های خروجی معتبر (Dofollow)', 'warning',
                'لینک خروجی وجود دارد اما به صورت nofollow علامت‌گذاری شده است.',
                'در صورت امکان، حداقل یک لینک dofollow به منبع مرجع معتبر اختصاص دهید.', 8);
        } else {
            addRule('readability', 'لینک‌های خروجی معتبر (Dofollow)', 'warning',
                'هیچ لینکی به منابع معتبر خارجی یافت نشد.',
                'افزودن لینک به یک منبع معتبر و مرتبط به گوگل نشان می‌دهد محتوای شما مستند است.', 8);
        }

        // 3.2 Internal Links
        const internalLinks = links.filter(a => {
            const href = (a.getAttribute('href') || '').trim();
            if (!href || href.startsWith('#')) return false;
            if (href.startsWith('/') || href.includes('sidoos.ir') || href.includes(window.location.hostname)) {
                return true;
            }
            return false;
        });

        if (internalLinks.length >= 1) {
            addRule('readability', 'لینک‌های داخلی به سایت', 'pass',
                `${internalLinks.length} پیوند داخلی به بخش‌های سایت پیدا شد.`,
                'عالی است؛ لینک‌سازی داخلی معماری سایت را تقویت می‌کند.', 8);
        } else {
            addRule('readability', 'لینک‌های داخلی به سایت', 'fail',
                'هیچ لینک داخلی در متن وجود ندارد.',
                'از دکمه «لینک داخلی (Ctrl+Shift+K)» برای پیوند به محصولات و مقالات دیگر استفاده کنید.', 8);
        }

        // 3.3 Short and Concise Paragraphs
        const longParagraphs = paragraphs.filter(p => countWords(extractPlainText(p.innerHTML)) > 120);
        if (paragraphs.length === 0) {
            addRule('readability', 'پاراگراف‌های کوتاه و خوانا (UX)', 'fail',
                'متن هنوز پاراگراف‌بندی نشده است.',
                'متن را به پاراگراف‌های کوچک تقسیم کنید.', 6);
        } else if (longParagraphs.length === 0) {
            addRule('readability', 'پاراگراف‌های کوتاه و خوانا (UX)', 'pass',
                'تمامی پاراگراف‌ها کوتاه و کمتر از ۱۲۰ کلمه هستند.',
                'عالی است؛ خوانایی در موبایل و دسکتاپ بسیار بالاست.', 6);
        } else {
            addRule('readability', 'پاراگراف‌های کوتاه و خوانا (UX)', 'warning',
                `${longParagraphs.length} پاراگراف بیش از حد طولانی (بیش از ۱۲۰ کلمه) هستند.`,
                'پاراگراف‌های طولانی را به بخش‌های کوچک‌تر ۲ الی ۳ خطی بشکنید.', 6);
        }

        // 3.4 Media (Images/Video)
        const hasMedia = images.length > 0 || doc.querySelector('video, iframe, oembed') !== null;
        if (hasMedia) {
            addRule('readability', 'محتوای بصری و چندرسانه‌ای', 'pass',
                `محتوا دارای ${images.length} تصویر یا مدیا است.`,
                'عالی است.', 8);
        } else {
            addRule('readability', 'محتوای بصری و چندرسانه‌ای', 'fail',
                'هیچ تصویر یا ویدیویی در متن وجود ندارد.',
                'برای جلب توجه کاربر و سئو، حداقل یک تصویر مرتبط اضافه کنید.', 8);
        }

        // ---------------------------------------------------------------------
        // Category 4: Automated System Enforcements
        // ---------------------------------------------------------------------
        results.automated.push({
            name: 'تبدیل خودکار به WebP (فعال در سرور)',
            status: 'auto',
            desc: 'تمامی تصاویری که در این ادیتور یا در بخش کاور بارگذاری شوند، به صورت خودکار در پس‌زمینه به فرمت سبک و مدرن WebP تبدیل می‌گردند.',
            tip: 'نیازی به بهینه‌سازی دستی سایز یا فرمت تصاویر ندارید؛ سامانه به طور خودکار کیفیت و سرعت را تضمین می‌کند.'
        });

        results.automated.push({
            name: 'آدرس کانونیکال خودکار (Canonical URL)',
            status: 'auto',
            desc: 'سیستم به صورت خودکار آدرس رسمی و کانونیکال صفحه را بر اساس نامک تولید کرده و از ایجاد محتوای تکراری در گوگل جلوگیری می‌نماید.',
            tip: 'پیش‌نمایش آدرس در کادر مربوطه در دسترس است.'
        });

        // ---------------------------------------------------------------------
        // Score Calculation
        // ---------------------------------------------------------------------
        const score = totalPossiblePoints > 0 ? Math.round((passedPoints / totalPossiblePoints) * 100) : 0;

        return {
            score,
            results,
            stats: {
                totalWords,
                keywordCount: countOccurrences(plainText, focusKeyword),
                headingsCount: headings.length,
                imagesCount: images.length,
                imagesMissingAlt: images.filter(img => !(img.getAttribute('alt') || '').trim()).length,
                linksCount: links.length,
            },
            imagesInfo: images.map(img => ({
                src: img.getAttribute('src') || '',
                alt: (img.getAttribute('alt') || '').trim()
            })),
            headingsList: headings.map(h => ({
                tag: h.tagName.toLowerCase(),
                text: extractPlainText(h.innerHTML)
            }))
        };
    }

    // =========================================================================
    // 3. UI Component Renderer
    // =========================================================================
    function getOrCreateSEOPanel(targetContainer) {
        let panel = document.getElementById('sidoos-seo-optimizer-panel');
        if (panel) return panel;

        panel = document.createElement('div');
        panel.id = 'sidoos-seo-optimizer-panel';
        panel.className = 'sidoos-seo-panel';
        panel.innerHTML = `
            <!-- Header -->
            <div class="sidoos-seo-header">
                <div class="sidoos-seo-header-title">
                    <span class="sidoos-seo-icon">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                        </svg>
                    </span>
                    <div>
                        <h4>بهینه‌ساز سئو زنده (SEO Optimizer)</h4>
                        <span style="font-size: 11px; color: #64748b;">چک‌لیست هوشمند و امتیاز زنده بر اساس استانداردهای RankMath & Yoast</span>
                    </div>
                </div>

                <div class="sidoos-seo-score-widget">
                    <span class="sidoos-seo-score-text">امتیاز سئو:</span>
                    <div id="sidoos-seo-score-badge" class="sidoos-seo-score-badge score-bad">
                        <span id="sidoos-seo-score-num">0</span> / 100
                    </div>
                </div>

                <div class="sidoos-seo-actions">
                    <button type="button" class="sidoos-seo-action-btn" id="sidoos-seo-gen-toc-btn" title="ساخت و درج فهرست مطالب خودکار بر اساس زیرعنوان‌ها">
                        ${ICONS.TOC}
                        <span>درج فهرست مطالب</span>
                    </button>
                    <button type="button" class="sidoos-seo-action-btn" id="sidoos-seo-inspect-alt-btn" title="مشاهده وضعیت متن جایگزین تصاویر">
                        ${ICONS.ALT}
                        <span>بررسی Alt تصاویر</span>
                    </button>
                </div>
            </div>

            <!-- Stats Bar -->
            <div class="sidoos-seo-stats-bar">
                <div class="sidoos-seo-stat-item">
                    <span class="sidoos-seo-stat-label">تعداد کلمات</span>
                    <span class="sidoos-seo-stat-val" id="seo-stat-words">0</span>
                </div>
                <div class="sidoos-seo-stat-item">
                    <span class="sidoos-seo-stat-label">تکرار کلمه کلیدی</span>
                    <span class="sidoos-seo-stat-val" id="seo-stat-keyword-count">0</span>
                </div>
                <div class="sidoos-seo-stat-item">
                    <span class="sidoos-seo-stat-label">زیرعنوان‌ها (تیترها)</span>
                    <span class="sidoos-seo-stat-val" id="seo-stat-headings">0</span>
                </div>
                <div class="sidoos-seo-stat-item">
                    <span class="sidoos-seo-stat-label">تعداد تصاویر</span>
                    <span class="sidoos-seo-stat-val" id="seo-stat-images">0</span>
                </div>
                <div class="sidoos-seo-stat-item">
                    <span class="sidoos-seo-stat-label">لینک‌ها</span>
                    <span class="sidoos-seo-stat-val" id="seo-stat-links">0</span>
                </div>
            </div>

            <!-- Accordion Sections -->
            <div class="sidoos-seo-body">
                <!-- Section 1: Basic SEO -->
                <div class="sidoos-seo-section is-open" id="seo-sec-basic">
                    <div class="sidoos-seo-section-header">
                        <span class="sidoos-seo-section-title">
                            📌 کلمه کلیدی کانونی و اصول پایه (Basic SEO)
                            <span class="sidoos-seo-section-badge" id="seo-badge-basic">0/8</span>
                        </span>
                        <span class="sidoos-seo-section-chevron">${ICONS.CHEVRON}</span>
                    </div>
                    <div class="sidoos-seo-section-content">
                        <ul class="sidoos-seo-rule-list" id="seo-list-basic"></ul>
                    </div>
                </div>

                <!-- Section 2: Additional SEO -->
                <div class="sidoos-seo-section is-open" id="seo-sec-additional">
                    <div class="sidoos-seo-section-header">
                        <span class="sidoos-seo-section-title">
                            🏗️ ساختار و بهینه‌سازی پیشرفته (Additional SEO)
                            <span class="sidoos-seo-section-badge" id="seo-badge-additional">0/5</span>
                        </span>
                        <span class="sidoos-seo-section-chevron">${ICONS.CHEVRON}</span>
                    </div>
                    <div class="sidoos-seo-section-content">
                        <ul class="sidoos-seo-rule-list" id="seo-list-additional"></ul>
                    </div>
                </div>

                <!-- Section 3: Readability & Media -->
                <div class="sidoos-seo-section is-open" id="seo-sec-readability">
                    <div class="sidoos-seo-section-header">
                        <span class="sidoos-seo-section-title">
                            📖 خوانایی، لینک‌سازی و رسانه (Readability & Media)
                            <span class="sidoos-seo-section-badge" id="seo-badge-readability">0/4</span>
                        </span>
                        <span class="sidoos-seo-section-chevron">${ICONS.CHEVRON}</span>
                    </div>
                    <div class="sidoos-seo-section-content">
                        <ul class="sidoos-seo-rule-list" id="seo-list-readability"></ul>
                    </div>
                </div>

                <!-- Section 4: Automated System Enforcements -->
                <div class="sidoos-seo-section" id="seo-sec-automated">
                    <div class="sidoos-seo-section-header">
                        <span class="sidoos-seo-section-title">
                            ⚡ بهینه‌سازی‌های خودکار سامانه (Automated Optimizations)
                            <span class="sidoos-seo-section-badge badge-complete">فعال</span>
                        </span>
                        <span class="sidoos-seo-section-chevron">${ICONS.CHEVRON}</span>
                    </div>
                    <div class="sidoos-seo-section-content">
                        <ul class="sidoos-seo-rule-list" id="seo-list-automated"></ul>
                    </div>
                </div>
            </div>

            <!-- Alt Text Inspector Drawer (Initially Hidden) -->
            <div id="sidoos-seo-alt-drawer" style="display:none; padding:16px 24px; background:#f8fafc; border-top:1px solid #e2e8f0;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h5 style="margin:0; font-size:14px; font-weight:700;">بررسی متن جایگزین (Alt) تصاویر موجود در متن</h5>
                    <button type="button" class="sidoos-seo-action-btn" id="sidoos-seo-close-alt-drawer">بستن</button>
                </div>
                <div id="sidoos-seo-alt-drawer-content"></div>
            </div>
        `;

        // Insert into DOM right below CKEditor container or adjacent to it
        if (targetContainer && targetContainer.parentNode) {
            targetContainer.parentNode.insertBefore(panel, targetContainer.nextSibling);
        } else {
            const form = document.querySelector('form#article_form') || document.querySelector('form#product_form') || document.querySelector('form');
            if (form) form.appendChild(panel);
        }

        // Setup accordion click handlers
        panel.querySelectorAll('.sidoos-seo-section-header').forEach(header => {
            header.addEventListener('click', function () {
                const section = this.closest('.sidoos-seo-section');
                section.classList.toggle('is-open');
            });
        });

        // Setup TOC Button
        const tocBtn = panel.querySelector('#sidoos-seo-gen-toc-btn');
        if (tocBtn) {
            tocBtn.addEventListener('click', function (e) {
                e.preventDefault();
                generateTableOfContents();
            });
        }

        // Setup Alt Inspector Button
        const altBtn = panel.querySelector('#sidoos-seo-inspect-alt-btn');
        const altDrawer = panel.querySelector('#sidoos-seo-alt-drawer');
        const closeAltDrawer = panel.querySelector('#sidoos-seo-close-alt-drawer');
        if (altBtn && altDrawer) {
            altBtn.addEventListener('click', function (e) {
                e.preventDefault();
                altDrawer.style.display = altDrawer.style.display === 'none' ? 'block' : 'none';
            });
            if (closeAltDrawer) {
                closeAltDrawer.addEventListener('click', function () {
                    altDrawer.style.display = 'none';
                });
            }
        }

        return panel;
    }

    // =========================================================================
    // 4. Update UI with Evaluation Results
    // =========================================================================
    function updateUI(evaluation) {
        const { score, results, stats, imagesInfo } = evaluation;

        // 1. Score Badge & Color
        const scoreBadge = document.getElementById('sidoos-seo-score-badge');
        const scoreNum = document.getElementById('sidoos-seo-score-num');
        if (scoreNum && scoreBadge) {
            scoreNum.textContent = score;
            scoreBadge.className = 'sidoos-seo-score-badge';
            if (score >= 80) {
                scoreBadge.classList.add('score-good');
            } else if (score >= 50) {
                scoreBadge.classList.add('score-ok');
            } else {
                scoreBadge.classList.add('score-bad');
            }
        }

        // 2. Stats Bar
        const elWords = document.getElementById('seo-stat-words');
        const elKeyCount = document.getElementById('seo-stat-keyword-count');
        const elHeadings = document.getElementById('seo-stat-headings');
        const elImages = document.getElementById('seo-stat-images');
        const elLinks = document.getElementById('seo-stat-links');

        if (elWords) elWords.textContent = stats.totalWords;
        if (elKeyCount) elKeyCount.textContent = stats.keywordCount;
        if (elHeadings) elHeadings.textContent = stats.headingsCount;
        if (elImages) {
            elImages.textContent = `${stats.imagesCount}${stats.imagesMissingAlt ? ` (${stats.imagesMissingAlt} بدون Alt)` : ''}`;
            elImages.style.color = stats.imagesMissingAlt ? '#b91c1c' : '#0f172a';
        }
        if (elLinks) elLinks.textContent = stats.linksCount;

        // 3. Render Checklist Items
        function renderCategory(catKey, listId, badgeId) {
            const listEl = document.getElementById(listId);
            const badgeEl = document.getElementById(badgeId);
            const items = results[catKey] || [];
            if (!listEl) return;

            let passCount = 0;
            listEl.innerHTML = '';

            items.forEach(item => {
                if (item.status === 'pass' || item.status === 'auto') passCount++;

                const li = document.createElement('li');
                li.className = `sidoos-seo-rule-item status-${item.status}`;

                let iconSvg = ICONS.PASS;
                let badgeText = 'پاس شده';
                if (item.status === 'warning') {
                    iconSvg = ICONS.WARN;
                    badgeText = 'نیاز به بهبود';
                } else if (item.status === 'fail') {
                    iconSvg = ICONS.FAIL;
                    badgeText = 'رد شده';
                } else if (item.status === 'auto') {
                    iconSvg = ICONS.INFO;
                    badgeText = 'سیستمی خودکار';
                } else if (item.status === 'info') {
                    iconSvg = ICONS.INFO;
                    badgeText = 'راهنما';
                }

                li.innerHTML = `
                    <span class="sidoos-seo-rule-icon">${iconSvg}</span>
                    <div class="sidoos-seo-rule-details">
                        <div class="sidoos-seo-rule-name">
                            <span>${item.name}</span>
                            <span class="sidoos-seo-rule-status-badge">${badgeText}</span>
                        </div>
                        <p class="sidoos-seo-rule-desc">${item.desc}</p>
                        ${item.tip ? `<p class="sidoos-seo-rule-tip">💡 ${item.tip}</p>` : ''}
                    </div>
                `;
                listEl.appendChild(li);
            });

            if (badgeEl && catKey !== 'automated') {
                badgeEl.textContent = `${passCount}/${items.length}`;
                if (passCount === items.length) {
                    badgeEl.classList.add('badge-complete');
                } else {
                    badgeEl.classList.remove('badge-complete');
                }
            }
        }

        renderCategory('basic', 'seo-list-basic', 'seo-badge-basic');
        renderCategory('additional', 'seo-list-additional', 'seo-badge-additional');
        renderCategory('readability', 'seo-list-readability', 'seo-badge-readability');
        renderCategory('automated', 'seo-list-automated', 'seo-badge-automated');

        // 4. Update Alt Inspector Drawer Content
        const altDrawerContent = document.getElementById('sidoos-seo-alt-drawer-content');
        if (altDrawerContent) {
            if (imagesInfo.length === 0) {
                altDrawerContent.innerHTML = '<p style="color:#64748b; font-size:13px; margin:0;">هیچ تصویری در متن یافت نشد.</p>';
            } else {
                let html = '<ul class="sidoos-seo-alt-list">';
                imagesInfo.forEach((img, idx) => {
                    const hasAlt = Boolean(img.alt);
                    html += `
                        <li class="sidoos-seo-alt-item ${hasAlt ? '' : 'missing-alt'}">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <img src="${img.src}" class="alt-preview-thumb" alt="" onerror="this.style.display='none'">
                                <div>
                                    <span style="font-weight:600;">تصویر #${idx + 1}:</span>
                                    <span style="color:${hasAlt ? '#15803d' : '#b91c1c'}; margin-right:6px;">
                                        ${hasAlt ? `متن جایگزین: «${img.alt}»` : '⚠️ متن جایگزین (Alt) خالی است!'}
                                    </span>
                                </div>
                            </div>
                            <span style="font-size:11px; color:#64748b;">(برای تغییر، در ادیتور روی تصویر کلیک کنید)</span>
                        </li>
                    `;
                });
                html += '</ul>';
                altDrawerContent.innerHTML = html;
            }
        }
    }

    // =========================================================================
    // 5. Table of Contents (TOC) Generator Action
    // =========================================================================
    function generateTableOfContents() {
        if (!activeEditor) {
            alert('ادیتور متن در دسترس نیست.');
            return;
        }

        const contentHtml = activeEditor.getData();
        const parser = new DOMParser();
        const doc = parser.parseFromString(contentHtml || '<div></div>', 'text/html');

        const headings = Array.from(doc.querySelectorAll('h2, h3'));
        if (headings.length === 0) {
            alert('برای ساخت فهرست مطالب، ابتدا حداقل یک یا دو تیتر با فرمت H2 یا H3 در متن بنویسید.');
            return;
        }

        // Build Table of Contents HTML
        let tocHtml = `
            <div class="sidoos-toc-box" data-toc="true">
                <p class="sidoos-toc-title">📋 فهرست مطالب این مقاله</p>
                <ul>
        `;

        headings.forEach((h, index) => {
            let id = h.getAttribute('id');
            if (!id) {
                // Generate clean slug ID from heading text
                const cleanSlug = extractPlainText(h.innerHTML)
                    .replace(/[^\w\u0600-\u06FF]+/g, '-')
                    .replace(/^-+|-+$/g, '') || `section-${index + 1}`;
                id = `toc-${cleanSlug}-${index + 1}`;
                h.setAttribute('id', id);
            }

            const isH3 = h.tagName.toLowerCase() === 'h3';
            const text = extractPlainText(h.innerHTML);
            tocHtml += `<li style="${isH3 ? 'margin-right: 20px;' : ''}"><a href="#${id}">${text}</a></li>`;
        });

        tocHtml += `
                </ul>
            </div>
        `;

        // Check if TOC already exists in document
        const existingToc = doc.querySelector('.sidoos-toc-box, [data-toc="true"]');
        if (existingToc) {
            existingToc.outerHTML = tocHtml;
            activeEditor.setData(doc.body.innerHTML);
        } else {
            // Prepend TOC right before the first heading or at the start
            const firstHeading = doc.querySelector('h2, h3');
            if (firstHeading) {
                firstHeading.insertAdjacentHTML('beforebegin', tocHtml);
                activeEditor.setData(doc.body.innerHTML);
            } else {
                activeEditor.setData(tocHtml + doc.body.innerHTML);
            }
        }

        runAnalysis();
    }

    // =========================================================================
    // 6. Debounced Controller
    // =========================================================================
    function runAnalysis() {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const evalResult = evaluateSEO();
            updateUI(evalResult);
        }, 150);
    }

    // =========================================================================
    // 7. Initialization & Event Binding
    // =========================================================================
    function init() {
        // Detect current form type
        isArticle = Boolean(document.getElementById('article_form') || document.querySelector('.model-article'));
        isProduct = Boolean(document.getElementById('product_form') || document.querySelector('.model-product'));

        if (!isArticle && !isProduct) {
            // Also check URL
            if (window.location.pathname.includes('/blogs/article/')) isArticle = true;
            if (window.location.pathname.includes('/products/product/')) isProduct = true;
        }

        if (!isArticle && !isProduct) {
            return; // Not an article or product change form
        }

        // Locate CKEditor container
        const findAndAttach = () => {
            const editorEl = document.querySelector('.django-ckeditor-5') || document.querySelector('.ck-editor');
            if (!editorEl) return false;

            getOrCreateSEOPanel(editorEl);

            // Find CKEditor 5 instance
            if (window.editors && typeof window.editors === 'object') {
                for (const ed of Object.values(window.editors)) {
                    if (ed && typeof ed.getData === 'function') {
                        activeEditor = ed;
                        break;
                    }
                }
            }

            if (activeEditor && activeEditor.model && activeEditor.model.document) {
                activeEditor.model.document.on('change:data', runAnalysis);
            }

            return true;
        };

        // Attempt immediate attachment
        if (!findAndAttach()) {
            const intervals = [300, 700, 1500, 3000];
            intervals.forEach(d => setTimeout(findAndAttach, d));
        }

        // Hook CKEditor register callback
        if (typeof window.ckeditorRegisterCallback === 'function') {
            const originalReg = window.ckeditorRegisterCallback;
            window.ckeditorRegisterCallback = function (id, cb) {
                originalReg(id, function (editor) {
                    if (typeof cb === 'function') cb(editor);
                    activeEditor = editor;
                    if (editor.model && editor.model.document) {
                        editor.model.document.on('change:data', runAnalysis);
                    }
                    setTimeout(findAndAttach, 50);
                    runAnalysis();
                });
            };
        }

        // Listen to all relevant form input fields
        const inputSelectors = [
            '#id_focus_keyword',
            '#id_title',
            '#id_name',
            '#id_slug',
            '#id_meta_title',
            '#id_meta_description',
            '#id_summary',
        ];

        inputSelectors.forEach(sel => {
            const el = document.querySelector(sel);
            if (el) {
                el.addEventListener('input', runAnalysis);
                el.addEventListener('change', runAnalysis);
                el.addEventListener('keyup', runAnalysis);
            }
        });

        // Delegate for editable area
        document.addEventListener('input', function (e) {
            if (e.target && e.target.classList && e.target.classList.contains('ck-editor__editable')) {
                runAnalysis();
            }
        });

        // Initial run
        setTimeout(runAnalysis, 500);
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
