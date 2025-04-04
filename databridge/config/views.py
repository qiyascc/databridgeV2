from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, UpdateView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import CityConfiguration, PriceConfiguration, StockConfiguration
from .forms import CityConfigurationForm, PriceConfigurationForm, StockConfigurationForm

class CityConfigurationListView(ListView):
    model = CityConfiguration
    template_name = 'config/city_list.html'
    context_object_name = 'cities'

class CityConfigurationCreateView(CreateView):
    model = CityConfiguration
    form_class = CityConfigurationForm
    template_name = 'config/city_form.html'
    success_url = reverse_lazy('city_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'City configuration added successfully.')
        return super().form_valid(form)

class CityConfigurationUpdateView(UpdateView):
    model = CityConfiguration
    form_class = CityConfigurationForm
    template_name = 'config/city_form.html'
    success_url = reverse_lazy('city_config_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'City configuration updated successfully.')
        return super().form_valid(form)

class PriceConfigurationUpdateView(UpdateView):
    model = PriceConfiguration
    form_class = PriceConfigurationForm
    template_name = 'config/price_form.html'
    success_url = reverse_lazy('price_config_edit')
    
    def get_object(self):
        return PriceConfiguration.objects.filter(is_active=True).first() or PriceConfiguration.objects.first()
    
    def form_valid(self, form):
        messages.success(self.request, 'Price configuration updated successfully.')
        return super().form_valid(form)

class StockConfigurationUpdateView(UpdateView):
    model = StockConfiguration
    form_class = StockConfigurationForm
    template_name = 'config/stock_form.html'
    success_url = reverse_lazy('stock_config_edit')
    
    def get_object(self):
        return StockConfiguration.objects.filter(is_active=True).first() or StockConfiguration.objects.first()
    
    def form_valid(self, form):
        messages.success(self.request, 'Stock configuration updated successfully.')
        return super().form_valid(form)