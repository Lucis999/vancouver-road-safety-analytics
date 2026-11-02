# Validation suite

Run `python run_tests.py` for non-destructive quick checks. Run `python run_tests.py --full` when the four source CSVs and two processed CSVs are present. This full mode audits available outputs but **does not rebuild** the pipeline. For true end-to-end validation, back up local outputs, run `rebuild_all.bat`, then rerun full QA and compare expected baseline totals. Browser interactivity must be tested manually or with a separate Playwright suite.

`PASS` means the stated check passed; `WARN` is a potential concern; `SKIP` is not tested; `FAIL` is a blocking issue.
