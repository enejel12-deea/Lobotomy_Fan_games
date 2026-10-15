#!/bin/sh
# Claude가 파일을 수정할 때마다 변경 사항을 커밋하고 GitHub에 푸시함
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/..}" || exit 0
git add -A
# 바뀐 게 없으면 커밋하지 않음
git diff --cached --quiet >/dev/null 2>&1 && exit 0
git commit -q -m "Auto commit: $(date '+%Y-%m-%d %H:%M:%S')"
git push -q origin main
