from django import forms

from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'parent')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Category name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Category.objects.select_related('parent')
        self.fields['parent'].required = False
