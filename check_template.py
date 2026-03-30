import os
import django
from django.conf import settings
from django.template import Template, Context, loader

# Mock settings if not already configured
if not settings.configured:
    settings.configure(
        DEBUG=True,
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(os.getcwd(), 'templates')],
            'APP_DIRS': True,
        }],
        INSTALLED_APPS=['store'],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        }
    )
    django.setup()

def check_template():
    try:
        t = loader.get_template('product_detail.html')
        print(f"Template found: {t.origin.name}")
        
        # Mock product object
        class MockProduct:
            id = 1
            title = "Test Product"
            price_per_day = 1000
            security_deposit = 500
            description = "Test description"
            size = "M"
            image = type('MockImage', (), {'url': '/media/test.jpg'})
            category = type('MockCat', (), {'name': 'Test Category'})
            is_currently_booked = False
        
        rendered = t.render({'product': MockProduct()})
        if '₹1000' in rendered:
            print("Successfully rendered price_per_day!")
        else:
            print("Failed to render price_per_day. Output snippet:")
            # Find the price section
            idx = rendered.find('detail-price')
            if idx != -1:
                print(rendered[idx:idx+200])
            else:
                print("Could not find detail-price class in output.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_template()
