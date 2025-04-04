from django.db import models

class CityConfiguration(models.Model):
    CITY_CHOICES = [
        ("866", "Adana"), ("894", "Adıyaman"), ("882", "Afyon"), ("927", "Ağrı"), ("920", "Aksaray"),
        ("935", "Amasya"), ("873", "Ankara"), ("867", "Antalya"), ("948", "Ardahan"), ("905", "Artvin"),
        ("871", "Aydın"), ("885", "Balıkesir"), ("939", "Bartın"), ("925", "Batman"), ("936", "Bayburt"),
        ("917", "Bilecik"), ("941", "Bingöl"), ("897", "Bitlis"), ("923", "Bolu"), ("919", "Burdur"),
        ("868", "Bursa"), ("910", "Çanakkale"), ("929", "Çankırı"), ("888", "Çorum"), ("874", "Denizli"),
        ("926", "Diyarbakır"), ("947", "Düzce"), ("906", "Edirne"), ("913", "Elazığ"), ("922", "Erzincan"),
        ("900", "Erzurum"), ("887", "Eskişehir"), ("890", "Gaziantep"), ("884", "Giresun"), ("943", "Gümüşhane"),
        ("924", "Hakkari"), ("877", "Hatay"), ("914", "Iğdır"), ("908", "Isparta"), ("865", "İstanbul"),
        ("872", "İzmir"), ("898", "Kahramanmaraş"), ("912", "Karabük"), ("883", "Karaman"), ("915", "Kars"),
        ("895", "Kastamonu"), ("869", "Kayseri"), ("896", "Kırıkkale"), ("902", "Kırklareli"), ("940", "Kırşehir"),
        ("876", "Kocaeli"), ("875", "Konya"), ("901", "Kütahya"), ("893", "Malatya"), ("891", "Manisa"),
        ("930", "Mardin"), ("903", "Mersin"), ("899", "Muğla"), ("932", "Muş"), ("907", "Nevşehir"),
        ("911", "Niğde"), ("904", "Ordu"), ("892", "Osmaniye"), ("928", "Rize"), ("870", "Sakarya"),
        ("916", "Samsun"), ("931", "Siirt"), ("918", "Sinop"), ("879", "Sivas"), ("921", "Şanlıurfa"),
        ("942", "Şırnak"), ("880", "Tekirdağ"), ("909", "Tokat"), ("878", "Trabzon"), ("937", "Tunceli"),
        ("886", "Uşak"), ("933", "Van"), ("889", "Yalova"), ("938", "Yozgat"), ("881", "Zonguldak"),
    ]
    
    city_id = models.CharField(max_length=3, choices=CITY_CHOICES, primary_key=True, verbose_name="City ID")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "City Configuration"
        verbose_name_plural = "City Configurations"

    def __str__(self):
        return self.get_city_id_display()


class PriceConfiguration(models.Model):
    PRICE_THRESHOLD = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=700.00,
        verbose_name="Price Threshold (TRY)"
    )
    BELOW_THRESHOLD_MULTIPLIER = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=2.00,
        verbose_name="Multiplier for Prices Below Threshold"
    )
    ABOVE_THRESHOLD_MULTIPLIER = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.50,
        verbose_name="Multiplier for Prices Above Threshold"
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price Configuration"
        verbose_name_plural = "Price Configurations"

    def __str__(self):
        return f"Price Configuration (Active: {self.is_active})"


class StockConfiguration(models.Model):
    STOCK_MAPPING = models.JSONField(
        default=dict,
        verbose_name="Stock Quantity Mapping",
        help_text="JSON format: {'original_quantity': 'mapped_quantity'}"
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock Configuration"
        verbose_name_plural = "Stock Configurations"

    def __str__(self):
        return f"Stock Configuration (Active: {self.is_active})"

    def get_mapped_quantity(self, original_quantity):
        """Get the mapped quantity based on the configuration"""
        try:
            mapping = self.STOCK_MAPPING or {}
            return mapping.get(str(original_quantity), original_quantity)
        except (ValueError, TypeError):
            return original_quantity