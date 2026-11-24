from .models import Asset, UserProfile


def global_finance_context(request):
    """Provides common user financial context to all templates (modal, sidebar, etc.)."""
    if request.user.is_authenticated:
        user_assets = Asset.objects.filter(user=request.user)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        property_asset = user_assets.filter(asset_type='REAL_ESTATE').first()
        return {
            'global_assets': user_assets,
            'assets': user_assets,
            'global_profile': profile,
            'global_property': property_asset,
        }
    return {}
