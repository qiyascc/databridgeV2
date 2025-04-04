from django import forms
from .models import CityConfiguration, PriceConfiguration, StockConfiguration

class CityConfigurationForm(forms.ModelForm):
    class Meta:
        model = CityConfiguration
        fields = ['city_id', 'is_active']
        widgets = {
            'city_id': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PriceConfigurationForm(forms.ModelForm):
    class Meta:
        model = PriceConfiguration
        fields = ['PRICE_THRESHOLD', 'BELOW_THRESHOLD_MULTIPLIER', 'ABOVE_THRESHOLD_MULTIPLIER', 'is_active']
        widgets = {
            'PRICE_THRESHOLD': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'BELOW_THRESHOLD_MULTIPLIER': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ABOVE_THRESHOLD_MULTIPLIER': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StockConfigurationForm(forms.ModelForm):
    class Meta:
        model = StockConfiguration
        fields = ['STOCK_MAPPING', 'is_active']
        widgets = {
            'STOCK_MAPPING': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '{"3": 1, "4": 2, "5": 3}'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_STOCK_MAPPING(self):
        data = self.cleaned_data['STOCK_MAPPING']
        try:
            if data:
                # Validate JSON format
                import json
                json.loads(data)
        except ValueError as e:
            raise forms.ValidationError(f"Invalid JSON format: {str(e)}")
        return data