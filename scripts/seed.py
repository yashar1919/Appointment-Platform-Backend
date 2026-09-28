import asyncio
from datetime import time
from decimal import Decimal
from sqlalchemy import delete, select
from app.domain.models import Location, Service, ServiceCategory, Staff, StaffService, Tenant, WorkingHours
from app.infrastructure.database import AsyncSessionLocal


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        tenant = await db.scalar(select(Tenant).where(Tenant.slug == "yasaman-raesi"))
        tenant_data = {
            "name": "آکادمی تخصصی یاسمن رئیسی",
            "slug": "yasaman-raesi",
            "timezone": "Asia/Tehran",
            "headline": "زیبایی ماندگار، با ظرافتی طبیعی",
            "description": "ما با به‌روزترین متدهای جهانی، چهره‌ای طبیعی و ماندگار برای شما خلق می‌کنیم.",
            "phone": "09128777749",
            "address": "شیراز، معالی آباد، بعد از خیابان پزشکان، ساختمان اوتانا 1، طبقه 2، واحد 201",
            "city": "شیراز",
            "currency": "IRR",
            "currency_symbol": "تومان",
            "image": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=1200",
            "logo": "/assets/logo.png",
            "cover_image": "https://images.unsplash.com/photo-1616683693504-3ea7e9ad6fec?w=1600",
            "rating": 4.95,
            "reviews_count": 384,
            "min_notice_hours": 0,
        }
        if tenant is None:
            tenant = Tenant(**tenant_data)
            db.add(tenant)
        else:
            for field, value in tenant_data.items():
                setattr(tenant, field, value)
        await db.flush()

        category_data = [
            {"external_id": "brows", "name": "ابرو", "description": "میکروبلیدینگ، نانوبروز و فیبروز تار به تار"},
            {"external_id": "lips", "name": "لب", "description": "شیدینگ لب روسی و لیپ بلش مخملی"},
            {"external_id": "eyes", "name": "چشم", "description": "بن مژه نامرئی و خط چشم مینیاتوری"},
            {"external_id": "care", "name": "ترمیم و ریموو", "description": "اصلاح بد رنگی و خنثی‌سازی تخصصی"},
            {"external_id": "consultation", "name": "مشاوره", "description": "طراحی آناتومیک و آنالیز هارمونی چهره"},
        ]
        categories: dict[str, ServiceCategory] = {}
        for data in category_data:
            category = await db.scalar(select(ServiceCategory).where(ServiceCategory.tenant_id == tenant.id, ServiceCategory.external_id == data["external_id"]))
            if category is None:
                category = await db.scalar(select(ServiceCategory).where(ServiceCategory.tenant_id == tenant.id, ServiceCategory.name == data["name"]))
            if category is None:
                category = ServiceCategory(tenant_id=tenant.id, **data)
                db.add(category)
            else:
                for field, value in data.items():
                    setattr(category, field, value)
            categories[data["external_id"]] = category
        await db.flush()

        service_data = [
            {"name": "میکروبلیدینگ فیبروز اختصاصی", "category_id": "brows", "description": "طراحی مویی و قرینه‌سازی متقارن ابرو با خطوط فوق‌العاده ظریف، متناسب با فرم استخوان‌بندی و چرخش طبیعی تارهای ابرو.", "duration_minutes": 120, "price": Decimal("4500000"), "is_featured": True, "is_popular": True, "image": "https://images.unsplash.com/photo-1616683693504-3ea7e9ad6fec?w=500", "included_items": ["طراحی و متقارن‌سازی هندسی با کولیس دیجیتال", "استفاده از کیت یک‌بار مصرف استریل و اختصاصی", "پیگمنت فیبروز اصل بدون قرمزی و دگرگونی رنگ", "بی‌حسی موضعی بدون تغییر بافت پوست"], "care_instructions": "تا ۳ روز از شستشوی مستقیم با آب خودداری فرمایید و از بالم ترمیم‌کننده مخصوص آکادمی استفاده شود."},
            {"name": "لیپ بلش و شیدینگ مخملی لب", "category_id": "lips", "description": "ایجاد رنگ طبیعی و شاداب، اصلاح تیرگی و فرم لب‌ها با تکنیک آبرنگی و گرادیانت ملایم بدون ایجاد خط دور غیرطبیعی.", "duration_minutes": 100, "price": Decimal("3800000"), "is_featured": False, "is_popular": True, "image": "https://images.unsplash.com/photo-1588510883734-31e19e9a8e51?w=500", "included_items": ["خنثی‌سازی اولیه پیگمنت تیرگی لب در صورت نیاز", "ترکیب رنگ سفارشی هماهنگ با ته‌رنگ پوست شما", "ماندگاری ۱۸ الی ۲۴ ماه با محوشدگی یکنواخت"], "care_instructions": "استفاده از ویتامین A چشمی روزی ۳ بار و پرهیز از نوشیدنی‌های خیلی داغ تا ۴۸ ساعت."},
            {"name": "بن مژه نامرئی و خط چشم مینیاتوری", "category_id": "eyes", "description": "کاشت رنگ در بن مژه‌ها جهت ایجاد عمق، گیرایی و پرپشت نشان دادن مژه‌ها با مشکی‌ترین پیگمنت‌های آلمانی.", "duration_minutes": 90, "price": Decimal("3200000"), "is_featured": False, "is_popular": False, "image": "https://images.unsplash.com/photo-1583001968930-13f3c6461baa?w=500", "included_items": ["قرینه‌سازی مینیاتوری و قرینه‌سازی زاویه چشم", "بدون پخش‌شدگی رنگ در بافت حساس پلک", "بی‌حسی پیشرفته بدون سوزش چشم"], "care_instructions": None},
            {"name": "نانوبروز تلفیقی با دستگاه", "category_id": "brows", "description": "تکنیک پیشرفته و غیرتهاجمی با دستگاه نانو برای پوست‌های چرب با تارهای نانو بسیار سبک و دوام فوق‌العاده بالا.", "duration_minutes": 130, "price": Decimal("4800000"), "is_featured": True, "is_popular": False, "image": "https://images.unsplash.com/photo-1629425733761-caae3b5f2e50?w=500", "included_items": ["مناسب انواع پوست مخصوصاً پوست‌های چرب و منافذدار", "بدون ایجاد اسکار و آسیب به ریشه تارهای موی طبیعی"], "care_instructions": None},
            {"name": "خنثی‌سازی و اصلاح بدرنگی تاتو قدیمی", "category_id": "care", "description": "تبدیل پیگمنت‌های دودی، بنفش، خاکستری و قرمز تاتوهای قدیمی به تناژ نچرال و گرم پیش از طراحی مجدد.", "duration_minutes": 75, "price": Decimal("2600000"), "is_featured": False, "is_popular": False, "image": "https://images.unsplash.com/photo-1596704017254-9b121068fb31?w=500", "included_items": None, "care_instructions": None},
            {"name": "مشاوره اختصاصی و طراحی آزمایشی چهره", "category_id": "consultation", "description": "۳۰ دقیقه جلسه حضوری جهت تست فرم‌های مناسب صورت، انتخاب پالت رنگ متناسب با پیگمنت طبیعی پوست و رفع سوالات.", "duration_minutes": 30, "price": Decimal("500000"), "is_featured": False, "is_popular": False, "image": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=500", "included_items": ["طراحی غیرماندگار موقت برای مشاهده نتیجه احتمالی", "هزینه در صورت انجام خدمت در فاکتور کسر می‌گردد"], "care_instructions": None},
        ]
        services: list[Service] = []
        for data in service_data:
            service = await db.scalar(select(Service).where(Service.tenant_id == tenant.id, Service.name == data["name"]))
            if service is None:
                service = Service(tenant_id=tenant.id, category_id=categories[data["category_id"]].id, **{key: value for key, value in data.items() if key != "category_id"})
                db.add(service)
            else:
                for key, value in data.items():
                    if key != "category_id":
                        setattr(service, key, value)
                service.category_id = categories[data["category_id"]].id
                service.is_active = True
            services.append(service)
        await db.flush()
        desired_service_names = {data["name"] for data in service_data}
        existing_services = list((await db.scalars(select(Service).where(Service.tenant_id == tenant.id))).all())
        for service in existing_services:
            service.is_active = service.name in desired_service_names

        staff_data = [
            {"name": "یاسمن رئیسی", "role": "مستر رسمی آکادمی فی اروپا و بنیان‌گذار آکادمی", "avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200", "bio": "بیش از ۹ سال سابقه تخصصی در زمینه میکروبلیدینگ و میکروپیگمنتیشن با بیش از ۶,۰۰۰ پیگمنت‌گذاری موفق در ایران و دبی.", "experience_years": 9, "rating": 4.98, "specialties": ["میکروبلیدینگ فیبروز", "نانوبروز تخصصی", "لیپ بلش مخملی"]},
            {"name": "نسترن کمالی", "role": "آرتیست ارشد آرایش دائم و میکروپیگمنتیشن", "avatar": "https://images.unsplash.com/photo-1594744803329-e58b31de8bf5?w=200", "bio": "فارغ‌التحصیل آکادمی S-Brows، متخصص در پیاده‌سازی خطوط تار به تار فوق‌العاده ظریف و شیدینگ سایه‌ای.", "experience_years": 6, "rating": 4.92, "specialties": ["نانوبروز", "بن مژه مینیاتوری", "طراحی قرینه"]},
            {"name": "مونا شایسته", "role": "متخصص شیدینگ و ترکیب رنگ ارگانیک لب", "avatar": "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=200", "bio": "استاد ترکیب رنگ و خنثی‌سازی پیگمنت‌های دودی، طراح لب‌های آمبره طبیعی بدون کادربندی تیز.", "experience_years": 5, "rating": 4.9, "specialties": ["لیپ بلش روسی", "خنثی‌سازی تیره", "ترمیم فرم لب"]},
        ]
        staff_members: list[Staff] = []
        for data in staff_data:
            member = await db.scalar(select(Staff).where(Staff.tenant_id == tenant.id, Staff.name == data["name"]))
            if member is None:
                member = Staff(tenant_id=tenant.id, **data)
                db.add(member)
            else:
                for field, value in data.items():
                    setattr(member, field, value)
                member.is_active = True
            staff_members.append(member)
        await db.flush()
        desired_staff_names = {data["name"] for data in staff_data}
        existing_staff = list((await db.scalars(select(Staff).where(Staff.tenant_id == tenant.id))).all())
        for member in existing_staff:
            member.is_active = member.name in desired_staff_names
        await db.execute(delete(StaffService).where(StaffService.staff_id.in_([member.id for member in staff_members])))
        db.add_all([StaffService(staff_id=member.id, service_id=service.id) for member in staff_members for service in services])

        location = await db.scalar(select(Location).where(Location.tenant_id == tenant.id, Location.name == "شعبه مرکزی معالی آباد"))
        location_data = {"name": "شعبه مرکزی معالی آباد", "address": "شیراز، معالی آباد، بعد از خیابان پزشکان، ساختمان اوتانا 1، طبقه 2، واحد 201", "city": "شیراز", "postal_code": "1988614321", "directions": "دارای پارکینگ اختصاصی مشتریان و دسترسی آسان از طریق خیابان ولیعصر"}
        if location is None:
            location = Location(tenant_id=tenant.id, **location_data)
            db.add(location)
        else:
            for field, value in location_data.items():
                setattr(location, field, value)
            location.is_active = True
        await db.flush()
        existing_locations = list((await db.scalars(select(Location).where(Location.tenant_id == tenant.id))).all())
        for existing_location in existing_locations:
            existing_location.is_active = existing_location.id == location.id
        await db.execute(delete(WorkingHours).where(WorkingHours.tenant_id == tenant.id, WorkingHours.location_id == location.id))
        backend_working_days = [5, 6, 0, 1, 2, 3]
        db.add_all([WorkingHours(tenant_id=tenant.id, location_id=location.id, day_of_week=day, start_time=time(10), end_time=time(20), slot_duration_minutes=60) for day in backend_working_days])
        await db.flush()
        await db.commit()
        print(f"Seeded Persian tenant yasaman-raesi with {len(categories)} categories, {len(services)} services, {len(staff_members)} staff, and 1 location")


if __name__ == "__main__":
    asyncio.run(seed())
