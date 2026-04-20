#!/bin/bash
# 视频下载脚本 - 支持全平台
# 使用：./download-video.sh <视频 URL>

YTDLP=~/Library/Python/3.9/bin/yt-dlp
FFMPEG=~/bin/ffmpeg
DOWNLOAD_DIR="/Volumes/1TB/openclaw/videos"

if [ -z "$1" ]; then
    echo "用法：$0 <视频 URL>"
    echo "示例：$0 https://www.bilibili.com/video/BV1GNcXz9E91/"
    exit 1
fi

mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

echo "📥 正在下载：$1"
echo "💾 保存位置：$DOWNLOAD_DIR"

# 下载视频（自动选择最佳画质并合并）
$YTDLP -f "bestvideo+bestaudio/best" --merge-output-format mp4 "$1"

# 如果需要手动合并（当 yt-dlp 无法自动合并时）
# 检查是否有分离的视频和音频文件
for video in *.f*.mp4; do
    if [ -f "$video" ]; then
        base="${video%.f*.mp4}"
        audio="${base}.f*.m4a"
        if ls $audio 1> /dev/null 2>&1; then
            echo "🔧 正在合并视频和音频..."
            $FFMPEG -i "$video" -i $audio -c copy "${base}.mp4" -y
            rm -f "$video" $audio
        fi
    fi
done

echo "✅ 下载完成！"
ls -lh *.mp4 | tail -1
