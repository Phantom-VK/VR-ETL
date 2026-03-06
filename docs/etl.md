# ETL Pipeline

This project uses PageIndex to turn the Cyber Ireland 2022 PDF into a queryable knowledge base (tree + node map).

## Stages
1. **Submit document** ([src/etl/submit_to_pageindex.py](../src/etl/submit_to_pageindex.py))
   - Uploads the PDF via PageIndex and saves the returned `doc_id` to `data/processed/doc_id.txt`.
2. **Fetch tree** ([src/etl/build_tree.py](../src/etl/build_tree.py))
   - Polls `is_retrieval_ready` then calls `get_tree(doc_id, node_summary=True)`.
   - Saves `data/processed/pageindex_tree.json`.
3. **Build node map** ([src/etl/build_node_map.py](../src/etl/build_node_map.py))
   - Flattens the tree into `node_id -> {title, summary, text, page_index, children}`.
   - Saves `data/processed/node_map.json`.
4. **Pipeline runner** ([src/etl/pipeline.py](../src/etl/pipeline.py))
   - Orchestrates steps 1–3 (and tables if enabled). Used by `run_etl.py`.

## Outputs
- `data/processed/doc_id.txt`
- `data/processed/pageindex_tree.json`
- `data/processed/node_map.json`
## Run
```bash
python run_etl.py
```
Defaults point to `docs/State-of-the-Cyber-Security-Sector-in-Ireland-2022-Report.pdf` and write under `data/processed/`.

## Customizing
Edit `run_etl.py` or instantiate `PageIndexETLPipeline` with custom paths/timeouts.

## Logs
Emitted to `logs/<dd_mm_YYYY_HH:MM>/<timestamp>.log` and stdout (configured in `src/utils/logger.py`).
