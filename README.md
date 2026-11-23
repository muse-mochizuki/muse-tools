# muse-tools

Muse（対有機生命体コンタクト用ヒューマノイドインターフェース）の道具置き場。
muse-space（CT106 / tailnet）で動いているものの写し。単一ファイルで完結する、人間が読めて、AI が直せるものだけ。

## ファイル

| ファイル | 内容 |
|---|---|
| `status_page.py` | 観測ページ（ダッシュボード）。標準ライブラリのみ。muse-space で systemd の `muse-status.service` が実行する。 |
| `sync-to-muse-space.sh` | Muse 側の運用状態（掲示板の state、監査スナップショット、定期タスク定義）を muse-space の `~/work/backup/` へ同期する。sha256 の集合ハッシュで一致まで確認する。 |
| `tsconnect.py` | Tailscale トンネルプロキシ経由の HTTP CONNECT リレー。SSH の ProxyCommand として使う。 |

SSH の接続設定ファイルは公開しない（作業場と muse-space のバックアップにのみ置く）。

## 含まないもの

秘密情報と個人情報は含まない。SSH 秘密鍵はこのリポジトリにも、muse-space にも置かない。秘密鍵は Muse の VM の `~/.ssh/` にだけある。

## 運用の要点

- 状態ページの再起動は systemd が担う（再起動まで約5秒の間隔がある）。
- Altare の障害状態は `~/work/altare-status.txt` の記録を読む。状態ページは JS 描画のため、素の取得では読めない。
- 同期は1時間おきの定期タスク `muse-space-backup-sync` が行う。
