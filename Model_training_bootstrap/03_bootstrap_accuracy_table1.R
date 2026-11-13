# 03_bootstrap_accuracy_table1.R
#
# Step 3 of the workflow: the accuracy assessment of the nine model x data combinations over
# 100 repeats (Table 1). The script lives in the sibling folder `Table1_bootstrap_accuracy`
# together with its inputs and outputs. This wrapper copies that script and its data into
# output/table1_rerun/, runs it there and copies the comparison table next to the other
# outputs of this folder.

table1_dir <- file.path("..", "Table1_bootstrap_accuracy")
if (!file.exists(file.path(table1_dir, "Table1_bootstrap_accuracy.R")))
  stop("sibling package Table1_bootstrap_accuracy not found next to this folder")

run_dir <- file.path("output", "table1_rerun")
dir.create(run_dir, showWarnings = FALSE, recursive = TRUE)
file.copy(file.path(table1_dir, "Table1_bootstrap_accuracy.R"), run_dir, overwrite = TRUE)
file.copy(file.path(table1_dir, "data"), run_dir, recursive = TRUE)   # the 18 predictor tables
dir.create(file.path(run_dir, "output"), showWarnings = FALSE)

owd <- setwd(run_dir)
on.exit(setwd(owd), add = TRUE)
source("Table1_bootstrap_accuracy.R", encoding = "UTF-8")
setwd(owd)

file.copy(file.path(run_dir, "output", "bootstrap_comparison_table.csv"),
          file.path("output", "table1_bootstrap_comparison_table.csv"), overwrite = TRUE)
# remove the working copies of the script and data again; the rerun's own outputs stay in output/table1_rerun/output
unlink(file.path(run_dir, "data"), recursive = TRUE)
unlink(file.path(run_dir, "Table1_bootstrap_accuracy.R"))
ref <- file.path(table1_dir, "output", "bootstrap_comparison_table.csv")
if (file.exists(ref)) {
  same <- identical(readLines(ref), readLines(file.path("output", "table1_bootstrap_comparison_table.csv")))
  cat(sprintf("Table 1 rerun finished; comparison table %s the one in %s\n",
              if (same) "identical to" else "DIFFERS from", table1_dir))
} else cat("Table 1 rerun finished; output/table1_bootstrap_comparison_table.csv written\n")
