from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .forms import StockTransactionForm, PurchaseForm, SaleForm
from django.forms import modelformset_factory, formset_factory
from .forms import StockCountSessionForm, StockCountEntryForm, PurchaseHeaderForm, PurchaseLineForm, SaleHeaderForm, SaleLineForm
from .models import StockTransaction, Purchase, Sale, StockCountEntry, AuditLog
from django.core.paginator import Paginator
from django.db.models import Sum, Max, Q, F, ExpressionWrapper, DecimalField, Value, OuterRef, Subquery
from django.db.models.functions import Coalesce
from datetime import date, timedelta, datetime
from django.utils.dateparse import parse_date
from django.utils.timezone import now
import logging
from decimal import Decimal
import calendar
from django.contrib import messages
from django.contrib.auth.decorators import login_required
 

@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']

        user = User.objects.create_user(username=username, password=password, email=email)
        user.is_active = False  # Require admin approval
        user.save()

        messages.success(request, "Registration submitted. Await admin approval.")
        return redirect('registration_pending')
    return render(request, 'register.html')


def registration_pending_view(request):
    return render(request, 'registration_pending.html')



def landing_view(request):
    return render(request, 'landing.html')

def audit_log_view(request):
    logs = AuditLog.objects.order_by('-timestamp')[:100]  # Limit to recent 100
    return render(request, 'audit_log.html', {'logs': logs})


def generate_document_number():
    last_sale = Sale.objects.order_by('-id').first()
    next_id = last_sale.id + 1 if last_sale else 1
    return f"SAL-{next_id:06d}"
    
def get_previous_day(date_input):
    if isinstance(date_input, str):
        date_input = date.fromisoformat(date_input)
    return date_input - timedelta(days=1)

def get_net_quantity(movements, types):
    return movements.filter(transaction_type__in=types).aggregate(Sum('transaction_quantity'))['transaction_quantity__sum'] or 0

def get_latest_purchase_price(stock, up_to_date):
    latest = Purchase.objects.filter(
        stock_code=stock,
        transaction_date__lte=up_to_date
    ).order_by('-transaction_date').first()
    return latest.price_per_unit if latest and latest.price_per_unit else 0


def add_transaction(request):
    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('add_transaction')  # You can define this URL
    else:
        form = StockTransactionForm()
    return render(request, 'add_transaction.html', {'form': form, 'active_tab': 'master'})


def add_purchase(request):
    LineFormSet = formset_factory(PurchaseLineForm, extra=1, can_delete=True)

    if request.method == 'POST':
        header_form = PurchaseHeaderForm(request.POST)
        formset = LineFormSet(request.POST)
        total_value = Decimal('0.00')  # ✅ Initialize here

        if header_form.is_valid() and formset.is_valid():
            header_data = header_form.cleaned_data
            document_number = header_data['document_number']  # ✅ Use user input

            

            for form in formset:
                if form.cleaned_data:
                    quantity = form.cleaned_data['quantity']
                    price = form.cleaned_data['price_per_unit']
                    total_value += quantity * price

                    Purchase.objects.create(
                        transaction_date=header_data['transaction_date'],
                        supplier_name=header_data['supplier_name'],
                        document_number=document_number,
                        stock_code=form.cleaned_data['stock_code'],
                        quantity=quantity,
                        price_per_unit=price
                    )

            messages.success(request, f"Purchases recorded under document number {document_number}. Total value: {total_value:.2f}")

            return redirect('purchase_invoice', document_number=document_number)
    else:
        header_form = PurchaseHeaderForm()
        formset = LineFormSet()
        total_value = Decimal('0.00')

    return render(request, 'add_purchases.html', {
        'header_form': header_form,
        'formset': formset,
        'total_value': total_value,
        'active_tab': 'purchases'
    })


def purchase_invoice(request, document_number):
    purchases = Purchase.objects.filter(document_number=document_number)
    if not purchases.exists():
        return HttpResponseNotFound("Invoice not found.")

    header = purchases.first()
    total_qty = sum(p.quantity for p in purchases)
    total_value = sum(p.quantity * p.price_per_unit for p in purchases)

    return render(request, 'purchase_invoice.html', {
        'purchases': purchases,
        'header': header,
        'total_qty': total_qty,
        'total_value': total_value,
        'active_tab': 'purchases',
    })



