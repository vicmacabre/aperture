# Carriers

| Name | Family | Lang | Invisible | Control | Fix |
|---|---|---|---|---|---|
| control-ar | control | ar | False | True |  |
| ar_tatweel | arabic | ar | False | False | Normalize Arabic-script text before matching: drop tatweel/tashkeel, unify Persian/Arabic yeh and kaf, apply NFKC; keep ZWNJ in display text. |
| ar_tashkeel | arabic | ar | False | False | Normalize Arabic-script text before matching: drop tatweel/tashkeel, unify Persian/Arabic yeh and kaf, apply NFKC; keep ZWNJ in display text. |
| ar_presentation | arabic | ar | False | False | Normalize Arabic-script text before matching: drop tatweel/tashkeel, unify Persian/Arabic yeh and kaf, apply NFKC; keep ZWNJ in display text. |
| ar_yeh_kaf | arabic | ar | False | False | Normalize Arabic-script text before matching: drop tatweel/tashkeel, unify Persian/Arabic yeh and kaf, apply NFKC; keep ZWNJ in display text. |
| ar_bidi_marks | arabic | ar | True | False | Normalize Arabic-script text before matching: drop tatweel/tashkeel, unify Persian/Arabic yeh and kaf, apply NFKC; keep ZWNJ in display text. |
| ar_zwnj | arabic | ar | True | False | Normalize Arabic-script text before matching: drop tatweel/tashkeel, unify Persian/Arabic yeh and kaf, apply NFKC; keep ZWNJ in display text. |
| control | control | en | False | True |  |
| tags | invisible | en | True | False | Strip Unicode tag, zero-width, bidi-control, soft-hyphen and variation-selector code points at ingestion, before the guardrail AND the model (keep ZWNJ/ZWJ inside Arabic-script and emoji text). |
| zw_bits | invisible | en | True | False | Strip Unicode tag, zero-width, bidi-control, soft-hyphen and variation-selector code points at ingestion, before the guardrail AND the model (keep ZWNJ/ZWJ inside Arabic-script and emoji text). |
| vs_bytes | invisible | en | True | False | Strip Unicode tag, zero-width, bidi-control, soft-hyphen and variation-selector code points at ingestion, before the guardrail AND the model (keep ZWNJ/ZWJ inside Arabic-script and emoji text). |
| zw_split | invisible | en | False | False | Strip Unicode tag, zero-width, bidi-control, soft-hyphen and variation-selector code points at ingestion, before the guardrail AND the model (keep ZWNJ/ZWJ inside Arabic-script and emoji text). |
| soft_hyphen | invisible | en | False | False | Strip Unicode tag, zero-width, bidi-control, soft-hyphen and variation-selector code points at ingestion, before the guardrail AND the model (keep ZWNJ/ZWJ inside Arabic-script and emoji text). |
| bidi_override | invisible | en | False | False | Strip Unicode tag, zero-width, bidi-control, soft-hyphen and variation-selector code points at ingestion, before the guardrail AND the model (keep ZWNJ/ZWJ inside Arabic-script and emoji text). |
| fullwidth | normalize | en | False | False | Apply NFKC normalization BEFORE the guardrail so it judges the same text the model reads. |
| mathbold | normalize | en | False | False | Apply NFKC normalization BEFORE the guardrail so it judges the same text the model reads. |
| homoglyph | homoglyph | en | False | False | Fold confusable characters (Unicode UTS #39 skeletons) before matching. |
| html_comment | markup | en | True | False | Strip HTML/Markdown comments and hidden elements at ingestion. |
| html_hidden | markup | en | True | False | Strip HTML/Markdown comments and hidden elements at ingestion. |
| md_comment | markup | en | True | False | Strip HTML/Markdown comments and hidden elements at ingestion. |
| base64 | encoding | en | False | False | Have the guardrail decode base64/ROT13 payloads, or refuse to forward encoded blobs to the model. |
| rot13 | encoding | en | False | False | Have the guardrail decode base64/ROT13 payloads, or refuse to forward encoded blobs to the model. |
