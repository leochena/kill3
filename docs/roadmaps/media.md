# Roadmap — media & catalog

## Now

- [x] `item.attachments[]` in schema (`uri`, `mime`, `sha256`)  
- [x] Docs: [media-and-catalog.md](../media-and-catalog.md)  

## Next (implement)

1. `POST /api/v1/media` → save under `runtime/board/media/`, return `/media/<id>`  
2. Static serve `/media/...`  
3. CLI `have --image ./photo.jpg` uploads then attaches  
4. UI: URL field + file input; gallery in detail  
5. Summary row: `image_count`, `thumb_uri`  

## Later

- IPFS helper script  
- Video poster frames  
- Client-side compress before upload  

## Done when

Merchant posts local photo without external CDN; buyer sees it in UI and agent summary.
