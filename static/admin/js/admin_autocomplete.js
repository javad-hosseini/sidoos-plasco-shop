(function ($) {
    'use strict';

    function initAutocomplete() {
        if (!$) return;
        $('.admin-autocomplete').each(function () {
            const el = this;
            const $el = $(el);

            // Destroy any previous broken/unconfigured select2 instance on this element
            if ($el.hasClass('select2-hidden-accessible')) {
                try {
                    $el.select2('destroy');
                } catch (e) {
                    // Ignore if destroy throws
                }
            }

            const ajaxUrl = el.dataset.ajaxUrl || el.getAttribute('data-ajax--url') || '/sidoos-administration/autocomplete/';
            const appLabel = el.dataset.appLabel || el.getAttribute('data-app-label');
            const modelName = el.dataset.modelName || el.getAttribute('data-model-name');
            const fieldName = el.dataset.fieldName || el.getAttribute('data-field-name');

            $el.select2({
                width: '100%',
                ajax: {
                    url: ajaxUrl,
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        return {
                            term: params.term || '',
                            page: params.page || 1,
                            app_label: appLabel,
                            model_name: modelName,
                            field_name: fieldName
                        };
                    },
                    processResults: function (data, params) {
                        return {
                            results: data.results,
                            pagination: data.pagination
                        };
                    },
                    cache: true
                },
                placeholder: el.getAttribute('data-placeholder') || 'جستجو و انتخاب کنید...',
                allowClear: el.getAttribute('data-allow-clear') === 'true'
            });
        });
    }

    $(document).ready(function () {
        initAutocomplete();
        // Run again with short delays to ensure execution after any theme scripts
        setTimeout(initAutocomplete, 100);
        setTimeout(initAutocomplete, 500);
    });

    if (window.django && window.django.jQuery) {
        window.django.jQuery(document).on('formset:added', function () {
            setTimeout(initAutocomplete, 100);
        });
    }
    $(document).on('formset:added', function () {
        setTimeout(initAutocomplete, 100);
    });

})(window.jQuery || window.$ || (window.django && window.django.jQuery));
