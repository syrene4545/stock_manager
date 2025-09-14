from django.db import models
from django.contrib.auth.models import User


class StockTransaction(models.Model):
    stock_code = models.CharField(max_length=20, unique=True)
    stock_description = models.CharField(max_length=100)
    uom = models.CharField(max_length=10)  # Unit of Measure
    
    def __str__(self):
        return f"{self.stock_code} - {self.stock_description}"


class Purchase(models.Model):
    transaction_date = models.DateField()
    supplier_name = models.CharField(max_length=100)
    document_number = models.CharField(max_length=50, unique=True)
    stock_code = models.ForeignKey(StockTransaction, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Purchase - {self.stock_code.stock_code} ({self.document_number})"


class Sale(models.Model):
    transaction_date = models.DateField()
    customer_name = models.CharField(max_length=100)
    document_number = models.CharField(max_length=50, unique=True)
    stock_code = models.ForeignKey(StockTransaction, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Sale - {self.stock_code.stock_code} ({self.document_number})"


class StockCountSession(models.Model):
    date = models.DateField()

    def __str__(self):
        return f"Stock Count Session on {self.date}"


class StockCountEntry(models.Model):
    session = models.ForeignKey(StockCountSession, on_delete=models.CASCADE, related_name='entries')
    stock_code = models.ForeignKey(StockTransaction, on_delete=models.CASCADE)
    quantity_counted = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.stock_code.stock_code} - Counted: {self.quantity_counted}"


class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    description = models.TextField()
    session = models.ForeignKey(StockCountSession, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.timestamp} - {self.action} on {self.model_name} #{self.object_id}"
