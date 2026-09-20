/**
 * Sidoos Admin - Real-Time Auto-Prepopulate for SEO and Metadata Fields
 *
 * Provides live, real-time synchronization as the user types, matching
 * Django's prepopulated_fields slug behavior:
 * - Title / Name -> meta_title
 * - Summary / Description -> meta_description
 * - Summary + Content -> reading_time (articles)
 * - Slug -> Canonical URL preview badge
 *
 * Tracks manual user edits so user customizations are never overwritten.
 */

(function ($) {
    'use strict';

    function stripHtml(html) {
        if (!html) return '';
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim();
    }

    function initAutoPrepopulate() {
        // =========================================================================
        // 1. Article Admin (Blogs)
        // =========================================================================
        const $artTitle = $('#id_title');
        const $artSummary = $('#id_summary');
        const $artMetaTitle = $('#id_meta_title');
        const $artMetaDesc = $('#id_meta_description');
        const $artReadingTime = $('#id_reading_time');
        const $artSlug = $('#id_slug');

        if ($artTitle.length && $artMetaTitle.length) {
            let metaTitleManual = Boolean($artMetaTitle.val() && $artMetaTitle.val() !== $artTitle.val());
            let metaDescManual = Boolean($artMetaDesc.val());
            let readingTimeManual = Boolean($artReadingTime.val() && $artReadingTime.val() !== '1' && $artReadingTime.val() !== '');

            function addResetBtn($input, labelText, onReset) {
                const $container = $input.closest('.form-row, .mb-3, .form-group');
                if (!$container.find('.seo-auto-reset-btn').length) {
                    const $btn = $('<button type="button" class="btn btn-sm btn-link seo-auto-reset-btn" style="padding:0; font-size:12px; color:#0d6efd; text-decoration:none; margin-inline-start:8px; display:inline-block;">🔄 همگام‌سازی خودکار با ' + labelText + '</button>');
                    $btn.on('click', function (e) {
                        e.preventDefault();
                        onReset();
                    });
                    $input.after($btn);
                }
            }

            addResetBtn($artMetaTitle, 'عنوان مقاله', function () {
                metaTitleManual = false;
                $artMetaTitle.val($artTitle.val()).trigger('input');
            });

            addResetBtn($artMetaDesc, 'خلاصه مقاله', function () {
                metaDescManual = false;
                const text = stripHtml($artSummary.val());
                $artMetaDesc.val(text.slice(0, 160)).trigger('input');
            });

            $artMetaTitle.on('input', function () {
                metaTitleManual = Boolean($(this).val().trim());
            });

            $artMetaDesc.on('input', function () {
                metaDescManual = Boolean($(this).val().trim());
            });

            $artReadingTime.on('input', function () {
                readingTimeManual = Boolean($(this).val().trim());
            });

            // Live sync Title -> Meta Title & Canonical Preview
            $artTitle.on('input keyup change', function () {
                const val = $(this).val();
                if (!metaTitleManual) {
                    $artMetaTitle.val(val);
                }
                setTimeout(function () {
                    updateCanonicalPreview('blogs', $artSlug.val() || val);
                }, 50);
            });

            // Live sync Summary -> Meta Description & Reading Time
            $artSummary.on('input keyup change', function () {
                const summaryText = stripHtml($(this).val());
                if (!metaDescManual) {
                    $artMetaDesc.val(summaryText.slice(0, 160));
                }
                if (!readingTimeManual) {
                    calculateArticleReadingTime();
                }
            });

            // Live sync Slug -> Canonical Preview
            $artSlug.on('input keyup change', function () {
                updateCanonicalPreview('blogs', $(this).val());
            });

            // Calculate reading time from summary and content
            function calculateArticleReadingTime() {
                const summaryText = stripHtml($artSummary.val() || '');
                let contentText = '';
                const $contentEl = $('#id_content');
                if ($contentEl.length) {
                    contentText = stripHtml($contentEl.val() || '');
                }
                const $editorEl = $('.ck-editor__editable');
                if ($editorEl.length) {
                    contentText += ' ' + stripHtml($editorEl.text() || '');
                }
                const fullText = (summaryText + ' ' + contentText).trim();
                const wordMatches = fullText.match(/[\w\u0600-\u06FF]+/g);
                const words = wordMatches ? wordMatches.length : 0;
                const minutes = Math.max(1, Math.min(60, Math.ceil(words / 180)));
                if (!readingTimeManual && $artReadingTime.length) {
                    $artReadingTime.val(minutes);
                }
            }

            // Hook editor changes
            $(document).on('input keyup', '.ck-editor__editable', function () {
                if (!readingTimeManual) {
                    calculateArticleReadingTime();
                }
            });
        }

        // =========================================================================
        // 2. Product Admin (Products)
        // =========================================================================
        const $prodName = $('#id_name');
        const $prodDesc = $('#id_description');
        const $prodMetaTitle = $('#id_meta_title');
        const $prodMetaDesc = $('#id_meta_description');
        const $prodSlug = $('#id_slug');

        if ($prodName.length && $prodMetaTitle.length) {
            let metaTitleManual = Boolean($prodMetaTitle.val() && $prodMetaTitle.val() !== ($prodName.val() + ' | سیدوس'));
            let metaDescManual = Boolean($prodMetaDesc.val());

            function addProductResetBtn($input, labelText, onReset) {
                const $container = $input.closest('.form-row, .mb-3, .form-group');
                if (!$container.find('.seo-auto-reset-btn').length) {
                    const $btn = $('<button type="button" class="btn btn-sm btn-link seo-auto-reset-btn" style="padding:0; font-size:12px; color:#0d6efd; text-decoration:none; margin-inline-start:8px; display:inline-block;">🔄 همگام‌سازی خودکار با ' + labelText + '</button>');
                    $btn.on('click', function (e) {
                        e.preventDefault();
                        onReset();
                    });
                    $input.after($btn);
                }
            }

            addProductResetBtn($prodMetaTitle, 'نام محصول', function () {
                metaTitleManual = false;
                const val = $prodName.val();
                $prodMetaTitle.val(val ? val + ' | سیدوس' : '').trigger('input');
            });

            addProductResetBtn($prodMetaDesc, 'توضیحات محصول', function () {
                metaDescManual = false;
                const text = stripHtml($prodDesc.val());
                $prodMetaDesc.val(text.slice(0, 160)).trigger('input');
            });

            $prodMetaTitle.on('input', function () {
                metaTitleManual = Boolean($(this).val().trim());
            });

            $prodMetaDesc.on('input', function () {
                metaDescManual = Boolean($(this).val().trim());
            });

            // Live sync Name -> Meta Title & Canonical Preview
            $prodName.on('input keyup change', function () {
                const val = $(this).val().trim();
                if (!metaTitleManual) {
                    $prodMetaTitle.val(val ? val + ' | سیدوس' : '');
                }
                setTimeout(function () {
                    updateCanonicalPreview('products', $prodSlug.val() || val);
                }, 50);
            });

            // Live sync Description -> Meta Description
            $prodDesc.on('input keyup change', function () {
                const text = stripHtml($(this).val());
                if (!metaDescManual) {
                    $prodMetaDesc.val(text.slice(0, 160));
                }
            });

            // Hook CKEditor for description if present
            $(document).on('input keyup', '.field-description .ck-editor__editable', function () {
                if (!metaDescManual) {
                    const text = stripHtml($(this).text());
                    $prodMetaDesc.val(text.slice(0, 160));
                }
            });

            // Live sync Slug -> Canonical Preview
            $prodSlug.on('input keyup change', function () {
                updateCanonicalPreview('products', $(this).val());
            });
        }

        // =========================================================================
        // Helper: Live Update Canonical URL Preview Badge
        // =========================================================================
        function updateCanonicalPreview(prefix, rawSlug) {
            if (!rawSlug) return;
            const cleanSlug = rawSlug.trim().replace(/\s+/g, '-');
            const canonicalUrl = 'https://sidoos.ir/' + prefix + '/' + cleanSlug + '/';
            const $previewA = $('.field-canonical_preview a, #canonical_preview a');
            if ($previewA.length) {
                $previewA.attr('href', canonicalUrl).text(canonicalUrl);
            }
            const $codeSpan = $('.field-canonical_preview code, #canonical_preview code');
            if ($codeSpan.length) {
                $codeSpan.text(canonicalUrl);
            }
        }
    }

    $(document).ready(initAutoPrepopulate);

})(django.jQuery || window.jQuery || window.$);
