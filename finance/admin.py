from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Asset, Liability, Transaction, MonthlyFinancialPlan


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_type', 'tag', 'current_valuation', 'purchase_price', 'user', 'is_default')
    list_filter = ('asset_type', 'is_default')
    search_fields = ('name', 'tag', 'specification', 'user__username')
    ordering = ('-current_valuation',)


@admin.register(Liability)
class LiabilityAdmin(admin.ModelAdmin):
    list_display = ('title', 'liability_type', 'monthly_emi', 'total_principal', 'remaining_balance', 'lender', 'user', 'is_active')
    list_filter = ('liability_type', 'is_active', 'is_default')
    search_fields = ('title', 'lender', 'user__username')
    ordering = ('-monthly_emi',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('title', 'transaction_type', 'category', 'amount', 'asset', 'date', 'financial_month', 'user')
    list_filter = ('transaction_type', 'category', 'financial_month', 'date')
    search_fields = ('title', 'notes', 'user__username')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')


@admin.register(MonthlyFinancialPlan)
class MonthlyFinancialPlanAdmin(admin.ModelAdmin):
    list_display = ('month_name', 'financial_year', 'salary_income', 'liabilities_emi', 'vehicle_expenses', 'is_customized', 'user')
    list_filter = ('financial_year', 'is_customized')
    search_fields = ('month_name', 'user__username')
    ordering = ('month_number',)


admin.site.site_header = "MONARCH Private Wealth Administration"
admin.site.site_title = "Monarch Admin Portal"
admin.site.index_title = "Wealth & Expense Analysis Management"
