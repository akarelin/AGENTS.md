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

# Fetch both remotes and rebase onto each
git fetch "$SRC"
git fetch "$DST"
git pull --rebase --autostash "$SRC" master
git pull --rebase --autostash "$DST" master

git push "$DST" master
git push "$DST" --tags

existing_releases=$(gh release list --repo "$DST_REPO" --limit 100 --json tagName -q '.[].tagName' 2>/dev/null || echo "")
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

    tmpdir=$(mktemp -d)

    gh release download "$tag" --repo "$SRC_REPO" --dir "$tmpdir" 2>/dev/null || true

    asset_flags=(); for f in "$tmpdir"/*; do [[ -f "$f" ]] && asset_flags+=("$f"); done

    # Creating release on target repo
    gh release create "$tag" --repo "$DST_REPO" --title "$name" --notes "$body" \
        ${flags[@]+"${flags[@]}"} ${asset_flags[@]+"${asset_flags[@]}"} 2>/dev/null || true

    rm -rf "$tmpdir"

    echo "  Release $tag created."
done <<< "$releases_json"
