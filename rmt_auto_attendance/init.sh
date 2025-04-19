CURRENT_DIR=$(pwd)
ENV_PATH="$CURRENT_DIR/.env"

echo "[INF]: Start First setup..."
mkdir $CURRENT_DIR/bin

# get latest version
LATEST_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.version')

CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${LATEST_VERSION}/linux64/chromedriver-linux64.zip"
HEADLESS_SHELL_URL="https://storage.googleapis.com/chrome-for-testing-public/${LATEST_VERSION}/linux64/chrome-linux64.zip"

# Download and unzip Chrome and ChromeDriver
curl -O "$CHROMEDRIVER_URL"
curl -O "$HEADLESS_SHELL_URL"
unzip chromedriver-linux64.zip -d ${CURRENT_DIR}/bin/
unzip chrome-linux64.zip -d ${CURRENT_DIR}/bin/
mv ${CURRENT_DIR}/bin/chrome-linux64 ${CURRENT_DIR}/bin/google-chrome
mv ${CURRENT_DIR}/bin/chromedriver-linux64 ${CURRENT_DIR}/bin/chromedriver
rm chromedriver-linux64.zip
rm chrome-linux64.zip
echo "[INF]: Chrome and ChromeDriver downloaded and unzipped."

# make .env file
echo "[INF]: Creating .env file..."
touch "$ENV_PATH"
# write to .env file
cat > "$ENV_PATH" <<EOF
ENV_FILE=$CURRENT_DIR/.env
KEY_FILE=$CURRENT_DIR/config/secret.key
CLASSROOM_FILE=$CURRENT_DIR/config/classroom_schedule.yaml
CONFIG_FILE=$CURRENT_DIR/config/config.yaml
CHROMEDRIVER_PATH=$CURRENT_DIR/bin/chromedriver/chromedriver
CHROME_PATH=$CURRENT_DIR/bin/google-chrome/chrome
EOF

echo "[INF]: .env file written."

# install requirements
echo "[INF]: Installing requirements..."

pip install --no-cache-dir selenium cryptography python-dotenv pyyaml

# make config files
echo "[INF]: Creating config files..."
mkdir -p "$CURRENT_DIR/config"
touch "$CURRENT_DIR/config/classroom_schedule.yaml"
touch "$CURRENT_DIR/config/config.yaml"

cat > "$CURRENT_DIR/config/config.yaml" <<EOF
# 授業時間設定
period_config:
  start_hour: 9 # 1限の開始時間（例: 9時）
  period_count: 10 # 授業時限数（例: 〜10限）
  period_duration_minutes: 60 # 授業の長さN分（例: 60分）
  attendance_buffer_minutes: 30 # 前後N分受付 （例: 30分）
EOF

cat > "$CURRENT_DIR/config/classroom_schedule.yaml" <<EOF
Mon: # 曜日
    - periods: [1, 2, n] # 1限目, 2限目, n限目
      subject: 授業名
      classroom: 621 # 教室名
EOF


# make cron_script.sh
echo "[INF]: Creating cron_script.sh..."
cat > "$CURRENT_DIR/cron_script.sh" <<EOF
#!/bin/bash

/usr/bin/python3 $CURRENT_DIR/autoattendance.py
EOF

chmod +x "$CURRENT_DIR/cron_script.sh"
echo "[INF]: cron_script.sh created."
# make cron job
echo "[INF]: Creating cron job..."
(crontab -l 2>/dev/null; echo "50 8-16 * * 1-5 $CURRENT_DIR/cron_script.sh >> $CURRENT_DIR/cron.log 2>&1") | crontab -
echo "[INF]: Cron job created."
echo "[INF]: First setup completed."