def add_sale(request):
    LineFormSet = formset_factory(SaleLineForm, extra=1, can_delete=True)

    

    if request.method == 'POST':
        header_form = SaleHeaderForm(request.POST)
        formset = LineFormSet(request.POST)
        total_value = Decimal('0.00')

        if header_form.is_valid() and formset.is_valid():
            header_data = header_form.cleaned_data
            document_number = generate_document_number()

            total_value = Decimal('0.00')

            for form in formset:
                if form.cleaned_data:
                    quantity = form.cleaned_data['quantity']
                    price = form.cleaned_data['price_per_unit']
                    total_value += quantity * price

                    Sale.objects.create(
                        transaction_date=header_data['transaction_date'],
                        customer_name=header_data['customer_name'],
                        document_number=document_number,
                        stock_code=form.cleaned_data['stock_code'],
                        quantity=quantity,
                        price_per_unit=price
                    )

            messages.success(request, f"Sales recorded under document number {document_number}. Total value: {total_value:.2f}")

            return redirect('sale_receipt', document_number=document_number)

    else:
        header_form = SaleHeaderForm()
        formset = LineFormSet()
        total_value = Decimal('0.00')

    return render(request, 'add_sales.html', {
        'header_form': header_form,
        'formset': formset,
        'total_value': total_value,
        'active_tab': 'sales'
    })


def sale_receipt(request, document_number):
    sales = Sale.objects.filter(document_number=document_number)
    if not sales.exists():
        return HttpResponseNotFound("Receipt not found.")

    header = sales.first()
    total_qty = sum(s.quantity for s in sales)
    total_value = sum(s.quantity * s.price_per_unit for s in sales)

    return render(request, 'sale_receipt.html', {
        'sales': sales,
        'header': header,
        'total_qty': total_qty,
        'total_value': total_value,
        'active_tab': 'sales',
    })



def get_stock_on_hand(stock, count_date):
    previous_day = get_previous_day(count_date)

    purchases = Purchase.objects.filter(
        stock_code=stock,
        transaction_date__lte=previous_day
    ).aggregate(Sum('quantity'))['quantity__sum'] or 0

    sales = Sale.objects.filter(
        stock_code=stock,
        transaction_date__lte=previous_day
    ).aggregate(Sum('quantity'))['quantity__sum'] or 0

    return purchases - sales

def add_stock_count_session(request):
    EntryFormSet = modelformset_factory(StockCountEntry, form=StockCountEntryForm, extra=1, can_delete=True)

    if request.method == 'POST':
        session_form = StockCountSessionForm(request.POST)
        formset = EntryFormSet(request.POST, queryset=StockCountEntry.objects.none())

        if session_form.is_valid() and formset.is_valid():
            session = session_form.save()
            count_date = session.date

            for form in formset:
                if form.cleaned_data:
                    stock = form.cleaned_data.get('stock_code')
                    qty = form.cleaned_data.get('quantity_counted')

                    if stock and qty is not None and str(qty).strip() != '':
                        entry = form.save(commit=False)
                        entry.session = session
                        entry.save()

                        # ✅ Always update stock on hand
                        system_qty = get_stock_on_hand(stock, count_date)
                        variance = qty - system_qty

                        if variance != 0:
                            latest_purchase = Purchase.objects.filter(
                                stock_code=stock,
                                transaction_date__lte=count_date
                            ).order_by('-transaction_date').first()

                            price = get_latest_purchase_price(stock, count_date)


                            # price = latest_purchase.price_per_unit if latest_purchase and latest_purchase.price_per_unit else 0

            return redirect('add_stock_count_session')
    else:
        session_form = StockCountSessionForm()
        formset = EntryFormSet(queryset=StockCountEntry.objects.none())

    return render(request, 'add_stock_count_session.html', {
        'session_form': session_form,
        'formset': formset,
        'active_tab': 'count'
    })



# Create the list view

