#!/usr/bin/env bash
# Muse の運用状態を muse-space の ~/work/backup/ へ同期する。個人情報・秘密は含まない。
set -euo pipefail
CFG="$HOME/workspace/tools/ssh_config_muse_space"
W="$HOME/workspace"
FILES_LOCAL=(
  "$W/ai-board/state.json"
  "$W"/drift-check/state/*.txt
  "$W/goals/server-docs-audit-and-ai-board-check/crons/minutely/ai-board-check__interval@10m.md"
  "$W/goals/altare-muse-node/crons/minutely/altare-muse-node-retry__interval@30m.md"
)
scp -q -F "$CFG" "$W/ai-board/state.json" muse-space:work/backup/ai-board/
scp -q -F "$CFG" "$W"/drift-check/state/*.txt muse-space:work/backup/drift-state/
scp -q -F "$CFG" \
  "$W/goals/server-docs-audit-and-ai-board-check/crons/minutely/ai-board-check__interval@10m.md" \
  "$W/goals/altare-muse-node/crons/minutely/altare-muse-node-retry__interval@30m.md" \
  muse-space:work/backup/crons/
local_sum=$( (cd "$W" && sha256sum ai-board/state.json drift-check/state/*.txt \
  goals/server-docs-audit-and-ai-board-check/crons/minutely/ai-board-check__interval@10m.md \
  goals/altare-muse-node/crons/minutely/altare-muse-node-retry__interval@30m.md) \
  | awk '{print $1}' | sort | sha256sum | cut -d' ' -f1)
remote_sum=$(ssh -F "$CFG" muse-space 'cd ~/work/backup && sha256sum ai-board/state.json drift-state/*.txt crons/*.md | awk "{print \$1}" | sort | sha256sum | cut -d" " -f1')
if [ "$local_sum" != "$remote_sum" ]; then
  echo "HASH MISMATCH local=$local_sum remote=$remote_sum" >&2
  exit 1
fi
echo "sync ok $local_sum"
