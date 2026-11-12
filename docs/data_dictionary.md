# ADL Insights Database — Data Dictionary

## Sheet 1: `Publications Master` & `publications_master.csv / .json`

| Field Name | Type | Description | Source / Derivation |
|---|---|---|---|
| `Publication ID` | String | Unique Drupal publication identifier (`nid`). Primary key. | API `nid` field |
| `Title` | String | Publication headline or article title. HTML stripped & unescaped. | API `title` field |
| `Subtitle` | String | Subtitle, secondary headline, or article brief. | API `subtitle` field |
| `Publication Date` | String | Official display publication period (e.g., "October 2026"). | API `field_date_publication` |
| `Publication Year` | Integer | Four-digit calendar year extracted from publication period. | Derived from `Publication Date` |
| `Created Date` | String | ISO 8601 timestamp when node was created in Drupal CMS. | `<time datetime="...">` in `created` |
| `Publication Type` | String | ADL publication type (Viewpoint, Report, Blue Shift, etc.). | API `field_insight_type` or `type` |
| `Industry` | String | Semicolon-separated original website industry categories. | Extracted links from `industries` |
| `Services / Capabilities` | String | Semicolon-separated ADL consulting capabilities / services. | Extracted links from `services` |
| `Challenges` | String | Semicolon-separated business challenges addressed. | Extracted links from `challenges` |
| `Summary / Excerpt` | String | Official article summary or opening excerpt. | API `body` field (clean text) |
| `URL` | String | Absolute canonical article URL on `adlittle.com`. | Resolved from relative `node_url` |
| `ENUR Relevance` | Enum | Relevance to Energy, Utilities & Resources: `Direct ENUR`, `Cross-practice`, or `Other / Non-ENUR`. | Algorithmic taxonomy classification |
| `ENUR Subsector` | Enum | Assigned ENUR consulting practice area (12 specialized sectors). | Keyword & semantic taxonomy matching |
| `BD Topics` | String | Relevant consulting themes for business development. | Mapped to practice offerings |
| `First Seen` | Date (YYYY-MM-DD) | Date when this publication was first observed by the system. | Ingestion audit trail |
| `Last Seen` | Date (YYYY-MM-DD) | Date when this publication was most recently verified. | Ingestion audit trail |
| `Last Updated` | Date (YYYY-MM-DD) | Date when title, date, excerpt, or industry changed. | Change detection engine |
| `Record Status` | Enum | `Active` (present in catalogue) or `Not observed` (delisted). | Lifecycle tracking |
| `Data Quality` | Enum | `Complete` (all fields verified), `Partial`, or `Review`. | Automated QA scoring |

---

## Sheet 2: `ENUR Publications` & `publications_enur.csv`

Materialized view containing all records where `ENUR Relevance` is `Direct ENUR` or `Cross-practice`.

| Field Name | Type | Description |
|---|---|---|
| `Publication ID` | String | Drupal `nid` |
| `Title` | String | Full publication title |
| `Subtitle` | String | Subtitle or deck |
| `Publication Date` | String | Month and year of release |
| `Publication Year` | Integer | Extracted calendar year |
| `Publication Type` | String | Document format (Viewpoint, Report, etc.) |
| `Industry` | String | Official ADL industry tags |
| `ENUR Relevance` | Enum | `Direct ENUR` or `Cross-practice` |
| `ENUR Subsector` | Enum | Primary ENUR subsector |
| `BD Topics` | String | Strategic consulting topics |
| `Summary / Excerpt` | String | Publication summary |
| `URL` | String | Absolute hyperlink to publication |

---

## Sheet 3: `Publication Themes` & `publication_topics.csv`

Normalized 1-to-many relationship mapping publications to specific consulting business development themes.

| Field Name | Type | Description |
|---|---|---|
| `Publication ID` | String | Foreign key to `Publications Master` |
| `Title` | String | Publication title |
| `Publication Date` | String | Official publication date |
| `Publication Year` | Integer | Publication year |
| `Industry` | String | Official industry classifications |
| `ENUR Relevance` | Enum | `Direct ENUR` or `Cross-practice` |
| `ENUR Subsector` | Enum | Consulting practice subsector |
| `BD Theme` | String | Specialized business development theme |
| `Potential BD Relevance` | String | Rationale for pitching / replicating approach |
| `URL` | String | Direct link to publication |

---

## Sheet 4: `Update Log`

Historical execution and audit record for every ETL run.

| Field Name | Description |
|---|---|
| `Run ID` | Unique run identifier (`RUN-YYYYMMDD-HHMMSS`) |
| `Run timestamp` | UTC timestamp of execution |
| `Execution environment` | Local machine or GitHub Actions runner |
| `Execution mode` | `backfill`, `update`, `import-json`, or `validate` |
| `Pages requested` | Number of API / file pages requested |
| `Pages successfully processed` | Number of pages successfully ingested |
| `API-reported publication count` | Target count reported by API pager |
| `Records retrieved` | Publications collected during this run |
| `Unique records` | Cumulative unique publications in archive |
| `New records` | Brand-new publications added |
| `Updated records` | Existing publications with revised metadata |
| `Errors` | Diagnostic error messages (or `None`) |
| `Coverage status` | `Complete` or `Partial / Incomplete` |
| `Execution result` | `SUCCESS`, `PARTIAL`, or `FAILED` |

---

## Sheet 5: `Data Quality & Coverage` & `sync_status.json`

Summary metrics validating database completeness, field integrity, and catalogue reconciliation.