def transaction_list(request):
    today = date.today()
    current_year = today.year

    default_start = date(current_year, 3, 1)
    default_end = date(current_year + 1, 2, 28)

    # --- DATE HANDLING ---
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    start_date = parse_date(start_date_param) if start_date_param else default_start
    end_date = parse_date(end_date_param) if end_date_param else default_end

    # --- SEARCH HANDLING ---
    search_query = request.GET.get('search')
    if search_query in [None, '', 'None']:
        search_query = None

    transactions = []

    # helper: safely sum qty
    def qty_sum(qs):
        return qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

    stock_items = StockTransaction.objects.all()
    if search_query:
        stock_items = stock_items.filter(
            Q(stock_code__icontains=search_query) |
            Q(stock_description__icontains=search_query)
        )

    previous_day = start_date - timedelta(days=1)

    total_valuation = Decimal('0.00')

    for stock in stock_items:
        # --- Opening Quantity (respect last prior count) ---
        latest_prior_count = StockCountEntry.objects.filter(
            stock_code=stock,
            session__date__lt=start_date
        ).order_by('-session__date').first()

        


        if latest_prior_count:
            count_date = latest_prior_count.session.date
            opening_quantity = latest_prior_count.quantity_counted

            purchases_after_count = qty_sum(
                Purchase.objects.filter(
                    stock_code=stock,
                    transaction_date__gt=count_date,
                    transaction_date__lte=previous_day
                )
            )
            sales_after_count = qty_sum(
                Sale.objects.filter(
                    stock_code=stock,
                    transaction_date__gt=count_date,
                    transaction_date__lte=previous_day
                )
            )
            opening_quantity += purchases_after_count - sales_after_count
        else:
            opening_purchases = qty_sum(
                Purchase.objects.filter(stock_code=stock, transaction_date__lte=previous_day)
            )
            opening_sales = qty_sum(
                Sale.objects.filter(stock_code=stock, transaction_date__lte=previous_day)
            )
            opening_quantity = opening_purchases - opening_sales

        # --- Movements in current period ---
        purchases = qty_sum(
            Purchase.objects.filter(
                stock_code=stock,
                transaction_date__gte=start_date,
                transaction_date__lte=end_date
            )
        )
        sales = qty_sum(
            Sale.objects.filter(
                stock_code=stock,
                transaction_date__gte=start_date,
                transaction_date__lte=end_date
            )
        )

        # --- Latest purchase price ---
        latest_purchase = Purchase.objects.filter(
            stock_code=stock,
            transaction_date__lte=end_date
        ).order_by('-transaction_date').first()
        latest_price = latest_purchase.price_per_unit if latest_purchase else Decimal('0')

        # --- System stock before adjustment ---
        # --- Default system quantity (before any count adjustment) ---
        system_quantity = opening_quantity + purchases - sales
        quantity_on_hand = system_quantity  # will be overwritten if count exists


        # --- Variance (only if count exists in this filter window) ---
        latest_count_entry = StockCountEntry.objects.filter(
            stock_code=stock,
            session__date__gte=start_date,
            session__date__lte=end_date
        ).order_by('-session__date', '-id').first()


        if latest_count_entry:
            count_date = latest_count_entry.session.date
            counted_quantity = latest_count_entry.quantity_counted

            # System quantity at the moment of count
            purchases_to_count = qty_sum(
                Purchase.objects.filter(
                    stock_code=stock,
                    transaction_date__gte=start_date,
                    transaction_date__lte=count_date
                )
            )
            sales_to_count = qty_sum(
                Sale.objects.filter(
                    stock_code=stock,
                    transaction_date__gte=start_date,
                    transaction_date__lte=count_date
                )
            )

            system_qty_at_count = opening_quantity + purchases_to_count - sales_to_count
            variance = counted_quantity - system_qty_at_count

            # ✅ Counted quantity becomes new baseline
            purchases_after_count = qty_sum(
                Purchase.objects.filter(
                    stock_code=stock,
                    transaction_date__gt=count_date,
                    transaction_date__lte=end_date
                )
            )
            sales_after_count = qty_sum(
                Sale.objects.filter(
                    stock_code=stock,
                    transaction_date__gt=count_date,
                    transaction_date__lte=end_date
                )
            )

            quantity_on_hand = counted_quantity + purchases_after_count - sales_after_count
        else:
            counted_quantity = None
            variance = None



        valuation = quantity_on_hand * latest_price
        total_valuation += valuation

        # --- Last movement date ---
        latest_purchase_date = Purchase.objects.filter(stock_code=stock).aggregate(Max('transaction_date'))['transaction_date__max']
        latest_sale_date = Sale.objects.filter(stock_code=stock).aggregate(Max('transaction_date'))['transaction_date__max']
        latest_date = list(filter(None, [latest_purchase_date, latest_sale_date]))

        transactions.append({
            'stock_code': stock.stock_code,
            'description': stock.stock_description,
            'opening_quantity': opening_quantity,
            'purchase_quantity': purchases,
            'sales_quantity': sales,
            'variance': variance,
            'quantity_on_hand': quantity_on_hand,
            'latest_price': latest_price,
            'valuation': valuation,
            'transaction_date': max(latest_date) if latest_date else None,
        })

    return render(request, 'transaction_list.html', {
        'transactions': transactions,
        'search_query': search_query,
        'start_date': start_date,
        'end_date': end_date,
        'active_tab': 'transactions',
        'total_valuation': total_valuation,
    })


