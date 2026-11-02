# Validation and release QA

## Windows quick test

From the project folder in VS Code / Anaconda Prompt:

```powershell
conda activate vancouver-parking
python run_tests.py
```

Or double-click `run_tests.bat`. Open `validation_results/validation_report.html`.

## Full local data audit

Copy the four official source CSVs into the project root using the filenames in `data/README.md`. Generate processed outputs using `rebuild_all.bat` **only after backing up existing results**. Then run:

```powershell
python run_tests.py --full
```

This checks source/output presence, cleaned parking coordinate bounds, crash weight validity and static dashboard elements. It does not claim to prove that raw counts reconcile to cleaned/excluded counts, that source-to-output ETL is deterministic, or that map controls work in a browser. Those remain release acceptance tasks.

## Browser acceptance checklist

Open `site/index.html` with internet access for CDN libraries. Confirm that: the map renders; parking/collision/comparison modes update; multi-year selections update summaries; B−A comparison works; road highlight toggles and top-N work; hover ranking and click lock work; radius 100–1000 m changes nearby crash results; and selecting ICBC 2020 gives a clear unavailable-data message. Check Chrome and Edge, and record screenshots and failures.

## Outputs

- `validation_results/validation_report.html` — readable summary
- `validation_results/test_results.json` — structured evidence
- `validation_results/test_results.csv` — row-level QA results

No test overwrites raw CSVs, processed CSVs, or the published HTML.
