import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('home', '0005_pricelist'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='نام و نام خانوادگی')),
                ('phone', models.CharField(max_length=30, verbose_name='شماره تماس')),
                ('subject', models.CharField(choices=[('buy', 'استعلام قیمت و خرید عمده'), ('cooperation', 'همکاری در پخش و نمایندگی'), ('tracking', 'پیگیری و وضعیت مرسوله'), ('other', 'سایر پرسش\u200cها و پیشنهادات')], default='buy', max_length=30, verbose_name='موضوع پیام')),
                ('message', models.TextField(verbose_name='متن پیام یا توضیحات')),
                ('is_read', models.BooleanField(default=False, help_text='تیک بزنید تا وضعیت پیام به عنوان بررسی شده علامت\u200cگذاری شود.', verbose_name='خوانده شده')),
                ('admin_note', models.TextField(blank=True, help_text='یادداشت\u200cهای داخلی تیم فروش و پشتیبانی در مورد این پیام.', verbose_name='یادداشت مدیر')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='آدرس IP')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ارسال')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')),
                ('user', models.ForeignKey(blank=True, help_text='در صورتی که کاربر وارد شده باشد، به حساب کاربری متصل می\u200cشود.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contact_messages', to=settings.AUTH_USER_MODEL, verbose_name='کاربر سایت')),
            ],
            options={
                'verbose_name': 'پیام تماس با ما',
                'verbose_name_plural': 'پیام\u200cهای تماس با ما',
                'ordering': ['-created_at'],
            },
        ),
    ]
