#!/usr/bin/env bash
# Собирает АВТОНОМНОЕ macOS-приложение «Lingra.app».
# Внутрь упаковываются: переносимый Python + все библиотеки + модель Whisper.
# Готовое приложение запускается по двойному клику — без интернета и без установки.
set -euo pipefail

cd "$(dirname "$0")"
PROJECT="$(pwd)"
APP_NAME="Lingra"
APP="$PROJECT/$APP_NAME.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RES="$CONTENTS/Resources"

# Переносимый CPython (relocatable, со своим pip) — выбираем под архитектуру ноутбука
PY_TAG="20260510"
PY_VER="3.12.13"
ARCH="$(uname -m)"   # arm64 (Apple Silicon) или x86_64 (Intel)
case "$ARCH" in
  arm64)  PY_TRIPLE="aarch64-apple-darwin" ;;
  x86_64) PY_TRIPLE="x86_64-apple-darwin" ;;
  *) echo "❌ Неизвестная архитектура: $ARCH"; exit 1 ;;
esac
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/cpython-${PY_VER}%2B${PY_TAG}-${PY_TRIPLE}-install_only.tar.gz"
echo "🖥  Архитектура: $ARCH → $PY_TRIPLE"
# Модель, которую запекаем внутрь (чтобы первая расшифровка не качала из сети)
BUNDLE_MODEL="${BUNDLE_MODEL:-small}"
# Модель перевода NLLB (CTranslate2). Пусто — не запекать (скачается при первом переводе).
BUNDLE_NLLB="${BUNDLE_NLLB:-OpenNMT/nllb-200-distilled-1.3B-ct2-int8}"

echo "🧹 Чищу старую сборку..."
rm -rf "$APP"
mkdir -p "$MACOS" "$RES" "$PROJECT/build_cache"

echo "📦 Копирую исходники..."
cp core.py app.py i18n.py translate.py translate_pdf.py "$RES/"

# --- Иконка ---
echo "🎨 Генерирую иконку..."
python3 assets/generate_icon.py >/dev/null
ICONSET="$PROJECT/assets/icon.iconset"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512 1024; do
  sips -z $size $size assets/icon_1024.png --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  [ $size -le 512 ] && sips -z $((size*2)) $((size*2)) assets/icon_1024.png --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$RES/AppIcon.icns"
rm -rf "$ICONSET"

# --- Переносимый Python ---
PY_TGZ="$PROJECT/build_cache/python-standalone-$ARCH.tar.gz"
if [ ! -f "$PY_TGZ" ]; then
  echo "⬇️  Скачиваю переносимый Python (один раз, кешируется)..."
  curl -L --fail -o "$PY_TGZ" "$PY_URL"
fi
echo "📦 Распаковываю Python в бандл..."
tar -xzf "$PY_TGZ" -C "$RES"          # появляется $RES/python/...
PYBIN="$RES/python/bin/python3"
"$PYBIN" --version

# --- Библиотеки внутрь бандла ---
echo "⬇️  Устанавливаю библиотеки внутрь приложения..."
"$PYBIN" -m pip install --upgrade pip -q
"$PYBIN" -m pip install -r requirements.txt -q

# --- Запекаем модель Whisper в бандл (HF-кеш внутри .app) ---
echo "⬇️  Скачиваю модель '$BUNDLE_MODEL' внутрь приложения..."
mkdir -p "$RES/models"
if HF_HOME="$RES/models" "$PYBIN" -c "from faster_whisper import WhisperModel; WhisperModel('$BUNDLE_MODEL', device='cpu', compute_type='int8'); print('ok')"; then
  echo "✅ Модель запечена."
else
  echo "⚠️  Не удалось запечь модель — приложение скачает её при первом запуске."
fi

# --- Запекаем модель перевода NLLB (CTranslate2) в тот же HF-кеш ---
if [ -n "$BUNDLE_NLLB" ]; then
  echo "⬇️  Скачиваю модель перевода '$BUNDLE_NLLB' внутрь приложения (~1.4 ГБ)..."
  if HF_HOME="$RES/models" "$PYBIN" -c "from huggingface_hub import snapshot_download; snapshot_download('$BUNDLE_NLLB'); print('ok')"; then
    echo "✅ Модель перевода запечена."
  else
    echo "⚠️  Не удалось запечь NLLB — перевод скачает модель при первом использовании."
  fi
fi

# --- Чистим лишнее для уменьшения размера ---
echo "🧹 Убираю кеши и тесты..."
find "$RES/python" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "$RES/python" -type d -name "test" -path "*/python3.12/*" -prune -exec rm -rf {} + 2>/dev/null || true
"$PYBIN" -m pip cache purge >/dev/null 2>&1 || true

# --- Исполняемый файл бандла: запускает сервер и открывает браузер ---
cat > "$MACOS/$APP_NAME" <<'EOF'
#!/bin/bash
HERE="$(cd "$(dirname "$0")/../Resources" && pwd)"
export HF_HOME="$HERE/models"               # модель ищется внутри .app
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}" # не лезть в сеть, если модель уже внутри
export TRANSCRIBE_OPEN_BROWSER=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=4
cd "$HERE"
exec "$HERE/python/bin/python3" "$HERE/app.py"
EOF
chmod +x "$MACOS/$APP_NAME"

# --- Info.plist ---
cat > "$CONTENTS/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleExecutable</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>com.local.lingra</string>
  <key>CFBundleVersion</key><string>3.0</string>
  <key>CFBundleShortVersionString</key><string>3.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

# Снимаем карантин, подписываем ad-hoc (нужно для запуска по клику на Apple Silicon)
xattr -cr "$APP" 2>/dev/null || true
echo "🔏 Подписываю ad-hoc..."
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || echo "⚠️  codesign пропущен (приложение всё равно запустится)"
touch "$APP"

SIZE="$(du -sh "$APP" | cut -f1)"
echo ""
echo "✅ Готово: $APP  (размер: $SIZE)"
echo "   Двойной клик — приложение запустится сразу, без интернета."
