"""Shared CKEditor 5 configuration for admin rich-text fields."""

CKEDITOR_COLOR_PALETTE = [
    {'color': '#800000', 'label': 'Maroon'},
    {'color': '#0b3d91', 'label': 'Blue'},
    {'color': '#B8860B', 'label': 'Gold'},
    {'color': '#166534', 'label': 'Green'},
    {'color': '#111827', 'label': 'Black'},
    {'color': '#ffffff', 'label': 'White', 'hasBorder': True},
]

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': [
                'heading', '|', 'bold', 'italic', 'link',
                'bulletedList', 'numberedList', 'blockQuote', 'insertImage',
            ],
        },
    },
    'full': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': {
            'items': [
                'heading', '|',
                'bold', 'italic', 'underline', 'strikethrough',
                'subscript', 'superscript', 'code', 'removeFormat', '|',
                'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', '|',
                'alignment', '|',
                'bulletedList', 'numberedList', 'todoList', '|',
                'outdent', 'indent', '|',
                'link', 'insertImage', 'mediaEmbed', 'insertTable',
                'blockQuote', 'codeBlock', 'horizontalLine',
                'specialCharacters', 'pageBreak', 'htmlEmbed', '|',
                'findAndReplace', 'selectAll', 'sourceEditing', '|',
                'undo', 'redo',
            ],
            'shouldNotGroupWhenFull': True,
        },
        'image': {
            'toolbar': [
                'imageTextAlternative', '|',
                'imageStyle:alignLeft', 'imageStyle:alignCenter',
                'imageStyle:alignRight', 'imageStyle:side', '|',
                'toggleImageCaption', 'imageResize',
            ],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ],
        },
        'table': {
            'contentToolbar': [
                'tableColumn', 'tableRow', 'mergeTableCells',
                'tableProperties', 'tableCellProperties',
            ],
            'tableProperties': {
                'borderColors': CKEDITOR_COLOR_PALETTE,
                'backgroundColors': CKEDITOR_COLOR_PALETTE,
            },
            'tableCellProperties': {
                'borderColors': CKEDITOR_COLOR_PALETTE,
                'backgroundColors': CKEDITOR_COLOR_PALETTE,
            },
        },
        'heading': {
            'options': [
                {'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph'},
                {'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1'},
                {'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2'},
                {'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3'},
            ],
        },
        'list': {
            'properties': {
                'styles': True,
                'startIndex': True,
                'reversed': True,
            },
        },
        'htmlSupport': {
            'allow': [
                {
                    'name': '/^.*$/',
                    'attributes': True,
                    'classes': True,
                    'styles': True,
                },
            ],
        },
    },
}