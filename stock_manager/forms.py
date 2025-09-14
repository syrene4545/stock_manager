from django import forms
from .models import StockTransaction, Purchase, Sale, StockCountSession, StockCountEntry
from django.core.exceptions import ValidationError


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['stock_code', 'stock_description', 'uom']

    def clean_stock_code(self):
        stock_code = self.cleaned_data['stock_code']
        if StockTransaction.objects.filter(stock_code__iexact=stock_code).exists():
            raise forms.ValidationError("This stock code already exists.")
        return stock_code


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = [
            'transaction_date',
            'supplier_name',
            'document_number',
            'stock_code',
            'quantity',
            'price_per_unit',
        ]
        widgets = {
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'transaction_date',
            'customer_name',
            'document_number',
            'stock_code',
            'quantity',
            'price_per_unit',
        ]
        widgets = {
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
        }

class StockCountSessionForm(forms.ModelForm):
    class Meta:
        model = StockCountSession
        fields = ['date']  # Add other fields as needed
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class StockCountEntryForm(forms.ModelForm):
    class Meta:
        model = StockCountEntry
        fields = ['stock_code', 'quantity_counted']
        

class PurchaseHeaderForm(forms.Form):
    transaction_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    supplier_name = forms.CharField(max_length=100)
    document_number = forms.CharField(max_length=50)
    def clean_document_number(self):
        doc_num = self.cleaned_data['document_number']
        if Purchase.objects.filter(document_number=doc_num).exists():
            raise ValidationError("This document number already exists.")
        return doc_num


class PurchaseLineForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['stock_code', 'quantity', 'price_per_unit']

class SaleHeaderForm(forms.Form):
    transaction_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    customer_name = forms.CharField(max_length=100)
    # document_number = forms.CharField(max_length=50)
    def clean_document_number(self):
        doc_num = self.cleaned_data['document_number']
        if Sale.objects.filter(document_number=doc_num).exists():
            raise ValidationError("This document number already exists.")
        return doc_num


class SaleLineForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['stock_code', 'quantity', 'price_per_unit']
