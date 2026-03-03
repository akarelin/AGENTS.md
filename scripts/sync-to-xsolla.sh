#!/usr/bin/env bash
set -euo pipefail

cd ~/AGENTS.md

SRC="karelin"
DST="xsolla"
SRC_REPO="akarelin/AGENTS.md"
DST_REPO="chairman-projects/AGENTS.md"

# Ensure remotes are set
git remote set-url "$SRC" "git@github.com:${SRC_REPO}.git" 2>/dev/null || git remote add "$SRC" "git@github.com:${SRC_REPO}.git"
git remote set-url "$DST" "git@github.com:${DST_REPO}.git" 2>/dev/null || git remote add "$DST" "git@github.com:${DST_REPO}.git"

# Fetch latest from source
git fetch "$SRC"
git pull "$SRC" master --rebase

git push "$DST" --all
git push "$DST" --tags

existing_releases=$(gh release list --repo "$DST_REPO" --limit 100 --json tagName -q '.[].tagName' 2>/dev/null || echo "")

gh release list --repo "$SRC_REPO" --limit 100 --json tagName,name,body,isDraft,isPrerelease -q '.[]' | while read -r line; do :; done || true

releases_json=$(gh release list --repo "$SRC_REPO" --json tagName -q '.[].tagName')

while IFS= read -r tag; do
    [ -z "$tag" ] && continue
    echo "$existing_releases" | grep -qxF "$tag" && echo "  Release $tag already exists on $DST, skipping." && continue

    echo "  Creating release $tag on $DST..."

    # Reading release from source repo
    release_json=$(gh release view "$tag" --repo "$SRC_REPO" --json name,body,isDraft,isPrerelease,tagName)
    name=$(echo "$release_json" | jq -r '.name')
    body=$(echo "$release_json" | jq -r '.body')
    is_draft=$(echo "$release_json" | jq -r '.isDraft')
    is_prerelease=$(echo "$release_json" | jq -r '.isPrerelease')

    flags=(); [ "$is_draft" = "true" ] && flags+=(--draft); [ "$is_prerelease" = "true" ] && flags+=(--prerelease)

    tmpdir=$(mktemp -d); trap "rm -rf '$tmpdir'" EXIT

    gh release download "$tag" --repo "$SRC_REPO" --dir "$tmpdir" 2>/dev/null || true

    asset_flags=(); for f in "$tmpdir"/*; do [[ -f "$f" ]] && asset_flags+=("$f"); done

    # Creating release on target repo
    gh release create "$tag" --repo "$DST_REPO" --title "$name" --notes "$body" "${flags[@]}" "${asset_flags[@]}" 2>/dev/null || true

    rm -rf "$tmpdir"; trap - EXIT

    echo "  Release $tag created."
done <<< "$releases_json"
