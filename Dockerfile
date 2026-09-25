# syntax=docker/dockerfile:1
# ============================================================================
#  tg-ytdlp-bot · ایمیج بهینه برای Railway (تک‌کانتینر)
#
#  داخل ایمیج:
#    • ffmpeg + mediainfo            → پردازش ویدیو/صدا
#    • Node.js 22                    → حل چالش JS یوتیوب (کیفیت 720p+)
#    • yt-dlp / gallery-dl           → دانلودرها
#    • bgutil PO-Token provider      → توکن یوتیوب (با متغیر روشن می‌شود)
#    • فونت فارسی/عربی + ایموجی      → زیرنویس و تامبنیل
#
#  خارج از ایمیج (روی Railway بی‌فایده‌اند):
#    docker.io / docker.sock / warp / داشبورد وب
#
#  همهٔ تنظیمات از متغیرهای محیطی خوانده می‌شوند — نیازی به ویرایش کد نیست.
# ============================================================================

# PO Token provider (npm build از ایمیج رسمی bgutil کپی می‌شود)
ARG POT_IMAGE=brainicism/bgutil-ytdlp-pot-provider:2.0.0-node
FROM ${POT_IMAGE} AS bgutil

FROM python:3.11-slim

ARG TZ=UTC
# 1 = نگه‌داشتن PO Token provider داخل ایمیج · 0 = حذف آن (ایمیج سبک‌تر)
ARG INSTALL_POT=1
# 1 = نصب فونت‌های سنگین CJK/هندی (پیش‌فرض 0 برای ایمیج سبک‌تر)
ARG EXTRA_FONTS=0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=${TZ} \
    TG_YTDLP_BG_WORKERS=8 \
    MAX_FILE_SIZE_GB=2 \
    MAX_CONCURRENT_DOWNLOADS=2 \
    MAX_CONCURRENT_UPLOADS=2 \
    YOUTUBE_POT_ENABLED=false

# بسته‌های سیستمی + فونت‌ها + کتابخانه‌های موردنیاز PO Token provider
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        mediainfo \
        curl \
        ca-certificates \
        gnupg \
        tzdata \
        fontconfig \
        libass9 \
        fonts-noto-core \
        fonts-kacst-one \
        fonts-noto-color-emoji \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libjpeg62-turbo \
        libgif7 \
        librsvg2-2 \
        libpixman-1-0 \
    && mkdir -p /usr/share/fonts/truetype/amiri \
    && for font in Amiri-Regular Amiri-Bold Amiri-Italic; do \
           curl -fsSL -o "/usr/share/fonts/truetype/amiri/$font.ttf" \
             "https://raw.githubusercontent.com/aliftype/amiri/main/fonts/$font.ttf" || true; \
       done \
    && fc-cache -f >/dev/null 2>&1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# فونت‌های اضافی (CJK/هندی) — فقط اگر EXTRA_FONTS=1 باشد
RUN if [ "$EXTRA_FONTS" = "1" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends fonts-noto-extra fonts-noto-cjk fonts-indic \
        && fc-cache -f >/dev/null 2>&1 \
        && apt-get clean && rm -rf /var/lib/apt/lists/* ; \
    fi

# Node.js 22 — چالش JS یوتیوب (yt-dlp EJS) به Node ≥ 22 نیاز دارد
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# PO Token provider (اگر INSTALL_POT=0 بود، حذف می‌شود)
COPY --from=bgutil /app /opt/bgutil
RUN if [ "$INSTALL_POT" != "1" ]; then rm -rf /opt/bgutil ; fi ; \
    test -f /opt/bgutil/build/main.js && echo "OK: PO token provider installed" || echo "NOTE: PO token provider not bundled"

WORKDIR /app

# پکیج‌های پایتون (لایهٔ جدا برای کش بهتر)
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && rm -rf /root/.cache/pip

# کد برنامه
COPY . .

RUN cp -f scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && (find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true) \
    && (find /app -type f -name "*.pyc" -delete 2>/dev/null || true)

RUN mkdir -p /app/users /data

EXPOSE 8080

CMD ["/usr/local/bin/docker-entrypoint.sh"]