def dashboard(request):
    today = date.today()
    current_month = today.month
    current_year = today.year

    first_day_of_month = date(current_year, current_month, 1)
    last_day_prev_month = first_day_of_month - timedelta(days=1)

    # Expression for calculating values
    value_expr = ExpressionWrapper(
        F('quantity') * F('price_per_unit'),
        output_field=DecimalField()
    )

    # --- Opening Stock ---
    opening_stock_qty = Decimal('0')
    opening_value = Decimal('0')
    stock_items = StockTransaction.objects.all()

    for stock in stock_items:
        # Get last count before current month
        last_count = StockCountEntry.objects.filter(
            stock_code=stock,
            session__date__lt=first_day_of_month
        ).order_by('-session__date').first()

        if last_count:
            count_date = last_count.session.date
            counted_qty = last_count.quantity_counted

            # Movements since count up to end of previous month
            purchases_since = Purchase.objects.filter(
                stock_code=stock,
                transaction_date__gt=count_date,
                transaction_date__lte=last_day_prev_month
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            sales_since = Sale.objects.filter(
                stock_code=stock,
                transaction_date__gt=count_date,
                transaction_date__lte=last_day_prev_month
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            adjusted_qty = counted_qty + purchases_since - sales_since
        else:
            # Fallback to net movement
            purchases = Purchase.objects.filter(
                stock_code=stock,
                transaction_date__lte=last_day_prev_month
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            sales = Sale.objects.filter(
                stock_code=stock,
                transaction_date__lte=last_day_prev_month
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            adjusted_qty = purchases - sales

        latest_price = Purchase.objects.filter(
            stock_code=stock,
            transaction_date__lte=last_day_prev_month
        ).order_by('-transaction_date').values_list('price_per_unit', flat=True).first() or 0

        opening_stock_qty += adjusted_qty
        opening_value += adjusted_qty * latest_price

    monthly_counts = StockCountEntry.objects.filter(
    session__date__month=current_month,
    session__date__year=current_year
)

    # Variance for the month
    total_variance_qty = Decimal('0')
    for count in monthly_counts:
        stock = count.stock_code
        count_date = count.session.date
        counted_qty = count.quantity_counted

        purchases_to_date = Purchase.objects.filter(
            stock_code=stock,
            transaction_date__lte=count_date
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0

        sales_to_date = Sale.objects.filter(
            stock_code=stock,
            transaction_date__lte=count_date
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0

        system_qty = purchases_to_date - sales_to_date
        variance = counted_qty - system_qty
        total_variance_qty += variance


    # --- This Month Purchases ---
    purchases_qs = Purchase.objects.filter(transaction_date__month=current_month, transaction_date__year=current_year)
    purchases_qty = purchases_qs.aggregate(Sum('quantity'))['quantity__sum'] or 0
    purchases_value = purchases_qs.annotate(value=value_expr).aggregate(Sum('value'))['value__sum'] or 0

    # --- This Month Sales ---
    sales_qs = Sale.objects.filter(transaction_date__month=current_month, transaction_date__year=current_year)
    sales_qty = sales_qs.aggregate(Sum('quantity'))['quantity__sum'] or 0
    sales_value = sales_qs.annotate(value=value_expr).aggregate(Sum('value'))['value__sum'] or 0

    # --- Closing Balance ---
    closing_balance_qty = opening_stock_qty + purchases_qty - sales_qty
    closing_balance_value = opening_value + purchases_value - sales_value

    # --- Top 5 Sales Items ---
    top_sales_items = (
        sales_qs.values('stock_code__stock_code', 'stock_code__stock_description')
        .annotate(total_qty=Sum('quantity'), total_value=Sum(F('quantity') * F('price_per_unit')))
        .order_by('-total_qty')[:5]
    )

    # --- Top 5 Purchases Items ---
    top_purchases_items = (
        purchases_qs.values('stock_code__stock_code', 'stock_code__stock_description')
        .annotate(total_qty=Sum('quantity'), total_value=Sum(F('quantity') * F('price_per_unit')))
        .order_by('-total_qty')[:5]
    )

    # --- Monthly Trend (last 6 months Purchases vs Sales) ---
    trends = []
    for i in range(5, -1, -1):  # last 6 months
        month = (today.month - i - 1) % 12 + 1
        year = today.year if today.month - i > 0 else today.year - 1
        label = f"{calendar.month_abbr[month]} {year}"

        m_purchases = Purchase.objects.filter(transaction_date__month=month, transaction_date__year=year).aggregate(Sum('quantity'))['quantity__sum'] or 0
        m_sales = Sale.objects.filter(transaction_date__month=month, transaction_date__year=year).aggregate(Sum('quantity'))['quantity__sum'] or 0

        trends.append({"month": label, "purchases": m_purchases, "sales": m_sales})

    context = {
        'opening_stock': opening_stock_qty,
        'opening_value': opening_value,
        'purchases': purchases_qty,
        'purchases_value': purchases_value,
        'sales': sales_qty,
        'sales_value': sales_value,
        'variance_qty': total_variance_qty,
        'closing_balance': closing_balance_qty,
        'closing_value': closing_balance_value,
        'top_sales_items': top_sales_items,
        'top_purchases_items': top_purchases_items,
        'trends': trends,
        'active_tab': 'dashboard',
    }
    return render(request, 'dashboard.html', context)


def inventory_summary(request):
    summary = []

    # --- Filters ---
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    search_query = request.GET.get('search')

    latest_session_date = StockCountEntry.objects.aggregate(
        latest=Max('session__date')
    )['latest']

    start_date = parse_date(start_date_param) if start_date_param else latest_session_date
    end_date = parse_date(end_date_param) if end_date_param else latest_session_date

    counts = StockCountEntry.objects.select_related('stock_code', 'session')

    if start_date:
        counts = counts.filter(session__date__gte=start_date)
    if end_date:
        counts = counts.filter(session__date__lte=end_date)
    if search_query:
        counts = counts.filter(
            Q(stock_code__stock_code__icontains=search_query) |
            Q(stock_code__stock_description__icontains=search_query)
        )

    # --- Helper: sum quantity safely ---
    def qty_sum(qs):
        return qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

    total_system_qty = Decimal('0')
    total_counted_qty = Decimal('0')
    total_variance_qty = Decimal('0')
    total_variance_value = Decimal('0.00')
    total_valuation = Decimal('0.00')

    # Only keep latest count per stock_code
    latest_counts_map = {}
    for count in counts.order_by('-session__date', '-id'):
        stock_id = count.stock_code_id
        if stock_id not in latest_counts_map:
            latest_counts_map[stock_id] = count

    latest_counts = latest_counts_map.values()



    for count in latest_counts:
        stock = count.stock_code
        count_date = count.session.date
        counted_qty = count.quantity_counted

        # --- Find prior count ---
        prior_count = StockCountEntry.objects.filter(
            stock_code=stock,
            session__date__lt=count_date
        ).order_by('-session__date', '-id').first()

        prior_qty = prior_count.quantity_counted if prior_count else Decimal('0')
        prior_date = prior_count.session.date if prior_count else None

        # --- Movements between prior count and current count ---
        purchase_filter = Q(stock_code=stock, transaction_date__lte=count_date)
        sale_filter = Q(stock_code=stock, transaction_date__lte=count_date)

        if prior_date:
            purchase_filter &= Q(transaction_date__gt=prior_date)
            sale_filter &= Q(transaction_date__gt=prior_date)

        purchases_since = qty_sum(Purchase.objects.filter(purchase_filter))
        sales_since = qty_sum(Sale.objects.filter(sale_filter))

        system_qty = prior_qty + purchases_since - sales_since
        variance = counted_qty - system_qty

        # --- Latest price before count ---
        latest_price = Purchase.objects.filter(
            stock_code=stock,
            transaction_date__lte=count_date
        ).order_by('-transaction_date').values_list('price_per_unit', flat=True).first() or Decimal('0')

        valuation = counted_qty * latest_price
        variance_value = variance * latest_price

        # --- Totals ---
        total_system_qty += system_qty
        total_counted_qty += counted_qty
        total_variance_qty += variance
        total_variance_value += variance_value
        total_valuation += valuation

        summary.append({
            'stock_code': stock.stock_code,
            'description': stock.stock_description,
            'count_date': count_date,
            'system_quantity': system_qty,
            'counted_quantity': counted_qty,
            'variance': variance,
            'latest_price': latest_price,
            'valuation': valuation,
            'variance_value': variance_value,
        })


    return render(request, 'inventory_summary.html', {
        'summary': summary,
        'search_query': search_query,
        'start_date': start_date,
        'end_date': end_date,
        'total_system_qty': total_system_qty,
        'total_counted_qty': total_counted_qty,
        'total_variance_qty': total_variance_qty,
        'total_valuation': total_valuation,
        'total_variance_value': total_variance_value,
        'active_tab': 'summary',
    })
