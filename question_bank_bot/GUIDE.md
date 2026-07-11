# 📖 راهنمای نصب و راه‌اندازی بات بانک سوال تلگرام
# Telegram Question Bank Bot – Installation & Deployment Guide

---

## ✅ پیش‌نیازها | Prerequisites

| نرم‌افزار | نسخه |
|-----------|-------|
| Docker | 24+ |
| Docker Compose | v2+ |
| دسترسی به اینترنت برای Telegram API | - |

---

## 🚀 مرحله ۱ – ساخت بات تلگرام

1. در تلگرام به [@BotFather](https://t.me/BotFather) بروید
2. دستور `/newbot` را بفرستید
3. نام و یوزرنیم بات را وارد کنید
4. **توکن** دریافتی را کپی کنید (مثال: `7123456789:AAFxxxxxxxxxx`)

---

## 🔑 مرحله ۲ – پیدا کردن Telegram ID خودتان

1. به [@userinfobot](https://t.me/userinfobot) پیام بدید
2. عدد `Id` که می‌دهد همان شناسه شماست (مثال: `123456789`)

---

## 📁 مرحله ۳ – آماده‌سازی پروژه روی سرور

```bash
# ۱. اتصال به سرور اوبونتو
ssh user@YOUR_SERVER_IP

# ۲. نصب Docker (اگر نصب نیست)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# ۳. کپی فایل‌های پروژه به سرور
# (فرض: پوشه question_bank_bot را آپلود کرده‌اید)
cd question_bank_bot

# ۴. ساخت فایل .env از نمونه
cp .env.example .env
```

---

## ⚙️ مرحله ۴ – تنظیم فایل .env

فایل `.env` را با ویرایشگر باز کنید:

```bash
nano .env
```

محتوای آن را پر کنید:

```env
BOT_TOKEN=7123456789:AAFxxxxxxxxxx        # توکن از BotFather
ADMIN_IDS=123456789,987654321             # شناسه تلگرام ادمین‌ها (با کاما جدا کنید)
UPLOADS_DIR=/app/uploads
LOGS_DIR=/app/logs
DB_PATH=/app/database/question_bank.db
MAX_FILE_SIZE_MB=50
ITEMS_PER_PAGE=8
```

---

## 🐳 مرحله ۵ – اجرا با Docker

```bash
# ساخت image و اجرا
docker compose up -d --build

# بررسی وضعیت
docker compose ps

# مشاهده لاگ‌ها
docker compose logs -f
```

---

## 🧪 مرحله ۶ – تست بات

در تلگرام:
1. بات خود را جستجو کنید
2. `/start` بفرستید ← باید منوی موضوعات را ببینید
3. `/admin` بفرستید ← باید پنل ادمین را ببینید (اگر ID شما در ADMIN_IDS باشد)

---

## 👑 راهنمای استفاده ادمین

### اضافه کردن محتوا (ترتیب مهم است!)

```
۱. ابتدا موضوع بسازید:    ➕ Add Subject  → مثلاً: "ریاضی"
۲. سپس فصل بسازید:       ➕ Add Chapter  → موضوع: ریاضی | فصل: "مشتق"
۳. سپس تاپیک بسازید:     ➕ Add Topic    → فصل: مشتق | تاپیک: "قوانین مشتق"
۴. در آخر فایل آپلود:    📤 Upload Question → PDF را بفرستید
```

### آپلود سوال

1. روی **📤 Upload Question** بزنید
2. موضوع ← فصل ← تاپیک را انتخاب کنید
3. فایل PDF را در چت بفرستید
4. بات فایل را ذخیره کرده و ZIP را به‌روز می‌کند

### حذف سوال

1. روی **🗑 Delete Question** بزنید
2. مسیر را انتخاب کنید
3. تأیید حذف را بزنید

### آمار سیستم

دستور `/stats` یا دکمه **📊 Statistics** → نمایش:
- تعداد موضوعات / فصل‌ها / تاپیک‌ها / PDFها
- حجم دیسک مصرفی
- تعداد فایل‌های ZIP

### ساخت دستی ZIP

دکمه **📦 Build ZIP Package** → موضوع ← فصل ← تاپیک را انتخاب کنید.
(ZIP ها بصورت خودکار هم هنگام آپلود/حذف ساخته می‌شوند)

---

## 👤 راهنمای استفاده کاربر عادی

```
/start
  ↓
📚 انتخاب موضوع (Subject)
  ↓
📂 انتخاب فصل (Chapter)
  ↓
📋 انتخاب تاپیک (Topic)
  ↓
📄 مشاهده لیست PDFها
  ├── تک‌تک دانلود کنید (روی هر فایل بزنید)
  ├── 📂 Download All PDFs (همه یکجا)
  └── 📦 Download ZIP (آرشیو فشرده)
```

---

## 🔧 دستورات مدیریتی Docker

```bash
# توقف بات
docker compose down

# ری‌استارت
docker compose restart

# آپدیت بعد از تغییر کد
docker compose up -d --build

# مشاهده لاگ آنی
docker compose logs -f

# ورود به کانتینر
docker compose exec bot sh

# بکاپ دیتابیس
docker compose cp bot:/app/database/question_bank.db ./backup.db

# بکاپ فایل‌های PDF
docker run --rm -v question_bank_bot_uploads_data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/uploads_backup.tar.gz /data
```

---

## 📂 ساختار ذخیره‌سازی فایل‌ها

```
uploads/
└── ریاضی/
    └── مشتق/
        └── قوانین_مشتق/
            ├── a1b2c3d4_سوال۱.pdf
            ├── e5f6g7h8_سوال۲.pdf
            └── قوانین_مشتق.zip   ← بصورت خودکار ساخته می‌شود
```

---

## 🛡️ نکات امنیتی

- فایل `.env` را هرگز در git commit نکنید
- `ADMIN_IDS` را فقط برای افراد مورد اعتماد تنظیم کنید
- حجم فایل آپلودی با `MAX_FILE_SIZE_MB` محدود می‌شود
- نام فایل‌ها sanitize می‌شوند (path traversal امکان‌پذیر نیست)

---

## ❓ مشکلات رایج

| مشکل | راه‌حل |
|------|---------|
| بات جواب نمی‌دهد | `docker compose logs -f` → بررسی خطا |
| `BOT_TOKEN is not set` | فایل `.env` را چک کنید |
| `/admin` کار نمی‌کند | مطمئن شوید ID شما در `ADMIN_IDS` است |
| آپلود PDF رد می‌شود | حجم فایل را چک کنید، فقط PDF قبول است |
| ZIP ساخته نمی‌شود | `docker compose logs` → بررسی فضای دیسک |
