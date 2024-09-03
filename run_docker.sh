#!/bin/bash

# イメージ名、Dockerfile、requirements.txtのパス
IMAGE_NAME="world_builer"
DOCKERFILE_PATH="./Dockerfile"
REQUIREMENTS_PATH="./requirements.txt"

# macOS用のstatコマンドを使用して最終変更日を取得
DOCKERFILE_LAST_MODIFIED=$(stat -f %m $DOCKERFILE_PATH)
REQUIREMENTS_LAST_MODIFIED=$(stat -f %m $REQUIREMENTS_PATH)

# イメージのビルド日を取得（イメージがない場合は空）
IMAGE_BUILD_TIMESTAMP=$(docker inspect -f '{{ .Created }}' $IMAGE_NAME 2>/dev/null)

# ナノ秒とタイムゾーンを除去してエポック秒に変換
if [[ ! -z "$IMAGE_BUILD_TIMESTAMP" ]]; then
  # ナノ秒の部分を削除（.以降を削除）
  IMAGE_BUILD_TIMESTAMP="${IMAGE_BUILD_TIMESTAMP%.*}"
  # タイムゾーン情報を削除（Zを削除）
  IMAGE_BUILD_TIMESTAMP="${IMAGE_BUILD_TIMESTAMP%Z}"
  IMAGE_BUILD_DATE=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$IMAGE_BUILD_TIMESTAMP" +%s)
fi

# Dockerfileまたはrequirements.txtが最後に変更された後にイメージが作成されているかどうかを確認
if [[ -z "$IMAGE_BUILD_DATE" || "$DOCKERFILE_LAST_MODIFIED" -gt "$IMAGE_BUILD_DATE" || "$REQUIREMENTS_LAST_MODIFIED" -gt "$IMAGE_BUILD_DATE" ]]; then
  echo "イメージを再構築します..."
  docker build -t $IMAGE_NAME .
else
  echo "既存のイメージを使用します..."
fi

# イメージを使ってコンテナを実行
docker run -v $(pwd):/usr/src/app --rm -it $IMAGE_NAME bash