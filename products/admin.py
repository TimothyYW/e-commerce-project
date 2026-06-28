# pyrefly: ignore [missing-import]
from django import forms
# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import Category, Product
from core.supabase_client import supabase
import time

# Custom Admin form to support uploading product images to Supabase
class ProductAdminForm(forms.ModelForm):
    image_file = forms.ImageField(required=False, label="Upload Product Image")

    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'stock', 'image_url']

class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'category', 'price', 'stock')
    search_fields = ('name', 'category__name')
    prepopulated_fields = {} # Can be customized later
    
    def save_model(self, request, obj, form, change):
        # Handle file upload directly to the 'product' bucket on Supabase
        if 'image_file' in request.FILES:
            image_file = request.FILES['image_file']
            ext = image_file.name.split('.')[-1]
            file_name = f"product_{int(time.time())}.{ext}"
            
            try:
                from core.supabase_client import upload_file
                # Read file content as bytes
                file_data = image_file.read()
                content_type = image_file.content_type
                
                # Upload and get public URL
                public_url = upload_file(
                    bucket_name="product",
                    file_name=file_name,
                    file_data=file_data,
                    content_type=content_type
                )
                obj.image_url = public_url
            except Exception as e:
                # Fail gracefully in the admin interface
                pass
                
        super().save_model(request, obj, form, change)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

# Register Category and Product in the Django admin dashboard
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
