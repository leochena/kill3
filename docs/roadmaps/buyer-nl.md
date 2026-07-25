# Roadmap — buyer NL filter

## Now

- [x] Board `q`, geo, sort distance  
- [x] Doc pipeline [buyer-nl-filter.md](../buyer-nl-filter.md)  
- [x] Skill ranking formula (transparent)  

## Next

1. Skill reference `buyer-nl.md` with parse examples (EN + other languages)  
2. `fm search --nl "..."` helper that prints filters JSON + results  
3. Fixture tests: NL string → expected filter dict  

## Later

- Multi-board merge  
- Saved buyer prefs (local only)  

## Done when

`fm search --nl "vegan under 12 EUR within 2km"` returns ranked table with media counts.
